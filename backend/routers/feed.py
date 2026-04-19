"""Feed router — paginated event stream with flexible date range and importance filters."""
import json
from typing import Optional
from fastapi import APIRouter, Query
from backend.database import get_connection

router = APIRouter()


@router.get("/feed")
def get_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),
    sector: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    date_from: Optional[str] = Query(
        None,
        description="Show events on or after this date (YYYY-MM-DD or full ISO datetime)",
    ),
    date_to: Optional[str] = Query(
        None,
        description="Show events on or before this date (YYYY-MM-DD or full ISO datetime)",
    ),
    min_importance: Optional[int] = Query(
        None, ge=1, le=5,
        description="Minimum importance score (1=minimal … 5=critical)",
    ),
) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    offset = (page - 1) * limit

    conditions: list[str] = []
    params: list = []

    if sector:
        conditions.append("en.sector = ?")
        params.append(sector)
    if type:
        conditions.append("e.event_type = ?")
        params.append(type)
    if min_amount is not None:
        conditions.append("e.amount >= ?")
        params.append(min_amount)
    if min_importance is not None:
        # COALESCE so unenriched events (NULL importance) default to 3
        conditions.append("COALESCE(e.importance, 3) >= ?")
        params.append(min_importance)
    if date_from:
        # If only a date is given (no time), treat it as start-of-day
        dt_from = date_from if "T" in date_from else date_from + "T00:00:00"
        conditions.append("COALESCE(e.occurred_at, e.ingested_at) >= ?")
        params.append(dt_from)
    if date_to:
        # Include the full end day
        dt_to = date_to if "T" in date_to else date_to + "T23:59:59"
        conditions.append("COALESCE(e.occurred_at, e.ingested_at) <= ?")
        params.append(dt_to)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total_row = cur.execute(
        f"""SELECT COUNT(*) FROM events e
            JOIN entities en ON e.entity_id = en.id
            {where_clause}""",
        params,
    ).fetchone()
    total = total_row[0] if total_row else 0

    rows = cur.execute(
        f"""SELECT e.*, en.name AS entity_name, en.type AS entity_type,
                   en.sector AS entity_sector
            FROM events e
            JOIN entities en ON e.entity_id = en.id
            {where_clause}
            ORDER BY COALESCE(e.importance, 3) DESC,
                     COALESCE(e.occurred_at, e.ingested_at) DESC
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    events = []
    for row in rows:
        d = dict(row)
        # Parse sector_tags JSON string → list
        raw_tags = d.get("sector_tags")
        if raw_tags:
            try:
                d["sector_tags"] = json.loads(raw_tags)
            except Exception:
                d["sector_tags"] = []
        else:
            d["sector_tags"] = []

        # Parse analysis JSON string → dict (or None)
        raw_analysis = d.get("analysis")
        if raw_analysis:
            try:
                d["analysis"] = json.loads(raw_analysis)
            except Exception:
                d["analysis"] = None
        else:
            d["analysis"] = None

        events.append(d)

    conn.close()
    return {
        "events": events,
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": (offset + limit) < total,
        "date_from": date_from,
        "date_to": date_to,
    }
