"""Profile SQLite query performance."""
import time
from backend.database import get_connection


def profile_query(sql: str, params: tuple = ()) -> dict:
    """Run a query and return timing + explain plan info."""
    conn = get_connection()
    try:
        explain_rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}", params).fetchall()
        explain = [dict(r) for r in explain_rows]

        start = time.perf_counter()
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            'query': sql,
            'duration_ms': round(elapsed_ms, 3),
            'rows_returned': len(rows),
            'query_plan': explain,
        }
    finally:
        conn.close()


def run_all_profiles() -> list:
    """Profile all critical feed queries. Print results."""
    queries = [
        (
            "SELECT * FROM events WHERE importance >= ? ORDER BY ingested_at DESC LIMIT 20",
            (4,),
        ),
        (
            "SELECT * FROM events ORDER BY ingested_at DESC LIMIT 20",
            (),
        ),
        (
            "SELECT * FROM events WHERE entity_id = (SELECT id FROM entities LIMIT 1) "
            "ORDER BY ingested_at DESC LIMIT 20",
            (),
        ),
        (
            "SELECT COUNT(*) FROM events WHERE enriched_at IS NULL",
            (),
        ),
        (
            """SELECT e.id, e.headline, e.importance, ent.name, ent.sector
               FROM events e JOIN entities ent ON e.entity_id = ent.id
               WHERE e.importance >= ?
               ORDER BY e.ingested_at DESC LIMIT 20""",
            (3,),
        ),
    ]

    results = []
    for sql, params in queries:
        result = profile_query(sql, params)
        label = sql[:60].replace('\n', ' ')
        status = 'FAST' if result['duration_ms'] < 100 else 'SLOW'
        print(
            f"[{status}] {label}... "
            f"{result['duration_ms']:.1f}ms, {result['rows_returned']} rows"
        )
        results.append(result)

    return results


if __name__ == '__main__':
    run_all_profiles()
