"""Geo router -- world map country data, geopolitical events, and intelligence overlays."""
import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.database import get_connection

router = APIRouter(prefix="/geo")


@router.get("/countries")
def list_countries(
    conflict_status: Optional[str] = Query(None),
    continent: Optional[str] = Query(None),
) -> list[dict]:
    conn = get_connection()

    conditions = []
    params: list = []
    if conflict_status:
        conditions.append("conflict_status = ?")
        params.append(conflict_status)
    if continent:
        conditions.append("continent = ?")
        params.append(continent)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = conn.execute(
        f"SELECT * FROM countries {where} ORDER BY name",
        params,
    ).fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        for field in ("alliances", "key_issues"):
            raw = d.get(field)
            try:
                d[field] = json.loads(raw) if raw else []
            except Exception:
                d[field] = []
        results.append(d)
    return results


@router.get("/countries/{iso2}")
def get_country(iso2: str) -> dict:
    conn = get_connection()

    country = conn.execute(
        "SELECT * FROM countries WHERE iso2 = ?", (iso2.upper(),)
    ).fetchone()
    if not country:
        conn.close()
        raise HTTPException(status_code=404, detail="Country not found")

    d = dict(country)
    for field in ("alliances", "key_issues"):
        raw = d.get(field)
        try:
            d[field] = json.loads(raw) if raw else []
        except Exception:
            d[field] = []

    geo_rows = conn.execute(
        """SELECT * FROM geo_events WHERE iso2 = ?
           ORDER BY occurred_at DESC LIMIT 20""",
        (iso2.upper(),),
    ).fetchall()
    d["geo_events"] = [dict(r) for r in geo_rows]

    entity_rows = conn.execute(
        """SELECT e.headline, e.event_type, e.amount, e.occurred_at,
                  e.plain_english, en.name AS entity_name
           FROM events e
           JOIN entities en ON e.entity_id = en.id
           WHERE e.headline LIKE ? OR e.plain_english LIKE ?
           ORDER BY e.occurred_at DESC LIMIT 15""",
        (f"%{d['name']}%", f"%{d['name']}%"),
    ).fetchall()
    d["entity_events"] = [dict(r) for r in entity_rows]

    pred_rows = conn.execute(
        """SELECT id, question, yes_price, no_price, volume_usd
           FROM prediction_markets
           WHERE question LIKE ?
           ORDER BY volume_usd DESC LIMIT 5""",
        (f"%{d['name']}%",),
    ).fetchall()
    d["prediction_markets"] = [dict(r) for r in pred_rows]

    infra_rows = conn.execute(
        """SELECT id, outage_type, scope, cause, started_at
           FROM infra_events
           WHERE iso2 = ?
           ORDER BY started_at DESC LIMIT 5""",
        (iso2.upper(),),
    ).fetchall()
    d["infra_events"] = [dict(r) for r in infra_rows]

    conn.close()
    return d


@router.get("/events")
def list_geo_events(
    iso2: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
) -> list[dict]:
    conn = get_connection()
    if iso2:
        rows = conn.execute(
            "SELECT * FROM geo_events WHERE iso2 = ? ORDER BY occurred_at DESC LIMIT ?",
            (iso2.upper(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM geo_events ORDER BY occurred_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/summary")
def geo_summary() -> dict:
    """Counts per conflict_status for the map legend."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT conflict_status, COUNT(*) AS cnt FROM countries GROUP BY conflict_status"
    ).fetchall()
    conn.close()
    return {r["conflict_status"]: r["cnt"] for r in rows}


@router.get("/stats")
def geo_stats() -> dict:
    """Live counter data for the stats bar."""
    conn = get_connection()
    result: dict = {}

    rows = conn.execute(
        "SELECT conflict_status, COUNT(*) AS cnt FROM countries GROUP BY conflict_status"
    ).fetchall()
    counts = {r["conflict_status"]: r["cnt"] for r in rows}
    result["conflict_counts"] = counts
    result["active_conflicts"] = counts.get("war", 0) + counts.get("active_conflict", 0)

    result["events_24h"] = conn.execute(
        "SELECT COUNT(*) FROM geo_events WHERE occurred_at >= datetime('now', '-24 hours')"
    ).fetchone()[0]

    result["events_7d"] = conn.execute(
        "SELECT COUNT(*) FROM geo_events WHERE occurred_at >= datetime('now', '-7 days')"
    ).fetchone()[0]

    result["aircraft"] = conn.execute(
        "SELECT COUNT(DISTINCT icao24) FROM adsb_events "
        "WHERE occurred_at >= datetime('now', '-12 hours')"
    ).fetchone()[0]

    result["vessels"] = conn.execute(
        "SELECT COUNT(DISTINCT mmsi) FROM maritime_events "
        "WHERE occurred_at >= datetime('now', '-24 hours')"
    ).fetchone()[0]

    result["fires"] = conn.execute(
        "SELECT COUNT(*) FROM satellite_events "
        "WHERE acq_date >= date('now', '-7 days')"
    ).fetchone()[0]

    result["conflict_pins"] = conn.execute(
        "SELECT COUNT(*) FROM geo_events "
        "WHERE latitude IS NOT NULL AND longitude IS NOT NULL "
        "AND occurred_at >= datetime('now', '-14 days')"
    ).fetchone()[0]

    result["infra_events"] = conn.execute(
        "SELECT COUNT(*) FROM infra_events "
        "WHERE started_at >= datetime('now', '-24 hours')"
    ).fetchone()[0]

    result["prediction_markets"] = conn.execute(
        "SELECT COUNT(*) FROM prediction_markets"
    ).fetchone()[0]

    conn.close()
    return result


@router.get("/live")
def live_geo_events(
    limit: int = Query(120, le=300),
    hours: int = Query(96, ge=1, le=168),
    iso2: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
) -> list[dict]:
    """Recent geo events for the live ticker panel."""
    conn = get_connection()
    conditions = ["occurred_at >= datetime('now', ? || ' hours')"]
    params: list = [f"-{hours}"]
    if iso2:
        conditions.append("iso2 = ?")
        params.append(iso2.upper())
    if source:
        conditions.append("source = ?")
        params.append(source)
    where = "WHERE " + " AND ".join(conditions)
    rows = conn.execute(
        f"""SELECT id, iso2, headline, url, source, occurred_at, tone, themes,
                   latitude, longitude
            FROM geo_events {where}
            ORDER BY occurred_at DESC LIMIT ?""",
        [*params, limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/conflict-pins")
def conflict_pins(
    limit: int = Query(1000, le=2000),
    days: int = Query(14, ge=1, le=30),
) -> list[dict]:
    """Geo events with lat/lon coordinates for map pins (ACLED/UCDP/GDELT sources)."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, iso2, headline, source, occurred_at, tone, themes,
                  latitude, longitude
           FROM geo_events
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL
             AND occurred_at >= datetime('now', ? || ' days')
           ORDER BY occurred_at DESC LIMIT ?""",
        (f"-{days}", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/adsb")
def get_adsb_positions(
    limit: int = Query(2000, le=5000),
    hours: int = Query(12, ge=1, le=48),
) -> list[dict]:
    """Recent ADS-B aircraft positions for map overlay."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, icao24, callsign, origin_country, latitude, longitude,
                  altitude_m, velocity_ms, on_ground, occurred_at, entity_id
           FROM adsb_events
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL
             AND occurred_at >= datetime('now', ? || ' hours')
           ORDER BY occurred_at DESC
           LIMIT ?""",
        (f"-{hours}", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/maritime")
def get_maritime_positions(
    limit: int = Query(1000, le=3000),
    hours: int = Query(48, ge=1, le=72),
) -> list[dict]:
    """Recent maritime vessel positions for map overlay."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, mmsi, ship_name, ship_type, latitude, longitude,
                  speed_knots, flag_country, occurred_at
           FROM maritime_events
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL
             AND occurred_at >= datetime('now', ? || ' hours')
           ORDER BY occurred_at DESC
           LIMIT ?""",
        (f"-{hours}", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/fires")
def get_satellite_fires(
    limit: int = Query(2000, le=5000),
    days: int = Query(7, ge=1, le=14),
    confidence: Optional[str] = Query(None),
) -> list[dict]:
    """Recent satellite fire detections for map overlay."""
    conn = get_connection()
    conditions = [
        "latitude IS NOT NULL",
        "longitude IS NOT NULL",
        f"acq_date >= date('now', '-{days} days')",
    ]
    params: list = []
    if confidence:
        conditions.append("confidence = ?")
        params.append(confidence)
    where = "WHERE " + " AND ".join(conditions)
    rows = conn.execute(
        f"""SELECT id, source, latitude, longitude, brightness,
                   confidence, acq_date, country_iso2
            FROM satellite_events
            {where}
            ORDER BY acq_date DESC
            LIMIT ?""",
        [*params, limit],
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/entities")
def get_geo_entities() -> list[dict]:
    """Return all entities with inferred country_iso2 for map pinning.
    Uses country name matching against entity name to derive location.
    Defaults to US when no match is found."""
    conn = get_connection()
    entities = conn.execute(
        "SELECT id, name, type, sector FROM entities ORDER BY name"
    ).fetchall()
    country_rows = conn.execute("SELECT iso2, name FROM countries").fetchall()
    conn.close()

    country_name_map = {}
    for c in country_rows:
        country_name_map[c["name"].lower()] = c["iso2"]

    result = []
    for en in entities:
        name_lower = en["name"].lower()
        iso2 = None
        for cname, ciso2 in country_name_map.items():
            if cname in name_lower:
                iso2 = ciso2
                break
        result.append({
            "id": en["id"],
            "name": en["name"],
            "type": en["type"],
            "sector": en["sector"],
            "country_iso2": iso2 or "US",
        })
    return result


@router.get("/infra")
def get_infra_events(
    limit: int = Query(200, le=500),
    hours: int = Query(72, ge=1, le=168),
) -> list[dict]:
    """Infrastructure outage events for map overlay and ticker."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT id, outage_type, scope, cause, iso2, asn, started_at
           FROM infra_events
           WHERE started_at >= datetime('now', ? || ' hours')
           ORDER BY started_at DESC
           LIMIT ?""",
        (f"-{hours}", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/predictions")
def get_geo_predictions(
    limit: int = Query(50, le=200),
) -> list[dict]:
    """Top prediction markets by volume for the intelligence ticker."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT pm.id, pm.question, pm.yes_price, pm.no_price,
                  pm.volume_usd, pm.entity_id, en.name AS entity_name
           FROM prediction_markets pm
           LEFT JOIN entities en ON pm.entity_id = en.id
           ORDER BY pm.volume_usd DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
