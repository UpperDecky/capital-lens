"""
Tier tracking -- enforce per-tier feature limits.

Tier limits:
  free : 5 events/page, 20 events/day, 10 entities
  pro  : 20 events/page, unlimited, all entities
  anon : same caps as free, no daily tracking

Provides get_optional_user() FastAPI dependency for optional auth.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from backend.config import JWT_SECRET, JWT_ALGORITHM
from backend.database import get_connection

_bearer = HTTPBearer(auto_error=False)

# ---- Tier configuration -----------------------------------------------------

FREE_DAILY_LIMIT  = 20   # max feed events per UTC day for free users
FREE_PAGE_LIMIT   = 5    # max events per page request for free/anon users
PRO_PAGE_LIMIT    = 20
FREE_ENTITY_LIMIT = 10   # max entities returned for free/anon users

TIER_CONFIG = {
    "free": {
        "page_limit":   FREE_PAGE_LIMIT,
        "daily_limit":  FREE_DAILY_LIMIT,
        "entity_limit": FREE_ENTITY_LIMIT,
    },
    "pro": {
        "page_limit":   PRO_PAGE_LIMIT,
        "daily_limit":  None,
        "entity_limit": None,
    },
    "admin": {
        "page_limit":   None,   # no cap -- admin sees everything
        "daily_limit":  None,
        "entity_limit": None,
    },
    "anon": {
        "page_limit":   FREE_PAGE_LIMIT,
        "daily_limit":  None,   # anon users not tracked (no identity)
        "entity_limit": FREE_ENTITY_LIMIT,
    },
}


# ---- Optional-auth dependency -----------------------------------------------

def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict | None:
    """
    Dependency that returns the authenticated user dict, or None if the
    request is unauthenticated. Never raises -- bad/missing tokens are
    treated silently as anonymous.
    """
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id or payload.get("scope") == "mfa_pending":
            return None
    except JWTError:
        return None

    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_tier(user: dict | None) -> str:
    """Return 'free', 'pro', or 'anon'."""
    if user is None:
        return "anon"
    return user.get("tier", "free")


# ---- Daily limit helpers ----------------------------------------------------

def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _reset_at_iso() -> str:
    """ISO datetime for next UTC midnight (when the daily counter resets)."""
    from datetime import date, timedelta
    tomorrow = date.today() + timedelta(days=1)
    return f"{tomorrow.isoformat()}T00:00:00Z"


def check_and_update_daily_limit(
    conn: Any,
    user_id: str,
    events_requested: int,
) -> tuple[int, bool]:
    """
    Check the free-tier daily event limit and increment the counter.

    Returns (remaining_after, is_over_limit).
    Resets the counter when the stored date differs from today (UTC).
    """
    today = _today_utc()

    row = conn.execute(
        "SELECT daily_event_count, daily_reset_at FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not row:
        return (FREE_DAILY_LIMIT, False)

    count    = row["daily_event_count"] or 0
    reset_at = row["daily_reset_at"] or ""

    # New calendar day -- reset counter
    if reset_at != today:
        count = 0
        conn.execute(
            "UPDATE users SET daily_event_count=0, daily_reset_at=? WHERE id=?",
            (today, user_id),
        )
        conn.commit()

    if count >= FREE_DAILY_LIMIT:
        return (0, True)

    consumed = min(events_requested, FREE_DAILY_LIMIT - count)
    conn.execute(
        "UPDATE users SET daily_event_count=daily_event_count+? WHERE id=?",
        (consumed, user_id),
    )
    conn.commit()

    remaining = FREE_DAILY_LIMIT - count - consumed
    return (max(0, remaining), False)


def get_daily_remaining(conn: Any, user_id: str) -> int:
    """Return how many feed events this free user still has today."""
    today = _today_utc()
    row = conn.execute(
        "SELECT daily_event_count, daily_reset_at FROM users WHERE id=?",
        (user_id,),
    ).fetchone()
    if not row:
        return FREE_DAILY_LIMIT
    count    = row["daily_event_count"] or 0
    reset_at = row["daily_reset_at"] or ""
    if reset_at != today:
        return FREE_DAILY_LIMIT
    return max(0, FREE_DAILY_LIMIT - count)
