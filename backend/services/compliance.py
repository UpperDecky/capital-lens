"""Compliance helpers -- disclaimer acceptance recording and audit trail."""
from datetime import datetime, timezone
from typing import Any

from backend.services.audit_logger import log_event

TOS_VERSION = "1.0"


def log_disclaimer_acceptance(conn: Any, user_id: str, version: str = TOS_VERSION) -> None:
    """Store disclaimer acceptance in users table AND write to immutable audit log.

    Call this whenever a user explicitly accepts the Terms of Service/Disclaimer.
    Audit entries are retained forever per legal requirements.
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE users SET disclaimers_accepted_at=?, tos_version=? WHERE id=?",
        (now, version, user_id),
    )
    conn.commit()
    log_event(
        "DISCLAIMER_ACCEPTED",
        user_id=user_id,
        details={"tos_version": version, "accepted_at": now},
    )
