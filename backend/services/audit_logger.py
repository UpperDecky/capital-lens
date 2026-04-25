"""Append-only audit log for security and compliance events.

Writes one JSON line per event to logs/audit.log.
The file is never truncated -- entries accumulate forever.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

_log_dir = Path(__file__).parent.parent.parent / "logs"
_log_dir.mkdir(exist_ok=True)
_log_path = _log_dir / "audit.log"

_audit = logging.getLogger("capital_lens.audit")
_audit.setLevel(logging.INFO)
_audit.propagate = False

if not _audit.handlers:
    _fh = logging.FileHandler(str(_log_path), encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(message)s"))
    _audit.addHandler(_fh)


def log_event(
    event_type: str,
    user_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Write one immutable JSON audit entry. Never call this from a hot loop."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "user_id": user_id,
        "details": details or {},
    }
    _audit.info(json.dumps(entry, separators=(",", ":")))
