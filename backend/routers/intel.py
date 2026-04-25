"""
Intel feed router -- unified stream of geo, ADS-B, maritime, satellite, and prediction events.
Separate from /feed which covers financial events only.
"""
import json
from typing import Optional
from fastapi import APIRouter, Query
from backend.database import get_connection

router = APIRouter()

# Normalised UNION across all 5 intelligence tables.
# Every branch must expose the same column list in the same order.
_UNION = """
SELECT
    id, intel_type, headline, occurred_at, source, iso2,
    lat, lon, importance, tone, url,
    callsign, altitude_m, on_ground,
    ship_name, ship_type, speed_knots, destination,
    brightness, confidence,
    question, yes_price, no_price, volume_usd,
    themes, entity_id
FROM (

    -- Geopolitical news (GDELT / ACLED / UCDP / Telegram / Cloudflare)
    SELECT
        id,
        'geo_event'                                          AS intel_type,
        headline,
        COALESCE(occurred_at, ingested_at)                   AS occurred_at,
        source,
        iso2,
        NULL                                                 AS lat,
        NULL                                                 AS lon,
        CASE
            WHEN tone < -8  THEN 5
            WHEN tone < -4  THEN 4
            WHEN tone > 4   THEN 2
            ELSE 3
        END                                                  AS importance,
        tone,
        url,
        NULL AS callsign,   NULL AS altitude_m,  NULL AS on_ground,
        NULL AS ship_name,  NULL AS ship_type,   NULL AS speed_knots,  NULL AS destination,
        NULL AS brightness, NULL AS confidence,
        NULL AS question,   NULL AS yes_price,   NULL AS no_price,     NULL AS volume_usd,
        themes,
        NULL AS entity_id
    FROM geo_events

    UNION ALL

    -- ADS-B aircraft snapshots (OpenSky Network)
    SELECT
        id,
        'adsb'                                               AS intel_type,
        COALESCE(callsign, 'Unknown') || ' over ' || COALESCE(origin_country, 'Unknown') AS headline,
        occurred_at,
        'OpenSky'                                            AS source,
        NULL                                                 AS iso2,
        latitude                                             AS lat,
        longitude                                            AS lon,
        CASE WHEN entity_id IS NOT NULL THEN 3 ELSE 2 END   AS importance,
        NULL AS tone, NULL AS url,
        callsign, altitude_m, on_ground,
        NULL AS ship_name, NULL AS ship_type, NULL AS speed_knots, NULL AS destination,
        NULL AS brightness, NULL AS confidence,
        NULL AS question, NULL AS yes_price, NULL AS no_price, NULL AS volume_usd,
        NULL AS themes,
        entity_id
    FROM adsb_events

    UNION ALL

    -- Maritime AIS vessel snapshots (aisstream.io)
    SELECT
        id,
        'maritime'                                           AS intel_type,
        COALESCE(ship_name, mmsi) || ' -- ' || COALESCE(ship_type, 'vessel') AS headline,
        occurred_at,
        'AISStream'                                          AS source,
        flag_country                                         AS iso2,
        latitude                                             AS lat,
        longitude                                            AS lon,
        2                                                    AS importance,
        NULL AS tone, NULL AS url,
        NULL AS callsign, NULL AS altitude_m, NULL AS on_ground,
        ship_name, ship_type, speed_knots, destination,
        NULL AS brightness, NULL AS confidence,
        NULL AS question, NULL AS yes_price, NULL AS no_price, NULL AS volume_usd,
        NULL AS themes,
        NULL AS entity_id
    FROM maritime_events

    UNION ALL

    -- Satellite fire detections (NASA FIRMS)
    SELECT
        id,
        'satellite'                                          AS intel_type,
        source || ' fire -- ' || COALESCE(country_iso2, 'unknown') || ' [' || COALESCE(confidence, 'nominal') || ']' AS headline,
        acq_date                                             AS occurred_at,
        source                                               AS source,
        country_iso2                                         AS iso2,
        latitude                                             AS lat,
        longitude                                            AS lon,
        CASE confidence WHEN 'high' THEN 3 ELSE 2 END        AS importance,
        NULL AS tone, NULL AS url,
        NULL AS callsign, NULL AS altitude_m, NULL AS on_ground,
        NULL AS ship_name, NULL AS ship_type, NULL AS speed_knots, NULL AS destination,
        brightness, confidence,
        NULL AS question, NULL AS yes_price, NULL AS no_price, NULL AS volume_usd,
        NULL AS themes,
        NULL AS entity_id
    FROM satellite_events

    UNION ALL

    -- Prediction markets (Polymarket)
    SELECT
        id,
        'prediction'                                         AS intel_type,
        question                                             AS headline,
        fetched_at                                           AS occurred_at,
        'Polymarket'                                         AS source,
        NULL                                                 AS iso2,
        NULL                                                 AS lat,
        NULL                                                 AS lon,
        CASE
            WHEN volume_usd > 100000 THEN 4
            WHEN volume_usd > 10000  THEN 3
            ELSE 2
        END                                                  AS importance,
        NULL AS tone, NULL AS url,
        NULL AS callsign, NULL AS altitude_m, NULL AS on_ground,
        NULL AS ship_name, NULL AS ship_type, NULL AS speed_knots, NULL AS destination,
        NULL AS brightness, NULL AS confidence,
        question, yes_price, no_price, volume_usd,
        NULL AS themes,
        entity_id
    FROM prediction_markets
    WHERE active = 1
)
"""


@router.get("/feed/intel")
def get_intel_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    intel_type: Optional[str] = Query(
        None,
        description="Filter: geo_event | adsb | maritime | satellite | prediction",
    ),
    iso2: Optional[str] = Query(None, description="Filter by ISO2 country code"),
    sort: Optional[str] = Query("recent", description="recent | top"),
) -> dict:
    conn = get_connection()
    offset = (page - 1) * limit

    conditions: list[str] = []
    params: list = []

    if intel_type:
        conditions.append("intel_type = ?")
        params.append(intel_type)
    if iso2:
        conditions.append("iso2 = ?")
        params.append(iso2.upper())

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    order_by = (
        "importance DESC, occurred_at DESC"
        if sort == "top"
        else "occurred_at DESC"
    )

    total = conn.execute(
        f"SELECT COUNT(*) FROM ({_UNION}) {where}", params
    ).fetchone()[0]

    rows = conn.execute(
        f"SELECT * FROM ({_UNION}) {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    events = []
    for row in rows:
        d = dict(row)
        raw_themes = d.get("themes")
        if raw_themes:
            try:
                d["themes"] = json.loads(raw_themes)
            except Exception:
                d["themes"] = []
        else:
            d["themes"] = []
        events.append(d)

    conn.close()
    return {
        "events":   events,
        "page":     page,
        "limit":    limit,
        "total":    total,
        "has_more": (offset + limit) < total,
    }


@router.get("/feed/alerts")
def get_alerts(
    since: Optional[str] = Query(
        None,
        description="ISO timestamp -- return events after this time. Defaults to last 24 h.",
    ),
    limit: int = Query(30, le=50),
) -> list[dict]:
    """High-importance events (score >= 4) from both financial and intel streams."""
    from datetime import datetime, timezone, timedelta

    if not since:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    conn = get_connection()

    # Intel stream -- geo events and prediction markets can reach importance 4+
    intel_rows = conn.execute(
        f"""SELECT id, intel_type, headline, occurred_at, source, iso2,
                   importance, url, NULL AS entity_name
            FROM ({_UNION})
            WHERE importance >= 4 AND occurred_at >= ?
            ORDER BY occurred_at DESC
            LIMIT ?""",
        [since, limit],
    ).fetchall()

    # Financial stream
    fin_rows = conn.execute(
        """SELECT e.id,
                  'financial'                                       AS intel_type,
                  e.headline,
                  COALESCE(e.occurred_at, e.ingested_at)           AS occurred_at,
                  e.source_name                                     AS source,
                  NULL                                              AS iso2,
                  COALESCE(e.importance, 3)                        AS importance,
                  e.source_url                                      AS url,
                  en.name                                           AS entity_name
           FROM events e
           JOIN entities en ON e.entity_id = en.id
           WHERE COALESCE(e.importance, 3) >= 4
             AND COALESCE(e.occurred_at, e.ingested_at) >= ?
           ORDER BY COALESCE(e.occurred_at, e.ingested_at) DESC
           LIMIT ?""",
        [since, limit],
    ).fetchall()

    conn.close()

    merged = [dict(r) for r in intel_rows] + [dict(r) for r in fin_rows]
    merged.sort(key=lambda x: x.get("occurred_at") or "", reverse=True)
    return merged[:limit]


@router.get("/feed/intel/counts")
def get_intel_counts() -> dict:
    """Row counts per intel type -- used for the tab badges."""
    conn = get_connection()
    tables = {
        "geo_event":  "SELECT COUNT(*) FROM geo_events",
        "adsb":       "SELECT COUNT(*) FROM adsb_events",
        "maritime":   "SELECT COUNT(*) FROM maritime_events",
        "satellite":  "SELECT COUNT(*) FROM satellite_events",
        "prediction": "SELECT COUNT(*) FROM prediction_markets WHERE active=1",
    }
    counts = {}
    for key, sql in tables.items():
        try:
            counts[key] = conn.execute(sql).fetchone()[0]
        except Exception:
            counts[key] = 0
    counts["total"] = sum(counts.values())
    conn.close()
    return counts
