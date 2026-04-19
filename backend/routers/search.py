"""Search router — full-text search across events and entities."""
import json
from fastapi import APIRouter, Query
from backend.database import get_connection

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=2)) -> dict:
    """
    Search events (headline, plain_english) and entities (name, description).
    Returns up to 20 combined results.
    """
    conn = get_connection()
    cur = conn.cursor()
    pattern = f"%{q}%"

    event_rows = cur.execute(
        """SELECT e.*, en.name AS entity_name, en.type AS entity_type,
                  en.sector AS entity_sector
           FROM events e
           JOIN entities en ON e.entity_id = en.id
           WHERE e.headline LIKE ?
              OR e.plain_english LIKE ?
              OR e.market_impact LIKE ?
              OR en.name LIKE ?
           ORDER BY e.occurred_at DESC
           LIMIT 20""",
        (pattern, pattern, pattern, pattern),
    ).fetchall()

    entity_rows = cur.execute(
        """SELECT * FROM entities
           WHERE name LIKE ? OR description LIKE ?
           LIMIT 10""",
        (pattern, pattern),
    ).fetchall()

    events = []
    for row in event_rows:
        d = dict(row)
        raw_tags = d.get("sector_tags")
        if raw_tags:
            try:
                d["sector_tags"] = json.loads(raw_tags)
            except Exception:
                d["sector_tags"] = []
        else:
            d["sector_tags"] = []
        events.append(d)

    conn.close()
    return {
        "query": q,
        "events": events,
        "entities": [dict(r) for r in entity_rows],
    }
