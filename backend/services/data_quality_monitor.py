"""Data quality monitoring service for Capital Lens ingestors."""
import uuid
import time
from datetime import datetime, timezone, timedelta
from backend.database import get_connection


class IngestorMonitor:
    """Track ingestor performance and health."""

    INGESTOR_INTERVALS = {
        'edgar':        15,
        'rss':          10,
        'market':       360,
        'congress':     360,
        'usaspending':  720,
        'fred':         360,
        'fec':          1440,
        'polygon':      30,
        'gdelt':        180,
        'adsb':         30,
        'maritime':     15,
        'geopolitical': 360,
        'satellite':    180,
        'infrastructure': 15,
        'prediction':   10,
        'telegram':     60,
        'enrich':       5,
        'valuation':    360,
        'connections':  360,
        'onchain':      5,
        'ofac':         60,
        'vcflow':       360,
    }

    def log_ingestor_start(self, ingestor_name: str) -> str:
        """Log start of ingestor run. Return run_id."""
        conn = get_connection()
        run_id = str(uuid.uuid4())
        try:
            conn.execute(
                """INSERT INTO ingestor_runs
                   (id, ingestor_name, started_at, status)
                   VALUES (?, ?, ?, ?)""",
                (run_id, ingestor_name, datetime.now(timezone.utc).isoformat(), 'running')
            )
            conn.commit()
        except Exception as exc:
            print(f"[Monitor] Failed to log start: {exc}")
        finally:
            conn.close()
        return run_id

    def log_ingestor_success(
        self,
        run_id: str,
        events_fetched: int,
        events_inserted: int,
        duration_seconds: float,
        api_response_time_ms: int = None,
    ) -> None:
        """Log successful ingestor completion."""
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE ingestor_runs
                   SET status=?, events_fetched=?, events_inserted=?,
                       completed_at=?, run_duration_seconds=?, api_response_time_ms=?
                   WHERE id=?""",
                (
                    'success',
                    events_fetched,
                    events_inserted,
                    datetime.now(timezone.utc).isoformat(),
                    duration_seconds,
                    api_response_time_ms,
                    run_id,
                )
            )
            conn.commit()
        except Exception as exc:
            print(f"[Monitor] Failed to log success: {exc}")
        finally:
            conn.close()

    def log_ingestor_failure(
        self, run_id: str, error_message: str, duration_seconds: float
    ) -> None:
        """Log failed ingestor run."""
        conn = get_connection()
        try:
            conn.execute(
                """UPDATE ingestor_runs
                   SET status=?, error_message=?, completed_at=?, run_duration_seconds=?
                   WHERE id=?""",
                (
                    'failed',
                    error_message[:500],
                    datetime.now(timezone.utc).isoformat(),
                    duration_seconds,
                    run_id,
                )
            )
            conn.commit()
        except Exception as exc:
            print(f"[Monitor] Failed to log failure: {exc}")
        finally:
            conn.close()

    def get_last_n_runs(self, ingestor_name: str, limit: int = 10) -> list:
        """Get last N runs for an ingestor."""
        conn = get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM ingestor_runs
                   WHERE ingestor_name=?
                   ORDER BY started_at DESC
                   LIMIT ?""",
                (ingestor_name, limit)
            ).fetchall()
            return [dict(row) for row in rows]
        except Exception:
            return []
        finally:
            conn.close()

    def get_ingestor_status(self, ingestor_name: str) -> dict:
        """Get current status for a single ingestor."""
        runs = self.get_last_n_runs(ingestor_name, limit=3)
        if not runs:
            return {'status': 'never_run', 'last_run_minutes_ago': None, 'error': None}

        latest = runs[0]
        expected_interval = self.INGESTOR_INTERVALS.get(ingestor_name, 60)

        try:
            ts = datetime.fromisoformat(latest['started_at'].replace('Z', '+00:00'))
            minutes_ago = (datetime.now(timezone.utc) - ts).total_seconds() / 60
        except Exception:
            minutes_ago = None

        # Determine health status
        if latest['status'] == 'failed':
            health = 'failed'
        elif minutes_ago is not None and minutes_ago > expected_interval * 2:
            health = 'stalled'
        else:
            health = latest['status']

        # Count consecutive failures
        consecutive_failures = 0
        for run in runs:
            if run['status'] == 'failed':
                consecutive_failures += 1
            else:
                break

        return {
            'status': health,
            'last_run_minutes_ago': round(minutes_ago, 1) if minutes_ago is not None else None,
            'events_inserted': latest.get('events_inserted', 0),
            'duration_seconds': latest.get('run_duration_seconds'),
            'api_response_time_ms': latest.get('api_response_time_ms'),
            'error': latest.get('error_message'),
            'consecutive_failures': consecutive_failures,
            'history': [
                {
                    'status': r['status'],
                    'inserted': r.get('events_inserted', 0),
                    'duration': r.get('run_duration_seconds'),
                    'started_at': r.get('started_at'),
                }
                for r in runs[:5]
            ],
        }

    def get_health_summary(self) -> dict:
        """Get overall data health snapshot."""
        conn = get_connection()
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            recent_runs = conn.execute(
                """SELECT ingestor_name, status, COUNT(*) as count
                   FROM ingestor_runs
                   WHERE started_at > ?
                   GROUP BY ingestor_name, status""",
                (cutoff,)
            ).fetchall()

            pending_count = conn.execute(
                "SELECT COUNT(*) FROM events WHERE enriched_at IS NULL"
            ).fetchone()[0]

            pending_high = conn.execute(
                "SELECT COUNT(*) FROM events WHERE enriched_at IS NULL AND importance >= 4"
            ).fetchone()[0]

            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            total_entities = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]

        except Exception as exc:
            return {'error': str(exc)}
        finally:
            conn.close()

        return {
            'recent_runs': [dict(row) for row in recent_runs],
            'enrichment_queue': {
                'total_pending': pending_count,
                'high_priority_pending': pending_high,
                'status': 'critical' if pending_count > 200 else 'warning' if pending_count > 50 else 'ok',
            },
            'database': {
                'total_events': total_events,
                'total_entities': total_entities,
            },
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }


# Global singleton
monitor = IngestorMonitor()


def wrapped_ingestor(ingestor_func, ingestor_name: str, *args, **kwargs):
    """Wrap ingestor function to log performance metrics automatically."""
    run_id = monitor.log_ingestor_start(ingestor_name)
    start_time = time.time()

    try:
        result = ingestor_func(*args, **kwargs)
        elapsed = time.time() - start_time
        api_duration_ms = int(elapsed * 1000)

        # Handle both int returns and dict returns
        if isinstance(result, dict):
            fetched = result.get('fetched', result.get('inserted', 0))
            inserted = result.get('inserted', 0)
        else:
            fetched = int(result) if result is not None else 0
            inserted = fetched

        monitor.log_ingestor_success(
            run_id,
            events_fetched=fetched,
            events_inserted=inserted,
            duration_seconds=elapsed,
            api_response_time_ms=api_duration_ms,
        )
        return inserted

    except Exception as exc:
        elapsed = time.time() - start_time
        monitor.log_ingestor_failure(run_id, str(exc), elapsed)
        print(f"[{ingestor_name}] Error (monitored): {str(exc)[:100]}")
        return 0
