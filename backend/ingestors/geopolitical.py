"""
Geopolitical conflict event ingestor — ACLED + UCDP.
Both APIs are free:
  ACLED:  register at acleddata.com/register → set ACLED_EMAIL + ACLED_KEY
  UCDP:   email ucdp@pcr.uu.se for token → set UCDP_TOKEN
Events are stored in the geo_events table (same as GDELT, source discriminates).
API docs:
  ACLED: https://acleddata.com/acled-api-documentation
  UCDP:  https://ucdp.uu.se/apidocs/
"""
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.config import ACLED_EMAIL, ACLED_KEY, UCDP_TOKEN

ACLED_BASE = "https://api.acleddata.com/acled/read.php"
UCDP_BASE  = "https://ucdpapi.pcr.uu.se/api/gedevents/23.1"

HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept": "application/json",
}

# ACLED event types to ingest — skip 'Strategic developments' (low signal)
ACLED_EVENT_TYPES = [
    "Battles",
    "Explosions/Remote violence",
    "Protests",
    "Riots",
    "Violence against civilians",
]

# ISO2 codes to prioritise — mirrors the GDELT country list plus extras
HIGH_INTEREST_COUNTRIES = [
    "UA", "RU", "IL", "PS", "SD", "MM", "YE", "ET", "CD", "LY",
    "ML", "HT", "IR", "KP", "CN", "TW", "VE", "SY", "AF", "PK",
    "IN", "KR", "NG", "MX", "SA", "TR",
]


# ──────────────────────────────────────────────────────────────────────────────
# ACLED
# ──────────────────────────────────────────────────────────────────────────────

def _acled_fetch(days_back: int = 3) -> list[dict]:
    """Fetch ACLED events from the last N days for high-interest countries."""
    if not ACLED_EMAIL or not ACLED_KEY:
        print("[ACLED] ACLED_EMAIL / ACLED_KEY not set — skipping.")
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    results: list[dict] = []

    params = {
        "email":             ACLED_EMAIL,
        "key":               ACLED_KEY,
        "event_date":        since,
        "event_date_where":  ">=",
        "iso":               "|".join(str(_iso3_num(c)) for c in HIGH_INTEREST_COUNTRIES if _iso3_num(c)),
        "event_type":        "|".join(ACLED_EVENT_TYPES),
        "limit":             500,
        "page":              1,
        "fields":            "event_id_cnty|event_date|event_type|sub_event_type|"
                             "country|iso|region|latitude|longitude|"
                             "actor1|actor2|fatalities|notes|source|source_scale",
        "format":            "json",
    }

    try:
        with httpx.Client(headers=HEADERS, timeout=30) as client:
            resp = client.get(ACLED_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("data", [])
    except Exception as exc:
        print(f"[ACLED] Fetch error: {exc}")

    return results


def _iso3_num(iso2: str) -> int | None:
    """Map ISO2 → ACLED numeric ISO (ISO 3166-1 numeric)."""
    # ACLED uses numeric ISO codes in its API filter
    MAP: dict[str, int] = {
        "UA": 804, "RU": 643, "IL": 376, "PS": 275, "SD": 729,
        "MM": 104, "YE": 887, "ET": 231, "CD": 180, "LY": 434,
        "ML": 466, "HT": 332, "IR": 364, "KP": 408, "CN": 156,
        "TW": 158, "VE": 862, "SY": 760, "AF":   4, "PK": 586,
        "IN": 356, "KR": 410, "NG": 566, "MX": 484, "SA": 682,
        "TR": 792,
    }
    return MAP.get(iso2)


def _store_acled(db_conn: Any, events: list[dict]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for ev in events:
        event_id = ev.get("event_id_cnty", "")
        url = f"https://acleddata.com/data-export-tool/?event_id={event_id}"

        # Deduplicate by URL (which embeds the ACLED event ID)
        exists = db_conn.execute(
            "SELECT 1 FROM geo_events WHERE url=?", (url,)
        ).fetchone()
        if exists:
            continue

        # Compose headline from ACLED fields
        actor1    = ev.get("actor1", "Unknown")
        actor2    = ev.get("actor2", "")
        etype     = ev.get("event_type", "")
        sub_etype = ev.get("sub_event_type", "")
        country   = ev.get("country", "")
        fatalities = ev.get("fatalities", 0)
        notes     = (ev.get("notes") or "")[:300]

        headline = f"[ACLED] {etype} — {actor1}"
        if actor2:
            headline += f" vs {actor2}"
        headline += f" in {country}"
        if fatalities:
            headline += f" ({fatalities} fatalities)"
        if sub_etype and sub_etype != etype:
            headline += f" [{sub_etype}]"

        # Extract ISO2 from numeric code
        iso2 = _num_to_iso2(int(ev.get("iso", 0) or 0))

        occurred_at = (ev.get("event_date") or now[:10]) + "T00:00:00Z"

        # Tone: rough mapping -- fatalities = negative tone
        fatalities_int = int(fatalities or 0)
        tone = -min(fatalities_int * 2.0, 100.0)

        lat = ev.get("latitude")
        lon = ev.get("longitude")
        try:
            lat = float(lat) if lat not in (None, "", "0", 0) else None
            lon = float(lon) if lon not in (None, "", "0", 0) else None
        except (TypeError, ValueError):
            lat = lon = None

        db_conn.execute(
            """INSERT INTO geo_events
               (id, iso2, headline, url, source, occurred_at, tone, themes, ingested_at, latitude, longitude)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                iso2,
                headline[:500],
                url,
                "ACLED",
                occurred_at,
                tone,
                f'["{etype}","{sub_etype}","conflict","fatalities:{fatalities_int}"]',
                now,
                lat,
                lon,
            ),
        )
        inserted += 1

    if inserted:
        db_conn.commit()
    return inserted


def _num_to_iso2(num: int) -> str | None:
    MAP: dict[int, str] = {v: k for k, v in {
        "UA": 804, "RU": 643, "IL": 376, "PS": 275, "SD": 729,
        "MM": 104, "YE": 887, "ET": 231, "CD": 180, "LY": 434,
        "ML": 466, "HT": 332, "IR": 364, "KP": 408, "CN": 156,
        "TW": 158, "VE": 862, "SY": 760, "AF":   4, "PK": 586,
        "IN": 356, "KR": 410, "NG": 566, "MX": 484, "SA": 682,
        "TR": 792,
    }.items()}
    return MAP.get(num)


# ──────────────────────────────────────────────────────────────────────────────
# UCDP
# ──────────────────────────────────────────────────────────────────────────────

def _ucdp_fetch(page: int = 0, pagesize: int = 100) -> list[dict]:
    """
    Fetch latest UCDP georeferenced conflict events.
    Public API -- no token required. Token header added only if UCDP_TOKEN is set.
    """
    results: list[dict] = []
    try:
        req_headers = {**HEADERS}
        if UCDP_TOKEN:
            req_headers["x-ucdp-access-token"] = UCDP_TOKEN
        with httpx.Client(headers=req_headers, timeout=30) as client:
            resp = client.get(
                UCDP_BASE,
                params={"pagesize": pagesize, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("Result", [])
    except Exception as exc:
        print(f"[UCDP] Fetch error: {exc}")

    return results


def _store_ucdp(db_conn: Any, events: list[dict]) -> int:
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for ev in events:
        uid      = ev.get("id", "")
        url      = f"https://ucdp.uu.se/event/{uid}"
        headline = (ev.get("source_headline") or ev.get("conflict_name") or "UCDP conflict event")[:500]
        country  = ev.get("country", "")
        deaths   = ev.get("deaths_a", 0) or 0
        iso2     = (ev.get("country_id") or "")[:2].upper() or None
        date_str = ev.get("date_start") or now[:10]
        try:
            occurred_at = datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
        except Exception:
            occurred_at = now

        exists = db_conn.execute(
            "SELECT 1 FROM geo_events WHERE url=?", (url,)
        ).fetchone()
        if exists:
            continue

        tone = -min(int(deaths) * 2.0, 100.0)
        db_conn.execute(
            """INSERT INTO geo_events
               (id, iso2, headline, url, source, occurred_at, tone, themes, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                iso2,
                f"[UCDP] {headline} in {country} ({deaths} deaths)",
                url,
                "UCDP",
                occurred_at,
                tone,
                '["conflict","armed-violence","ucdp"]',
                now,
            ),
        )
        inserted += 1

    if inserted:
        db_conn.commit()
    return inserted


# ──────────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────────

def fetch_geopolitical_events(db_conn: Any) -> int:
    """Run ACLED + UCDP ingestors. Returns total new geo_events rows."""
    total = 0

    acled_raw = _acled_fetch(days_back=3)
    if acled_raw:
        n = _store_acled(db_conn, acled_raw)
        print(f"[ACLED] Inserted {n} new events (of {len(acled_raw)} fetched)")
        total += n
    else:
        print("[ACLED] No events returned (key missing or API error)")

    ucdp_raw = _ucdp_fetch()
    if ucdp_raw:
        n = _store_ucdp(db_conn, ucdp_raw)
        print(f"[UCDP] Inserted {n} new events (of {len(ucdp_raw)} fetched)")
        total += n

    return total
