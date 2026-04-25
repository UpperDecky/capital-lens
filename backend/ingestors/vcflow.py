"""
VC / M&A deal flow ingestor.

Scans the existing events table for high-value funding rounds and
acquisitions already ingested from EDGAR + RSS, then promotes them
to cash_flow records so they appear on the Cash Flow map and ticker.

No external API calls -- operates purely on data already in the DB.
Runs every 6 hours via scheduler.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Any

# ---- Sector-to-country heuristic --------------------------------------------
# Used to assign source_country (the investor / acquirer country) when we
# can't determine it precisely. Tech/Finance dominated by US/UK.

SECTOR_INVESTOR_COUNTRY: dict[str, str] = {
    "Technology":  "US",
    "E-Commerce":  "US",
    "Finance":     "US",
    "Aerospace":   "US",
    "Defense":     "US",
    "Healthcare":  "US",
    "Automotive":  "US",
    "Retail":      "US",
    "Energy":      "US",
    "Government":  "US",
}

COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "US": (37.09,  -95.71),
    "GB": (55.38,   -3.44),
    "CN": (35.86,  104.20),
    "JP": (36.20,  138.25),
    "DE": (51.17,   10.45),
    "SA": (23.89,   45.08),
    "AE": (23.42,   53.85),
    "SG": ( 1.35,  103.82),
    "XX": ( 0.00,    0.00),
}

# Keywords that indicate a funding / deal event
FUNDING_KEYWORDS = (
    "raises", "raised", "raise", "funding", "funds",
    "series a", "series b", "series c", "series d", "series e",
    "seed round", "pre-seed", "round", "valuation",
    "ipo", "spac", "go public", "public offering",
)

ACQUISITION_KEYWORDS = (
    "acquires", "acquired", "acquisition", "buys", "purchases",
    "takeover", "merger", "merges",
)


def _coords(iso2: str) -> tuple[float, float]:
    return COUNTRY_COORDS.get(iso2, COUNTRY_COORDS["XX"])


def _is_funding_event(headline: str) -> bool:
    lower = headline.lower()
    return any(kw in lower for kw in FUNDING_KEYWORDS)


def _is_acquisition_event(headline: str, event_type: str) -> bool:
    if event_type == "acquisition":
        return True
    lower = headline.lower()
    return any(kw in lower for kw in ACQUISITION_KEYWORDS)


def _extract_amount(amount_field: float | None, headline: str) -> float | None:
    """Use DB amount field if present, else try to extract from headline text."""
    if amount_field and amount_field > 0:
        return float(amount_field)
    match = re.search(
        r"\$([0-9,.]+)\s*(trillion|billion|million|T|B|M)\b",
        headline,
        re.IGNORECASE,
    )
    if match:
        num  = float(match.group(1).replace(",", ""))
        unit = match.group(2).lower()
        if unit in ("trillion", "t"):
            return num * 1e12
        if unit in ("billion", "b"):
            return num * 1e9
        return num * 1e6
    return None


def promote_events_to_flows(db_conn: Any) -> int:
    """
    Scan events table for high-value funding/M&A events and create
    corresponding cash_flow records. Returns count of new records.
    """
    now     = datetime.now(timezone.utc).isoformat()
    inserted = 0

    # Pull events that look like funding/acquisition and have a source_url
    # (source_url used as dedup key in cash_flows)
    rows = db_conn.execute(
        """SELECT e.id, e.entity_id, e.event_type, e.headline,
                  e.amount, e.source_url, e.occurred_at, e.ingested_at,
                  en.name AS entity_name, en.sector
           FROM events e
           JOIN entities en ON e.entity_id = en.id
           WHERE e.source_url IS NOT NULL
             AND (
                   e.event_type IN ('acquisition', 'filing', 'news')
               )
           ORDER BY e.ingested_at DESC
           LIMIT 500"""
    ).fetchall()

    for row in rows:
        headline   = row["headline"] or ""
        event_type = row["event_type"] or ""
        amount_db  = row["amount"]

        is_funding  = _is_funding_event(headline)
        is_acq      = _is_acquisition_event(headline, event_type)

        if not (is_funding or is_acq):
            continue

        amount_usd = _extract_amount(amount_db, headline)
        if not amount_usd or amount_usd < 1_000_000:
            continue

        source_url  = row["source_url"]
        sector      = row["sector"] or "Technology"
        entity_name = row["entity_name"] or "Unknown"

        # Investor country heuristic -- most tracked entities are US-based
        inv_iso   = SECTOR_INVESTOR_COUNTRY.get(sector, "US")
        rec_iso   = "US"  # recipient (the company) assumed US for seed entities

        flow_type = "vc_deal" if is_funding else "vc_deal"
        if is_acq:
            flow_type = "vc_deal"

        src_lat, src_lon = _coords(inv_iso)
        dst_lat, dst_lon = _coords(rec_iso)

        occurred_at = row["occurred_at"] or row["ingested_at"] or now

        flow_id = str(uuid.uuid4())
        try:
            db_conn.execute(
                """INSERT OR IGNORE INTO cash_flows
                   (id, flow_type, asset, amount_usd,
                    source_label, dest_label,
                    source_country, dest_country,
                    source_lat, source_lon, dest_lat, dest_lon,
                    headline, source_name, source_url,
                    entity_id, occurred_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (flow_id, flow_type, "USD", amount_usd,
                 "Investor", entity_name,
                 inv_iso, rec_iso,
                 src_lat, src_lon, dst_lat, dst_lon,
                 headline[:300], "Capital Lens Events",
                 source_url,
                 row["entity_id"],
                 occurred_at, now),
            )
            inserted += db_conn.execute("SELECT changes()").fetchone()[0]
        except Exception as exc:
            print(f"[CashFlow/VC] DB error: {exc}")

    if inserted:
        db_conn.commit()
        print(f"[CashFlow/VC] Promoted {inserted} events to cash flows")
    return inserted
