"""
ADS-B aircraft tracking ingestor — OpenSky Network.
Free REST API, no auth required for basic access.
Optional login in .env doubles the rate limit (10s → 5s between calls).
API docs: https://openskynetwork.github.io/opensky-api/rest.html
"""
import uuid
import httpx
from datetime import datetime, timezone
from typing import Any

from backend.config import OPENSKY_USERNAME, OPENSKY_PASSWORD

OPENSKY_BASE = "https://opensky-network.org/api"

HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept": "application/json",
}

# ICAO24 hex codes for aircraft linked to seed entities.
# Add more as you identify them (e.g. via planespotters.net lookup by owner).
# These are tracked with special interest regardless of where they are.
ENTITY_AIRCRAFT: dict[str, str] = {
    # icao24 → entity_name
    "a835af": "Elon Musk",   # N628TS — Musk's Gulfstream G650ER
    "a0b6fd": "Jeff Bezos",  # N271DV — Bezos's Gulfstream G650ER
    "a4f236": "Bill Gates",  # Cessna Citation Longitude (approximate)
    "c03029": "Elon Musk",   # N272BG — second Musk jet (Tesla / SpaceX ops)
}

# Bounding boxes for regions of geopolitical/market interest [lamin, lomin, lamax, lomax]
# We poll each region to get a snapshot of air traffic over it.
REGIONS: list[tuple[str, list[float]]] = [
    ("Taiwan Strait",         [21.0, 119.0, 26.0, 123.0]),
    ("Black Sea / Ukraine",   [44.0,  28.0, 48.0,  38.0]),
    ("Red Sea",               [12.0,  42.0, 28.0,  45.0]),
    ("Persian Gulf",          [24.0,  50.0, 28.0,  57.0]),
    ("South China Sea",       [5.0,  110.0, 22.0, 120.0]),
    ("Eastern Mediterranean", [30.0,  28.0, 38.0,  37.0]),
]


def _auth() -> tuple[str, str] | None:
    if OPENSKY_USERNAME and OPENSKY_PASSWORD:
        return (OPENSKY_USERNAME, OPENSKY_PASSWORD)
    return None


def _insert_snapshot(
    db_conn: Any,
    icao24: str,
    callsign: str | None,
    origin_country: str | None,
    lat: float | None,
    lon: float | None,
    alt_m: float | None,
    velocity: float | None,
    heading: float | None,
    on_ground: bool,
    timestamp: int,
    entity_name: str | None,
    entity_map: dict[str, str],
) -> bool:
    """Insert one aircraft snapshot. Returns True if inserted (not a duplicate)."""
    occurred_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
    now = datetime.now(timezone.utc).isoformat()

    # Deduplicate: same icao24 within the same minute is not re-inserted
    minute_prefix = occurred_at[:16]  # "YYYY-MM-DDTHH:MM"
    exists = db_conn.execute(
        "SELECT 1 FROM adsb_events WHERE icao24=? AND occurred_at LIKE ?",
        (icao24, minute_prefix + "%"),
    ).fetchone()
    if exists:
        return False

    entity_id: str | None = None
    if entity_name:
        entity_id = entity_map.get(entity_name)

    db_conn.execute(
        """INSERT INTO adsb_events
           (id, icao24, callsign, origin_country, latitude, longitude,
            altitude_m, velocity_ms, heading, on_ground, occurred_at, ingested_at, entity_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            str(uuid.uuid4()),
            icao24,
            (callsign or "").strip() or None,
            origin_country,
            lat,
            lon,
            alt_m,
            velocity,
            heading,
            1 if on_ground else 0,
            occurred_at,
            now,
            entity_id,
        ),
    )
    return True


def fetch_adsb_data(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    1. Fetch all tracked entity aircraft by ICAO24 globally.
    2. Fetch aircraft over each high-interest region.
    Stores snapshots in adsb_events table.
    Returns total new rows inserted.
    """
    auth = _auth()
    inserted = 0
    now_ts = int(datetime.now(timezone.utc).timestamp())

    with httpx.Client(headers=HEADERS, timeout=30, auth=auth) as client:  # type: ignore[arg-type]

        # ── 1. Track specific entity-linked aircraft ──────────────────────
        for icao24, entity_name in ENTITY_AIRCRAFT.items():
            try:
                resp = client.get(
                    f"{OPENSKY_BASE}/states/all",
                    params={"icao24": icao24},
                )
                resp.raise_for_status()
                data = resp.json()
                states = data.get("states") or []
                for sv in states:
                    ok = _insert_snapshot(
                        db_conn,
                        icao24=sv[0],
                        callsign=sv[1],
                        origin_country=sv[2],
                        lat=sv[6],
                        lon=sv[5],
                        alt_m=sv[7],
                        velocity=sv[9],
                        heading=sv[10],
                        on_ground=bool(sv[8]),
                        timestamp=sv[3] or now_ts,
                        entity_name=entity_name,
                        entity_map=entity_map,
                    )
                    if ok:
                        inserted += 1
            except Exception as exc:
                print(f"[ADS-B] Entity aircraft {icao24}: {exc}")

        # ── 2. Regional snapshots ─────────────────────────────────────────
        for region_name, bbox in REGIONS:
            try:
                resp = client.get(
                    f"{OPENSKY_BASE}/states/all",
                    params={
                        "lamin": bbox[0],
                        "lomin": bbox[1],
                        "lamax": bbox[2],
                        "lomax": bbox[3],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                states = data.get("states") or []

                # Only snapshot military/interesting callsigns or cap at 20 per region
                count = 0
                for sv in states:
                    if count >= 20:
                        break
                    callsign = (sv[1] or "").strip()
                    # Only store if callsign looks like a military/government/cargo flight
                    # or if the region itself is a high-tension zone (store all then)
                    ok = _insert_snapshot(
                        db_conn,
                        icao24=sv[0],
                        callsign=callsign,
                        origin_country=sv[2],
                        lat=sv[6],
                        lon=sv[5],
                        alt_m=sv[7],
                        velocity=sv[9],
                        heading=sv[10],
                        on_ground=bool(sv[8]),
                        timestamp=sv[3] or now_ts,
                        entity_name=None,
                        entity_map=entity_map,
                    )
                    if ok:
                        inserted += 1
                        count += 1

                total_in_region = len(states)
                print(
                    f"[ADS-B] {region_name}: {total_in_region} aircraft in zone, "
                    f"{count} new snapshots stored"
                )

            except Exception as exc:
                print(f"[ADS-B] Region {region_name}: {exc}")

    if inserted:
        db_conn.commit()
        print(f"[ADS-B] ✓ Total {inserted} new snapshots stored")
    return inserted
