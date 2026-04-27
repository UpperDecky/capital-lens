"""Admin analytics routes."""
from fastapi import APIRouter, Header, HTTPException
import os

from backend.services.analytics_reporter import reporter

router = APIRouter(prefix="/admin/analytics", tags=["admin"])

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def _check_admin(secret: str | None) -> None:
    if ADMIN_SECRET and secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Secret header")


@router.get("/weekly")
def get_weekly_analytics(x_admin_secret: str | None = Header(default=None)) -> dict:
    """Weekly analytics report."""
    _check_admin(x_admin_secret)
    return reporter.get_weekly_report()


@router.get("/cohort")
def get_cohort_analytics(
    days_ago: int = 7, x_admin_secret: str | None = Header(default=None)
) -> dict:
    """Retention for users who signed up N days ago."""
    _check_admin(x_admin_secret)
    return reporter.get_user_cohort(days_ago)


@router.get("/dau")
def get_dau(
    days: int = 30, x_admin_secret: str | None = Header(default=None)
) -> dict:
    """Daily active users for last N days."""
    _check_admin(x_admin_secret)
    dau = reporter.get_daily_active_users(days=days)
    return {'days': days, 'data': dau}
