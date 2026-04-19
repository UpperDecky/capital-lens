"""
FRED (Federal Reserve Economic Data) ingestor.

Pulls key macroeconomic indicators and maps them to the Federal Reserve entity.
These indicators are the signals that move every market — interest rates, inflation,
unemployment, and yield curve shape.

Free API key: https://fred.stlouisfed.org/docs/api/api_key.html
Key in .env: FRED_API_KEY
"""
import uuid
from datetime import datetime, timezone
from typing import Any
import httpx

from backend.config import FRED_API_KEY

BASE_URL = "https://api.stlouisfed.org/fred"

HEADERS = {
    "User-Agent": "CapitalLens research@capitallens.dev",
    "Accept": "application/json",
}

# Series to track → (series_id, display_name, unit, what it means)
SERIES: list[tuple[str, str, str, str]] = [
    ("FEDFUNDS",   "Federal Funds Rate",          "%",   "The benchmark interest rate banks charge each other overnight"),
    ("CPIAUCSL",   "Consumer Price Index (CPI)",   "index","Inflation benchmark — tracks the cost of a basket of goods"),
    ("UNRATE",     "Unemployment Rate",            "%",   "% of labor force actively seeking work but unemployed"),
    ("DGS10",      "10-Year Treasury Yield",       "%",   "Return on 10-year US government bonds — the global risk-free rate"),
    ("T10Y2Y",     "Yield Curve Spread (10Y-2Y)",  "%",   "Difference between 10-year and 2-year yields — negative = recession warning"),
    ("MORTGAGE30US","30-Year Mortgage Rate",       "%",   "Average rate on a 30-year fixed mortgage — tracks housing affordability"),
    ("DEXUSEU",    "USD/EUR Exchange Rate",        "$/€", "How many dollars buy one Euro — tracks dollar strength"),
    ("VIXCLS",     "VIX Volatility Index",         "pts", "Stock market fear gauge — high = uncertainty, low = calm"),
]


def _fetch_latest_observation(series_id: str) -> dict | None:
    """Fetch the most recent observation for a FRED series."""
    if not FRED_API_KEY:
        return None

    try:
        with httpx.Client(headers=HEADERS, timeout=20) as client:
            resp = client.get(
                f"{BASE_URL}/series/observations",
                params={
                    "series_id":   series_id,
                    "api_key":     FRED_API_KEY,
                    "file_type":   "json",
                    "sort_order":  "desc",
                    "limit":       "2",         # Get 2 so we can compute change
                    "observation_end": "9999-12-31",
                },
            )
            resp.raise_for_status()
            observations = resp.json().get("observations", [])
            if len(observations) >= 1:
                return {
                    "latest": observations[0],
                    "previous": observations[1] if len(observations) >= 2 else None,
                }
    except Exception as exc:
        print(f"[FRED] Error fetching {series_id}: {exc}")
    return None


def _build_headline(name: str, value: str, unit: str, prev_value: str | None) -> str:
    """Build a descriptive headline from a FRED observation."""
    try:
        val_f = float(value)
    except (ValueError, TypeError):
        return f"FRED: {name} = {value}{unit}"

    val_str = f"{val_f:.2f}{unit}"

    if prev_value:
        try:
            prev_f = float(prev_value)
            delta  = val_f - prev_f
            direction = "rose" if delta > 0 else "fell"
            delta_str = f"{abs(delta):.2f}{unit}"
            return f"{name} {direction} to {val_str} (Δ{delta_str}) — Federal Reserve data"
        except (ValueError, TypeError):
            pass

    return f"{name} at {val_str} — Federal Reserve economic indicator"


def fetch_fred_indicators(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch latest FRED macroeconomic indicators and store as events for
    the Federal Reserve entity. Skips if FRED_API_KEY is not set.

    Returns count of new events inserted.
    """
    if not FRED_API_KEY:
        print("[FRED] No API key set — skipping (set FRED_API_KEY in .env)")
        return 0

    fed_id = entity_map.get("Federal Reserve")
    if not fed_id:
        print("[FRED] 'Federal Reserve' entity not found in DB — skipping")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for series_id, display_name, unit, _ in SERIES:
        result = _fetch_latest_observation(series_id)
        if not result:
            continue

        latest   = result["latest"]
        previous = result.get("previous")

        obs_date  = latest.get("date", "")
        obs_value = latest.get("value", ".")
        prev_value = previous.get("value") if previous else None

        # FRED uses "." for missing values
        if obs_value == ".":
            continue

        headline = _build_headline(display_name, obs_value, unit, prev_value)

        # Skip if we already have this exact observation
        exists = db_conn.execute(
            "SELECT 1 FROM events WHERE entity_id=? AND source_url=? AND occurred_at=?",
            (fed_id, f"FRED:{series_id}", obs_date),
        ).fetchone()
        if exists:
            continue

        # Also skip if we have the same headline (same value, different route)
        exists_hl = db_conn.execute(
            "SELECT 1 FROM events WHERE entity_id=? AND headline=?",
            (fed_id, headline),
        ).fetchone()
        if exists_hl:
            continue

        # Compute amount: raw numeric value (useful for sorting/filtering)
        try:
            amount = float(obs_value)
        except (ValueError, TypeError):
            amount = None

        # Score: macro indicators are always notable (level 3 minimum)
        from backend.scoring import score_event
        event_draft = {
            "headline":   headline,
            "amount":     amount,
            "event_type": "filing",       # treat as official data release (filing type)
            "source_name": "FRED / Federal Reserve",
        }
        importance = max(3, score_event(event_draft))  # floor at 3 — macro data always notable

        db_conn.execute(
            """INSERT INTO events
               (id, entity_id, event_type, headline, amount, currency,
                source_url, source_name, occurred_at, ingested_at, importance)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                fed_id,
                "filing",
                headline,
                amount,
                unit,
                f"FRED:{series_id}",
                "Federal Reserve (FRED)",
                obs_date,
                now,
                importance,
            ),
        )
        inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[FRED] ✓ Inserted {inserted} new macro indicator events")
    return inserted
