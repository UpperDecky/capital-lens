"""Auth router -- JWT register/login plus TOTP-based MFA."""
import json
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import pyotp
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from backend.database import get_connection
from backend.models.user import (
    BackupCodesResponse,
    MeResponse,
    MfaChallengeRequest,
    MfaDisableRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
)
from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_DAYS
from backend.middleware.tier_tracking import TIER_CONFIG, _reset_at_iso, get_daily_remaining
from backend.services.audit_logger import log_event
from backend.services.compliance import TOS_VERSION, log_disclaimer_acceptance

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)

APP_NAME = "Capital Lens"
MFA_PENDING_MINUTES = 10
BACKUP_CODE_COUNT = 8


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _create_token(user_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_mfa_pending_token(user_id: str, email: str) -> str:
    """Short-lived, scope-restricted token used only between login and MFA challenge."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=MFA_PENDING_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "scope": "mfa_pending",
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_mfa_pending_token(token: str) -> dict:
    """Decode and validate an mfa_pending token. Raises 401 on any failure."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="MFA session expired or invalid")
    if payload.get("scope") != "mfa_pending":
        raise HTTPException(status_code=401, detail="Invalid token scope")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        # Reject mfa_pending tokens on all protected routes
        if payload.get("scope") == "mfa_pending":
            raise HTTPException(status_code=401, detail="MFA verification required")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)


# ---------------------------------------------------------------------------
# Backup-code helpers
# ---------------------------------------------------------------------------

def _generate_backup_codes() -> tuple[list[str], list[str]]:
    """Return (plaintext_codes, hashed_codes) -- 8 x 8-hex-char codes."""
    plaintext = [secrets.token_hex(4) for _ in range(BACKUP_CODE_COUNT)]
    hashed = [bcrypt.hashpw(c.encode(), bcrypt.gensalt()).decode() for c in plaintext]
    return plaintext, hashed


def _verify_backup_code(code: str, hashed_list: list[str]) -> tuple[bool, list[str]]:
    """Check code against stored hashes. Returns (matched, remaining_hashes)."""
    for i, h in enumerate(hashed_list):
        try:
            if bcrypt.checkpw(code.encode(), h.encode()):
                remaining = hashed_list[:i] + hashed_list[i + 1:]
                return True, remaining
        except Exception:
            continue
    return False, hashed_list


def _check_mfa_code(code: str, row: dict) -> bool:
    """
    Verify a TOTP code (6 digits) or backup code (8 hex chars).
    Mutates the DB row's backup codes on successful backup-code use.
    Returns True if valid, False otherwise. Raises on DB error.
    """
    totp_secret = row.get("totp_secret")
    if not totp_secret:
        return False

    if len(code) == 6 and code.isdigit():
        return pyotp.TOTP(totp_secret).verify(code, valid_window=1)

    if len(code) == 8:
        raw_codes = row.get("mfa_backup_codes")
        if not raw_codes:
            return False
        hashed_list = json.loads(raw_codes)
        matched, remaining = _verify_backup_code(code, hashed_list)
        if matched:
            conn = get_connection()
            conn.execute(
                "UPDATE users SET mfa_backup_codes=? WHERE id=?",
                (json.dumps(remaining), row["id"]),
            )
            conn.commit()
            conn.close()
        return matched

    return False


# ---------------------------------------------------------------------------
# Routes -- register / login
# ---------------------------------------------------------------------------

@router.post("/auth/register", response_model=TokenResponse)
def register(body: UserCreate) -> TokenResponse:
    conn = get_connection()
    existing = conn.execute(
        "SELECT 1 FROM users WHERE email=?", (body.email,)
    ).fetchone()
    if existing:
        conn.close()
        log_event("REGISTER_DUPLICATE", details={"email": body.email})
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO users
           (id, email, password_hash, tier, created_at, disclaimers_accepted_at, tos_version)
           VALUES (?,?,?,?,?,?,?)""",
        (user_id, body.email, _hash_password(body.password), "free", now, now, TOS_VERSION),
    )
    conn.commit()
    conn.close()

    log_event("REGISTER_SUCCESS", user_id=user_id, details={"email": body.email})
    token = _create_token(user_id, body.email)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: UserLogin) -> TokenResponse:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE email=?", (body.email,)
    ).fetchone()
    conn.close()

    if not row or not _verify_password(body.password, row["password_hash"]):
        log_event("LOGIN_FAILED", details={"email": body.email})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    row = dict(row)
    log_event("LOGIN_SUCCESS", user_id=row["id"], details={"email": row["email"]})

    if row.get("mfa_enabled"):
        # Return a short-lived pending token -- client must call /auth/mfa/challenge
        pending = _create_mfa_pending_token(row["id"], row["email"])
        return TokenResponse(access_token=pending, mfa_required=True)

    token = _create_token(row["id"], row["email"])
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Routes -- MFA challenge (step 2 of login when MFA is enabled)
# ---------------------------------------------------------------------------

@router.post("/auth/mfa/challenge", response_model=TokenResponse)
def mfa_challenge(
    body: MfaChallengeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenResponse:
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    payload = _verify_mfa_pending_token(credentials.credentials)
    user_id = payload["sub"]

    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")

    if not _check_mfa_code(body.code, dict(row)):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    token = _create_token(row["id"], row["email"])
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# Routes -- MFA setup (authenticated)
# ---------------------------------------------------------------------------

@router.post("/auth/mfa/setup", response_model=MfaSetupResponse)
def mfa_setup(current_user: dict = Depends(get_current_user)) -> MfaSetupResponse:
    secret = pyotp.random_base32()
    conn = get_connection()
    conn.execute(
        "UPDATE users SET totp_secret=? WHERE id=?",
        (secret, current_user["id"]),
    )
    conn.commit()
    conn.close()

    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user["email"],
        issuer_name=APP_NAME,
    )
    return MfaSetupResponse(totp_uri=uri)


@router.post("/auth/mfa/verify", response_model=BackupCodesResponse)
def mfa_verify(
    body: MfaVerifyRequest,
    current_user: dict = Depends(get_current_user),
) -> BackupCodesResponse:
    totp_secret = current_user.get("totp_secret")
    if not totp_secret:
        raise HTTPException(
            status_code=400,
            detail="MFA setup not initiated -- call /auth/mfa/setup first",
        )

    if not pyotp.TOTP(totp_secret).verify(body.code, valid_window=1):
        raise HTTPException(
            status_code=400,
            detail="Invalid code -- check your authenticator app and try again",
        )

    plaintext_codes, hashed_codes = _generate_backup_codes()

    conn = get_connection()
    conn.execute(
        "UPDATE users SET mfa_enabled=1, mfa_backup_codes=? WHERE id=?",
        (json.dumps(hashed_codes), current_user["id"]),
    )
    conn.commit()
    conn.close()

    return BackupCodesResponse(backup_codes=plaintext_codes)


# ---------------------------------------------------------------------------
# Routes -- MFA disable (authenticated)
# ---------------------------------------------------------------------------

@router.post("/auth/mfa/disable")
def mfa_disable(
    body: MfaDisableRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    if not _verify_password(body.password, current_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    if not _check_mfa_code(body.code, current_user):
        raise HTTPException(status_code=401, detail="Invalid MFA code")

    conn = get_connection()
    conn.execute(
        "UPDATE users SET mfa_enabled=0, totp_secret=NULL, mfa_backup_codes=NULL WHERE id=?",
        (current_user["id"],),
    )
    conn.commit()
    conn.close()

    return {"status": "MFA disabled"}


# ---------------------------------------------------------------------------
# Routes -- disclaimer acceptance
# ---------------------------------------------------------------------------

@router.post("/auth/accept-disclaimer")
def accept_disclaimer(current_user: dict = Depends(get_current_user)) -> dict:
    """Record that the authenticated user has read and accepted the disclaimer/ToS."""
    conn = get_connection()
    log_disclaimer_acceptance(conn, current_user["id"])
    conn.close()
    return {"status": "accepted", "tos_version": TOS_VERSION}


# ---------------------------------------------------------------------------
# Routes -- profile
# ---------------------------------------------------------------------------

@router.get("/auth/me", response_model=MeResponse)
def get_me(current_user: dict = Depends(get_current_user)) -> MeResponse:
    tier = current_user.get("tier", "free")
    daily_remaining = None
    reset_at = None
    if tier == "free":
        conn = get_connection()
        daily_remaining = get_daily_remaining(conn, current_user["id"])
        conn.close()
        reset_at = _reset_at_iso()
    return MeResponse(
        id=current_user["id"],
        email=current_user["email"],
        tier=tier,
        mfa_enabled=bool(current_user.get("mfa_enabled", 0)),
        daily_remaining=daily_remaining,
        daily_limit=TIER_CONFIG[tier]["daily_limit"],
        reset_at=reset_at,
        disclaimers_accepted_at=current_user.get("disclaimers_accepted_at"),
        tos_version=current_user.get("tos_version"),
    )
