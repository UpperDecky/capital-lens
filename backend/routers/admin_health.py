"""Admin health routes for data quality dashboard."""
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException

from backend.database import get_connection
from backend.services.data_quality_monitor import monitor

router = APIRouter(prefix="/admin/health", tags=["admin"])

ADMIN_SECRET = __import__('os').getenv("ADMIN_SECRET", "")


def _check_admin(secret: str | None) -> None:
    if ADMIN_SECRET and secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Secret header")


@router.get("/ingestors")
def get_ingestors_health(x_admin_secret: str | None = Header(default=None)) -> dict:
    """Status of all ingestors."""
    _check_admin(x_admin_secret)

    ingestor_names = list(monitor.INGESTOR_INTERVALS.keys())
    results = {}
    for name in ingestor_names:
        results[name] = monitor.get_ingestor_status(name)

    # Summary counts
    ok = sum(1 for v in results.values() if v['status'] == 'success')
    failed = sum(1 for v in results.values() if v['status'] == 'failed')
    stalled = sum(1 for v in results.values() if v['status'] == 'stalled')
    never = sum(1 for v in results.values() if v['status'] == 'never_run')

    return {
        'summary': {
            'total': len(ingestor_names),
            'ok': ok,
            'failed': failed,
            'stalled': stalled,
            'never_run': never,
        },
        'ingestors': results,
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }


@router.get("/queue")
def get_enrichment_queue(x_admin_secret: str | None = Header(default=None)) -> dict:
    """Enrichment queue depth and status."""
    _check_admin(x_admin_secret)

    conn = get_connection()
    try:
        pending = conn.execute(
            "SELECT COUNT(*) FROM events WHERE enriched_at IS NULL"
        ).fetchone()[0]

        by_importance = conn.execute(
            """SELECT importance, COUNT(*) as count
               FROM events
               WHERE enriched_at IS NULL
               GROUP BY importance
               ORDER BY importance DESC"""
        ).fetchall()

        oldest = conn.execute(
            """SELECT id, headline, importance, ingested_at
               FROM events
               WHERE enriched_at IS NULL
               ORDER BY ingested_at ASC
               LIMIT 1"""
        ).fetchone()

        oldest_hours = None
        if oldest:
            try:
                ts = datetime.fromisoformat(oldest['ingested_at'].replace('Z', '+00:00'))
                oldest_hours = round(
                    (datetime.now(timezone.utc) - ts).total_seconds() / 3600, 2
                )
            except Exception:
                pass

        return {
            'total_pending': pending,
            'by_importance': {
                str(row['importance']): row['count'] for row in by_importance
            },
            'oldest_pending_age_hours': oldest_hours,
            'status': (
                'critical' if pending > 200
                else 'warning' if pending > 50
                else 'ok'
            ),
            'checked_at': datetime.now(timezone.utc).isoformat(),
        }
    finally:
        conn.close()


@router.get("/summary")
def get_health_summary(x_admin_secret: str | None = Header(default=None)) -> dict:
    """Overall data health snapshot."""
    _check_admin(x_admin_secret)
    return monitor.get_health_summary()


@router.get("/ingestors/{ingestor_name}")
def get_ingestor_detail(
    ingestor_name: str, x_admin_secret: str | None = Header(default=None)
) -> dict:
    """Last 10 runs for a specific ingestor."""
    _check_admin(x_admin_secret)
    runs = monitor.get_last_n_runs(ingestor_name, limit=10)
    return {
        'ingestor': ingestor_name,
        'runs': runs,
        'status': monitor.get_ingestor_status(ingestor_name),
    }
