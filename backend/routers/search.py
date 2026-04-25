"""Search router -- full-text search across events, entities, geo events, and prediction markets."""
import json
from fastapi import APIRouter, Query
from backend.database import get_connection

router = APIRouter()


@router.get("/search")
def search(q: str = Query(..., min_length=2)) -> dict:
    """
    Search financial events, entities, geopolitical events, and prediction markets.
    Returns up to 20 results per category.
    """
    conn = get_connection()
    cur = conn.cursor()
    pattern = f"%{q}%"

    # Financial events
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

    # Entities
    entity_rows = cur.execute(
        """SELECT * FROM entities
           WHERE name LIKE ? OR description LIKE ?
           LIMIT 10""",
        (pattern, pattern),
    ).fetchall()

    # Geopolitical events
    geo_rows = cur.execute(
        """SELECT id, iso2, headline, source,
                  COALESCE(occurred_at, ingested_at) AS occurred_at,
                  url, tone, themes
           FROM geo_events
           WHERE headline LIKE ? OR iso2 LIKE ? OR source LIKE ?
           ORDER BY occurred_at DESC
           LIMIT 10""",
        (pattern, pattern, pattern),
    ).fetchall()

    # Prediction markets (active only, ranked by volume)
    pred_rows = cur.execute(
        """SELECT id, question, yes_price, no_price, volume_usd,
                  category, active, fetched_at
           FROM prediction_markets
           WHERE question LIKE ? AND active = 1
           ORDER BY COALESCE(volume_usd, 0) DESC
           LIMIT 10""",
        (pattern,),
    ).fetchall()

    conn.close()

    # Parse financial events
    events = []
    for row in event_rows:
        d = dict(row)
        raw = d.get("sector_tags")
        try:
            d["sector_tags"] = json.loads(raw) if raw else []
        except Exception:
            d["sector_tags"] = []
        events.append(d)

    # Normalize geo_events to intel_type shape (for IntelCard reuse)
    geo_events = []
    for row in geo_rows:
        d = dict(row)
        raw = d.get("themes")
        try:
            d["themes"] = json.loads(raw) if raw else []
        except Exception:
            d["themes"] = []
        d["intel_type"] = "geo_event"
        tone = d.get("tone") or 0
        if tone < -8:
            d["importance"] = 5
        elif tone < -4:
            d["importance"] = 4
        elif tone > 4:
            d["importance"] = 2
        else:
            d["importance"] = 3
        geo_events.append(d)

    # Normalize prediction_markets to intel_type shape
    predictions = []
    for row in pred_rows:
        d = dict(row)
        d["intel_type"] = "prediction"
        d["headline"] = d.get("question", "")
        d["occurred_at"] = d.get("fetched_at")
        d["source"] = "Polymarket"
        vol = d.get("volume_usd") or 0
        d["importance"] = 4 if vol > 100_000 else 3 if vol > 10_000 else 2
        predictions.append(d)

    return {
        "query":       q,
        "events":      events,
        "entities":    [dict(r) for r in entity_rows],
        "geo_events":  geo_events,
        "predictions": predictions,
    }
