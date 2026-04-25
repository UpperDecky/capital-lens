"""Feed router -- paginated event stream with flexible date range and importance filters."""
import csv
import io
import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from backend.database import get_connection
from backend.middleware.tier_tracking import (
    TIER_CONFIG,
    _reset_at_iso,
    get_daily_remaining,
    check_and_update_daily_limit,
    get_optional_user,
    get_tier,
)

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
        description="Minimum importance score (1=minimal ... 5=critical)",
    ),
    sort: Optional[str] = Query(
        "top",
        description="Sort order: 'top' = importance then date, 'recent' = newest ingested first",
    ),
    current_user: dict | None = Depends(get_optional_user),
) -> dict:
    tier = get_tier(current_user)
    cfg = TIER_CONFIG[tier]

    # Cap limit to tier page limit (None means no cap -- admin tier)
    page_limit = cfg["page_limit"]
    if page_limit is not None:
        limit = min(limit, page_limit)

    conn = get_connection()

    daily_remaining = None
    reset_at = None

    if tier == "free" and current_user:
        pre_remaining = get_daily_remaining(conn, current_user["id"])
        if pre_remaining == 0:
            conn.close()
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "daily_limit_reached",
                    "message": "You have reached your 20-event daily limit. Upgrade to Pro for unlimited access.",
                    "reset_at": _reset_at_iso(),
                },
            )
        limit = min(limit, pre_remaining)
        remaining_after, _ = check_and_update_daily_limit(conn, current_user["id"], limit)
        daily_remaining = remaining_after
        reset_at = _reset_at_iso()

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
        conditions.append("COALESCE(e.importance, 3) >= ?")
        params.append(min_importance)
    if date_from:
        dt_from = date_from if "T" in date_from else date_from + "T00:00:00"
        conditions.append("COALESCE(e.occurred_at, e.ingested_at) >= ?")
        params.append(dt_from)
    if date_to:
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

    if sort == "recent":
        order_by = "COALESCE(e.occurred_at, e.ingested_at) DESC"
    else:
        order_by = "COALESCE(e.importance, 3) DESC, COALESCE(e.occurred_at, e.ingested_at) DESC"

    rows = cur.execute(
        f"""SELECT e.*, en.name AS entity_name, en.type AS entity_type,
                   en.sector AS entity_sector
            FROM events e
            JOIN entities en ON e.entity_id = en.id
            {where_clause}
            ORDER BY {order_by}
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    events = []
    for row in rows:
        d = dict(row)
        raw_tags = d.get("sector_tags")
        if raw_tags:
            try:
                d["sector_tags"] = json.loads(raw_tags)
            except Exception:
                d["sector_tags"] = []
        else:
            d["sector_tags"] = []

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
        "tier": tier,
        "page_limit": page_limit,
        "daily_limit": cfg["daily_limit"],
        "daily_remaining": daily_remaining,
        "reset_at": reset_at,
    }


_EXPORT_COLS = [
    "occurred_at", "entity_name", "event_type", "headline",
    "amount", "currency", "importance", "sector_tags",
    "plain_english", "market_impact", "invest_signal", "source_url",
]


@router.get("/feed/export")
def export_feed(
    format: str = Query("csv", pattern="^(csv|json)$"),
    sector: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    min_importance: Optional[int] = Query(None, ge=1, le=5),
    sort: Optional[str] = Query("top"),
    current_user: dict | None = Depends(get_optional_user),
) -> Response:
    """Download the current filtered feed as CSV or JSON (max 500 rows, Pro only)."""
    tier = get_tier(current_user)
    if tier != "pro":
        raise HTTPException(
            status_code=403,
            detail="Feed export is a Pro feature. Upgrade to access CSV/JSON export.",
        )

    conn = get_connection()
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
        conditions.append("COALESCE(e.importance, 3) >= ?")
        params.append(min_importance)
    if date_from:
        dt_from = date_from if "T" in date_from else date_from + "T00:00:00"
        conditions.append("COALESCE(e.occurred_at, e.ingested_at) >= ?")
        params.append(dt_from)
    if date_to:
        dt_to = date_to if "T" in date_to else date_to + "T23:59:59"
        conditions.append("COALESCE(e.occurred_at, e.ingested_at) <= ?")
        params.append(dt_to)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order_by = (
        "COALESCE(e.occurred_at, e.ingested_at) DESC"
        if sort == "recent"
        else "COALESCE(e.importance, 3) DESC, COALESCE(e.occurred_at, e.ingested_at) DESC"
    )

    rows = conn.execute(
        f"""SELECT e.headline, en.name AS entity_name, e.event_type,
                   COALESCE(e.occurred_at, e.ingested_at) AS occurred_at,
                   e.amount, e.currency,
                   COALESCE(e.importance, 3) AS importance,
                   e.sector_tags, e.plain_english, e.market_impact,
                   e.invest_signal, e.source_url
            FROM events e
            JOIN entities en ON e.entity_id = en.id
            {where}
            ORDER BY {order_by}
            LIMIT 500""",
        params,
    ).fetchall()
    conn.close()

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if format == "json":
        records = []
        for r in rows:
            d = dict(r)
            raw = d.get("sector_tags")
            try:
                d["sector_tags"] = json.loads(raw) if raw else []
            except Exception:
                d["sector_tags"] = []
            records.append(d)
        body = json.dumps(records, indent=2, ensure_ascii=False)
        return Response(
            content=body,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="capital-lens-{date_str}.json"',
            },
        )

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=_EXPORT_COLS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        d = dict(r)
        raw = d.get("sector_tags")
        try:
            d["sector_tags"] = "|".join(json.loads(raw)) if raw else ""
        except Exception:
            d["sector_tags"] = ""
        writer.writerow(d)

    return Response(
        content=buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="capital-lens-{date_str}.csv"',
        },
    )
