"""Themes router — aggregate sector signals from enriched events."""
import json
from fastapi import APIRouter
from backend.database import get_connection
from collections import Counter

router = APIRouter()


@router.get("/themes")
def get_themes() -> list[dict]:
    """
    Aggregate sector tags from enriched events.
    Returns top themes sorted by event count and total capital moved.
    """
    conn = get_connection()
    cur = conn.cursor()

    rows = cur.execute(
        """SELECT e.sector_tags, e.amount, en.sector,
                  e.invest_signal, e.market_impact
           FROM events e
           JOIN entities en ON e.entity_id = en.id
           WHERE e.enriched_at IS NOT NULL AND e.sector_tags IS NOT NULL"""
    ).fetchall()

    theme_map: dict[str, dict] = {}

    # Also build from entity sectors directly
    sector_rows = cur.execute(
        """SELECT en.sector, COUNT(*) as cnt, SUM(e.amount) as total_amount
           FROM events e JOIN entities en ON e.entity_id = en.id
           GROUP BY en.sector ORDER BY cnt DESC"""
    ).fetchall()

    for row in sector_rows:
        sector = row["sector"]
        if sector not in theme_map:
            theme_map[sector] = {
                "theme": sector,
                "event_count": 0,
                "total_capital": 0.0,
                "tags": [],
                "signals": [],
            }
        theme_map[sector]["event_count"] += row["cnt"]
        theme_map[sector]["total_capital"] += float(row["total_amount"] or 0)

    # Augment with AI-generated tags
    for row in rows:
        raw_tags = row["sector_tags"]
        try:
            tags = json.loads(raw_tags) if raw_tags else []
        except Exception:
            tags = []
        sector = row["sector"]
        if sector in theme_map:
            theme_map[sector]["tags"].extend(tags)
            if row["invest_signal"]:
                theme_map[sector]["signals"].append(row["invest_signal"])

    # Deduplicate tags and trim signals
    result = []
    for key, t in theme_map.items():
        top_tags = [tag for tag, _ in Counter(t["tags"]).most_common(5)]
        result.append({
            "theme": t["theme"],
            "event_count": t["event_count"],
            "total_capital": t["total_capital"],
            "top_tags": top_tags,
            "latest_signal": t["signals"][0] if t["signals"] else None,
        })

    result.sort(key=lambda x: x["event_count"], reverse=True)
    conn.close()
    return result[:15]
