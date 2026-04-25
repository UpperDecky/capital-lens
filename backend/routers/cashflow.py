"""Cash Flow router -- global capital movement feed and statistics."""
from typing import Optional
from fastapi import APIRouter, Query
from backend.database import get_connection

router = APIRouter(prefix="/cashflow", tags=["cashflow"])

_VALID_FLOW_TYPES = {
    "crypto_whale", "ofac_sanction", "vc_deal",
    "fec_dark_money", "cross_border", "seizure",
}


@router.get("")
def get_cash_flows(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    flow_type: Optional[str] = Query(None),
    asset: Optional[str] = Query(None),
    country: Optional[str] = Query(None, description="ISO2 -- filter by source or dest country"),
    min_amount: Optional[float] = Query(None),
    sort: Optional[str] = Query("recent", description="recent | largest"),
) -> dict:
    """Paginated cash flow list with optional filters."""
    conn   = get_connection()
    offset = (page - 1) * limit

    conditions: list[str] = []
    params: list = []

    if flow_type and flow_type in _VALID_FLOW_TYPES:
        conditions.append("flow_type = ?")
        params.append(flow_type)
    if asset:
        conditions.append("UPPER(asset) = UPPER(?)")
        params.append(asset)
    if country:
        conditions.append("(source_country = ? OR dest_country = ?)")
        params.extend([country, country])
    if min_amount is not None:
        conditions.append("amount_usd >= ?")
        params.append(min_amount)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total = conn.execute(
        f"SELECT COUNT(*) FROM cash_flows {where}", params
    ).fetchone()[0]

    order = "amount_usd DESC" if sort == "largest" else "occurred_at DESC"

    rows = conn.execute(
        f"""SELECT * FROM cash_flows {where}
            ORDER BY {order}
            LIMIT ? OFFSET ?""",
        [*params, limit, offset],
    ).fetchall()

    conn.close()
    return {
        "flows":    [dict(r) for r in rows],
        "page":     page,
        "limit":    limit,
        "total":    total,
        "has_more": (offset + limit) < total,
    }


@router.get("/live")
def get_live_flows(
    limit: int = Query(50, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168),
) -> list[dict]:
    """
    Return the most recent flows for the animated map.
    Defaults to last 24 h, up to 50 records.
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM cash_flows
           WHERE occurred_at >= datetime('now', ? || ' hours')
           ORDER BY occurred_at DESC
           LIMIT ?""",
        (f"-{hours}", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/stats")
def get_flow_stats() -> dict:
    """Aggregate stats for the Cash Flow dashboard."""
    conn = get_connection()

    # Overall totals
    totals = conn.execute(
        """SELECT
               COUNT(*) AS total_flows,
               COALESCE(SUM(amount_usd), 0) AS total_volume_usd,
               COALESCE(SUM(CASE WHEN occurred_at >= datetime('now', '-1 day')
                            THEN amount_usd ELSE 0 END), 0) AS volume_24h,
               COALESCE(SUM(CASE WHEN occurred_at >= datetime('now', '-7 days')
                            THEN amount_usd ELSE 0 END), 0) AS volume_7d
           FROM cash_flows"""
    ).fetchone()

    # By flow type
    type_rows = conn.execute(
        """SELECT flow_type,
                  COUNT(*) AS cnt,
                  COALESCE(SUM(amount_usd), 0) AS volume_usd
           FROM cash_flows
           GROUP BY flow_type
           ORDER BY volume_usd DESC"""
    ).fetchall()

    # By asset
    asset_rows = conn.execute(
        """SELECT asset,
                  COUNT(*) AS cnt,
                  COALESCE(SUM(amount_usd), 0) AS volume_usd
           FROM cash_flows
           WHERE asset IS NOT NULL
           GROUP BY asset
           ORDER BY volume_usd DESC
           LIMIT 10"""
    ).fetchall()

    # Top destination countries
    dest_rows = conn.execute(
        """SELECT dest_country AS country,
                  COUNT(*) AS cnt,
                  COALESCE(SUM(amount_usd), 0) AS volume_usd
           FROM cash_flows
           WHERE dest_country IS NOT NULL AND dest_country != 'XX'
           GROUP BY dest_country
           ORDER BY cnt DESC
           LIMIT 10"""
    ).fetchall()

    # Top source countries
    src_rows = conn.execute(
        """SELECT source_country AS country,
                  COUNT(*) AS cnt,
                  COALESCE(SUM(amount_usd), 0) AS volume_usd
           FROM cash_flows
           WHERE source_country IS NOT NULL AND source_country != 'XX'
           GROUP BY source_country
           ORDER BY cnt DESC
           LIMIT 10"""
    ).fetchall()

    conn.close()
    return {
        "total_flows":     totals["total_flows"],
        "total_volume_usd": totals["total_volume_usd"],
        "volume_24h":      totals["volume_24h"],
        "volume_7d":       totals["volume_7d"],
        "by_type":         [dict(r) for r in type_rows],
        "by_asset":        [dict(r) for r in asset_rows],
        "top_dest":        [dict(r) for r in dest_rows],
        "top_source":      [dict(r) for r in src_rows],
    }


@router.get("/volume")
def get_volume_timeseries(
    days: int = Query(7, ge=1, le=90),
    flow_type: Optional[str] = Query(None),
) -> list[dict]:
    """Hourly volume timeseries for sparkline charts."""
    conn = get_connection()
    conditions = [f"occurred_at >= datetime('now', '-{days} days')"]
    params: list = []
    if flow_type and flow_type in _VALID_FLOW_TYPES:
        conditions.append("flow_type = ?")
        params.append(flow_type)

    where = "WHERE " + " AND ".join(conditions)
    rows = conn.execute(
        f"""SELECT strftime('%Y-%m-%dT%H:00:00', occurred_at) AS hour,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(amount_usd), 0) AS volume_usd
            FROM cash_flows
            {where}
            GROUP BY hour
            ORDER BY hour ASC""",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
