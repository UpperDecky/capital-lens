"""Entities router — browse and profile views."""
import json
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.database import get_connection

router = APIRouter()


@router.get("/entities")
def list_entities(
    type: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    conditions: list[str] = []
    params: list = []

    if type:
        conditions.append("type = ?")
        params.append(type)
    if sector:
        conditions.append("sector = ?")
        params.append(sector)
    if q:
        conditions.append("(name LIKE ? OR description LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = cur.execute(
        f"SELECT * FROM entities {where_clause} ORDER BY net_worth DESC",
        params,
    ).fetchall()

    conn.close()
    return [dict(r) for r in rows]


@router.get("/entities/{entity_id}")
def get_entity(entity_id: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    entity = cur.execute(
        "SELECT * FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    if not entity:
        conn.close()
        raise HTTPException(status_code=404, detail="Entity not found")

    events = cur.execute(
        """SELECT * FROM events WHERE entity_id = ?
           ORDER BY occurred_at DESC LIMIT 20""",
        (entity_id,),
    ).fetchall()

    parsed_events = []
    for row in events:
        d = dict(row)
        raw_tags = d.get("sector_tags")
        if raw_tags:
            try:
                d["sector_tags"] = json.loads(raw_tags)
            except Exception:
                d["sector_tags"] = []
        else:
            d["sector_tags"] = []
        parsed_events.append(d)

    conn.close()
    return {
        **dict(entity),
        "events": parsed_events,
    }


@router.get("/entities/{entity_id}/portfolio")
def get_entity_portfolio(entity_id: str) -> dict:
    """
    Aggregate investment exposure for an entity.
    Returns sector lean, event type mix, largest capital moves,
    and congressional trade buy/sell breakdown.
    """
    conn = get_connection()
    cur = conn.cursor()

    entity = cur.execute(
        "SELECT id, name, type FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    if not entity:
        conn.close()
        raise HTTPException(status_code=404, detail="Entity not found")

    # Pull all events — only the fields we need
    rows = cur.execute(
        """SELECT event_type, amount, currency, headline, sector_tags, occurred_at
           FROM events WHERE entity_id = ?
           ORDER BY occurred_at DESC""",
        (entity_id,),
    ).fetchall()

    sector_counts: dict[str, int]   = defaultdict(int)
    sector_amounts: dict[str, float] = defaultdict(float)
    event_type_counts: dict[str, int] = defaultdict(int)
    total_capital = 0.0

    for row in rows:
        d = dict(row)
        et = d.get("event_type") or "unknown"
        event_type_counts[et] += 1

        amount: float = d.get("amount") or 0.0
        total_capital += amount

        raw_tags = d.get("sector_tags")
        if raw_tags:
            try:
                tags: list[str] = json.loads(raw_tags)
                for tag in tags:
                    if tag:
                        sector_counts[tag] += 1
                        sector_amounts[tag] += amount
            except Exception:
                pass

    # Top 5 events by dollar amount
    top_events_rows = cur.execute(
        """SELECT headline, event_type, amount, currency, occurred_at
           FROM events
           WHERE entity_id = ? AND amount IS NOT NULL AND amount > 0
           ORDER BY amount DESC
           LIMIT 5""",
        (entity_id,),
    ).fetchall()

    # Congressional trade buy vs sell split
    congress_rows = cur.execute(
        """SELECT headline FROM events
           WHERE entity_id = ? AND event_type = 'congressional_trade'""",
        (entity_id,),
    ).fetchall()

    buys = 0
    sells = 0
    for r in congress_rows:
        hl = (r["headline"] or "").lower()
        if "purchase" in hl or "buy" in hl or "bought" in hl:
            buys += 1
        elif "sale" in hl or "sell" in hl or "sold" in hl:
            sells += 1

    conn.close()

    # Sort sector exposure by event count desc
    sector_exposure = sorted(
        [
            {
                "sector": k,
                "count": sector_counts[k],
                "amount": round(sector_amounts[k], 2),
            }
            for k in sector_counts
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    event_breakdown = sorted(
        [{"event_type": k, "count": v} for k, v in event_type_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    return {
        "entity_id": entity_id,
        "total_events": len(rows),
        "total_capital_tracked": round(total_capital, 2),
        "sector_exposure": sector_exposure,
        "event_breakdown": event_breakdown,
        "top_events": [dict(r) for r in top_events_rows],
        "congressional_trades": {
            "total": len(congress_rows),
            "buys": buys,
            "sells": sells,
        },
    }
