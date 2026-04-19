"""
USA Spending ingestor — federal contract tracking.

No API key required. Uses the public USASpending.gov API (POST requests).
Tracks defense and tech companies that receive significant federal contracts.

API docs: https://api.usaspending.gov/docs/endpoint-reference.html
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
import httpx

BASE_URL = "https://api.usaspending.gov/api/v2"

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "CapitalLens research@capitallens.dev",
}

# Entities to track — match exactly to seeded entity names
CONTRACT_TARGETS: list[str] = [
    "Palantir",
    "Lockheed Martin",
    "SpaceX",
    "Boeing",
    "Raytheon",
    "General Dynamics",
    "Amazon",
    "Microsoft",
    "Nvidia",
    "Google",          # Alphabet subsidiary
    "Pfizer",
    "Walmart",
]

# Map keywords to canonical entity names (for search matching)
ENTITY_ALIASES: dict[str, str] = {
    "palantir":          "Palantir",
    "lockheed martin":   "Lockheed Martin",
    "lockheed":          "Lockheed Martin",
    "spacex":            "SpaceX",
    "boeing":            "Boeing",
    "raytheon":          "Raytheon",
    "general dynamics":  "General Dynamics",
    "amazon":            "Amazon",
    "amazon web services": "Amazon",
    "aws":               "Amazon",
    "microsoft":         "Microsoft",
    "nvidia":            "Nvidia",
    "google":            "Alphabet",
    "alphabet":          "Alphabet",
    "pfizer":            "Pfizer",
    "walmart":           "Walmart",
}


def _resolve_recipient(name: str) -> str | None:
    """Map a USA Spending recipient name to our canonical entity name."""
    lower = name.lower()
    for alias, canonical in ENTITY_ALIASES.items():
        if alias in lower:
            return canonical
    return None


def _fetch_contracts_for_recipient(recipient_name: str, days_back: int = 90) -> list[dict]:
    """
    Query USA Spending for recent contracts awarded to a recipient.
    Uses the spending_by_award search endpoint with a keyword filter.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    payload = {
        "filters": {
            "time_period": [{"start_date": cutoff, "end_date": today}],
            "award_type_codes": ["A", "B", "C", "D"],  # contracts (not grants)
            "recipient_search_text": [recipient_name],
        },
        "fields": [
            "Award ID", "Recipient Name", "Award Amount",
            "Description", "Awarding Agency", "Period of Performance Start Date",
            "Place of Performance State Code",
        ],
        "page": 1,
        "limit": 10,
        "sort": "Award Amount",
        "order": "desc",
    }

    try:
        with httpx.Client(headers=HEADERS, timeout=30) as client:
            resp = client.post(f"{BASE_URL}/search/spending_by_award/", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
    except Exception as exc:
        print(f"[USASpending] Error fetching '{recipient_name}': {exc}")
        return []


def fetch_federal_contracts(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch recent federal contracts for tracked entities from USA Spending.
    Inserts new contract events into the events table.
    Returns count of new events inserted.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for target in CONTRACT_TARGETS:
        if target not in entity_map:
            continue  # entity not seeded — skip

        entity_id = entity_map[target]
        contracts = _fetch_contracts_for_recipient(target)

        for contract in contracts:
            recipient_raw = (contract.get("Recipient Name") or "").strip()
            canonical = _resolve_recipient(recipient_raw)
            if not canonical or canonical not in entity_map:
                continue

            # Some contracts match a different entity than target — use the matched one
            cid = entity_map[canonical]

            amount_raw = contract.get("Award Amount")
            try:
                amount = float(amount_raw) if amount_raw else None
            except (ValueError, TypeError):
                amount = None

            # Skip tiny contracts (< $100K) to reduce noise
            if amount and amount < 100_000:
                continue

            description = (contract.get("Description") or "").strip().title()
            agency      = (contract.get("Awarding Agency") or "Federal Government").strip()
            award_id    = (contract.get("Award ID") or "").strip()
            date_str    = contract.get("Period of Performance Start Date") or ""

            # Build a descriptive headline
            amount_str = f"${amount:,.0f}" if amount else "undisclosed amount"
            headline = (
                f"{canonical} awarded {amount_str} federal contract"
                + (f": {description[:60]}" if description else "")
                + f" — {agency}"
            )

            # Deduplicate: same entity + award_id OR same headline
            exists = db_conn.execute(
                "SELECT 1 FROM events WHERE entity_id=? AND (headline=? OR source_url=?)",
                (cid, headline, award_id),
            ).fetchone()
            if exists:
                continue

            # Score using deterministic algorithm
            from backend.scoring import score_event
            event_draft = {
                "headline":   headline,
                "amount":     amount,
                "event_type": "news",   # classified as news (contract award)
                "source_name": agency,
            }
            importance = score_event(event_draft)

            db_conn.execute(
                """INSERT INTO events
                   (id, entity_id, event_type, headline, amount, currency,
                    source_url, source_name, occurred_at, ingested_at, importance)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    cid,
                    "news",           # contract awards treated as news events
                    headline,
                    amount,
                    "USD",
                    award_id,
                    agency,
                    date_str,
                    now,
                    importance,
                ),
            )
            inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[USASpending] ✓ Inserted {inserted} new federal contract events")
    return inserted
