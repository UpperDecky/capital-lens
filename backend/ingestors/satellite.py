"""
NASA FIRMS (Fire Information for Resource Management System) satellite ingestor.
Detects active fires globally from VIIRS and MODIS satellites.
Free MAP_KEY — register at https://firms.modaps.eosdis.nasa.gov/api/
5,000 transactions per 10-minute window. Global data within 3 hours of observation.
API docs: https://firms.modaps.eosdis.nasa.gov/api/area/
"""
import csv
import io
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import NASA_FIRMS_MAP_KEY

FIRMS_BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
}

# Satellite sources in priority order (VIIRS = higher resolution NRT)
SOURCES = ["VIIRS_NOAA20_NRT", "VIIRS_SNPP_NRT", "MODIS_NRT"]

# Bounding boxes linked to geopolitical / economic regions of interest
# Format: (label, lon_min, lat_min, lon_max, lat_max, country_iso2)
REGIONS: list[tuple[str, float, float, float, float, str]] = [
    ("Ukraine/Russia",    22.0,  44.0,  40.5,  52.5, "UA"),
    ("Gaza/Israel",       34.0,  29.5,  35.8,  33.5, "IL"),
    ("Sudan",             22.0,   8.0,  39.0,  23.0, "SD"),
    ("DR Congo",          17.0, -11.5,  31.5,   5.0, "CD"),
    ("Myanmar",           92.0,  10.0, 101.5,  28.5, "MM"),
    ("Amazon Basin",     -74.0, -15.0, -46.0,   5.0, "BR"),
    ("California/US West", -124.0, 32.0, -114.0, 42.0, "US"),
    ("Australia",         113.0, -44.0, 154.0, -10.0, "AU"),
    ("Siberia/Russia",     60.0,  50.0, 140.0,  75.0, "RU"),
    ("Indonesia",         95.0, -10.0, 141.0,   6.0, "ID"),
    ("Canada Boreal",    -140.0,  48.0, -52.0,  70.0, "CA"),
    ("Central Africa",     9.0,  -5.0,  25.0,  10.0, "CF"),
]

DAY_RANGE = 1   # look back 1 day — run every 3 hours for fresh data


def _fetch_region(
    client: httpx.Client,
    source: str,
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
) -> list[dict]:
    """Fetch FIRMS CSV for a bounding box and parse into list of dicts."""
    area = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    url = f"{FIRMS_BASE}/{NASA_FIRMS_MAP_KEY}/{source}/{area}/{DAY_RANGE}"
    try:
        resp = client.get(url, timeout=30)
        if resp.status_code == 401:
            print(f"[FIRMS] Invalid MAP_KEY — check NASA_FIRMS_MAP_KEY in .env")
            return []
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        return list(reader)
    except Exception as exc:
        print(f"[FIRMS] {source} {area}: {exc}")
        return []


def _confidence_label(raw: str) -> str:
    """Normalise VIIRS/MODIS confidence to low/nominal/high."""
    if not raw:
        return "nominal"
    r = raw.strip().lower()
    if r in ("l", "low", "0", "1", "2"):
        return "low"
    if r in ("h", "high", "100", "99", "98", "97", "96", "95"):
        return "high"
    return "nominal"


def fetch_satellite_fires(db_conn: Any) -> int:
    """
    Pull VIIRS/MODIS fire detections for all regions of interest.
    Stores new detections in satellite_events table.
    Returns count of new rows inserted.
    """
    if not NASA_FIRMS_MAP_KEY:
        print("[FIRMS] NASA_FIRMS_MAP_KEY not set — skipping.")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    with httpx.Client(headers=HEADERS) as client:
        for label, lon_min, lat_min, lon_max, lat_max, iso2 in REGIONS:
            for source in SOURCES:
                rows = _fetch_region(client, source, lon_min, lat_min, lon_max, lat_max)
                if not rows:
                    continue  # try next source for this region

                new_in_region = 0
                for row in rows:
                    lat_str  = row.get("latitude", "")
                    lon_str  = row.get("longitude", "")
                    date_str = row.get("acq_date", "")
                    time_str = row.get("acq_time", "")
                    bright   = row.get("bright_ti4") or row.get("brightness", "")
                    conf     = row.get("confidence", "nominal")
                    frp      = row.get("frp", "")  # fire radiative power (MW)

                    if not lat_str or not lon_str:
                        continue

                    try:
                        lat = float(lat_str)
                        lon = float(lon_str)
                        brightness_val = float(frp or bright or 0) if (frp or bright) else None
                    except ValueError:
                        continue

                    # Dedup: same lat/lon/date (rounded to 0.01°)
                    lat_r = round(lat, 2)
                    lon_r = round(lon, 2)
                    exists = db_conn.execute(
                        """SELECT 1 FROM satellite_events
                           WHERE round(latitude,2)=? AND round(longitude,2)=? AND acq_date=?""",
                        (lat_r, lon_r, date_str),
                    ).fetchone()
                    if exists:
                        continue

                    db_conn.execute(
                        """INSERT INTO satellite_events
                           (id, source, latitude, longitude, brightness,
                            confidence, acq_date, acq_time, country_iso2, ingested_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (
                            str(uuid.uuid4()),
                            source,
                            lat,
                            lon,
                            brightness_val,
                            _confidence_label(conf),
                            date_str,
                            time_str,
                            iso2,
                            now,
                        ),
                    )
                    new_in_region += 1
                    inserted += 1

                if new_in_region:
                    print(f"[FIRMS] {label} ({source}): {new_in_region} new fire detections")
                break  # got data from this source; don't try fallback sources

    if inserted:
        db_conn.commit()
        print(f"[FIRMS] ✓ Total {inserted} new fire detections stored")
    else:
        print("[FIRMS] No new fire detections")

    return inserted
