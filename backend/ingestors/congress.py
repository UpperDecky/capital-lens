"""
Congressional stock trade ingestor — House Stock Watcher API.

Pulls recent House member stock disclosures and matches them to seeded
politician entities. Trade amounts are reported as ranges in filings;
we take the midpoint of each range.

API: https://housestockwatcher.com/api (no auth required)
Senate data: https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json
"""
import re
import uuid
import time
from datetime import datetime, timezone
from typing import Any, Optional
import httpx

HOUSE_API_URL   = "https://housestockwatcher.com/api/transactions"
SENATE_DATA_URL = (
    "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com"
    "/aggregate/all_transactions.json"
)

HEADERS = {
    "User-Agent": "CapitalLens research@capitallens.dev",
    "Accept": "application/json",
}

# Politician name aliases — congressional disclosures may use full legal names
NAME_ALIASES: dict[str, str] = {
    "Pelosi, Nancy": "Nancy Pelosi",
    "Nancy Pelosi": "Nancy Pelosi",
    "Romney, Mitt": "Mitt Romney",
    "Mitt Romney": "Mitt Romney",
    "Tuberville, Tommy": "Tommy Tuberville",
    "Tommy Tuberville": "Tommy Tuberville",
    "Khanna, Ro": "Ro Khanna",
    "Ro Khanna": "Ro Khanna",
    "Crenshaw, Dan": "Dan Crenshaw",
    "Dan Crenshaw": "Dan Crenshaw",
    "Ocasio-Cortez, Alexandria": "Alexandria Ocasio-Cortez",
    "Alexandria Ocasio-Cortez": "Alexandria Ocasio-Cortez",
    "Newsom, Gavin": "Gavin Newsom",
    "Gavin Newsom": "Gavin Newsom",
    "McConnell, Mitch": "Mitch McConnell",
    "Mitch McConnell": "Mitch McConnell",
    "Trump, Donald": "Donald Trump",
    "Donald Trump": "Donald Trump",
}


def _parse_amount(amount_str: str) -> Optional[float]:
    """
    Parse congressional disclosure range strings into a dollar midpoint.
    Examples: "$15,001 - $50,000" → 32500.5
              "$1,000,001 - $5,000,000" → 3000000.5
              "Over $50,000,000" → 50000000
    """
    if not amount_str:
        return None
    # Remove dollar signs, commas, spaces
    clean = re.sub(r"[$,\s]", "", amount_str)
    # Find all numbers in the string
    nums = [int(n) for n in re.findall(r"\d+", clean) if len(n) <= 12]
    if not nums:
        return None
    if len(nums) == 1:
        return float(nums[0])
    return float(sum(nums) / len(nums))  # midpoint of range


def _resolve_name(raw_name: str) -> Optional[str]:
    """Resolve a congressman name from disclosure format to our seeded name."""
    if not raw_name:
        return None
    # Direct match
    if raw_name in NAME_ALIASES:
        return NAME_ALIASES[raw_name]
    # Try reversed "Last, First" → "First Last"
    if "," in raw_name:
        parts = [p.strip() for p in raw_name.split(",", 1)]
        if len(parts) == 2:
            normalized = f"{parts[1]} {parts[0]}"
            if normalized in NAME_ALIASES:
                return NAME_ALIASES[normalized]
    return None


def _build_headline(rep: str, ticker: str, asset: str, trade_type: str) -> str:
    action = "purchased" if trade_type.lower() in ("purchase", "buy") else "sold"
    symbol = ticker.strip() if ticker and ticker.strip() not in ("--", "N/A", "") else None
    if symbol:
        return f"{rep} {action} ${symbol} ({asset}) — congressional stock disclosure"
    return f"{rep} {action} {asset} — congressional stock disclosure"


def _fetch_house_trades() -> list[dict]:
    """Fetch House member trades from House Stock Watcher API."""
    try:
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            resp = client.get(HOUSE_API_URL)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data
            # Some API versions wrap in {"data": [...]}
            if isinstance(data, dict):
                return data.get("data", [])
    except Exception as exc:
        print(f"[Congress/House] Fetch error: {exc}")
    return []


def _fetch_senate_trades() -> list[dict]:
    """Fetch Senate member trades from Senate Stock Watcher data."""
    try:
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            resp = client.get(SENATE_DATA_URL)
            resp.raise_for_status()
            data = resp.json()
            # Senate data format may be a list of transactions
            if isinstance(data, list):
                return data[:200]  # cap — Senate file can be large
            if isinstance(data, dict):
                return data.get("data", [])[:200]
    except Exception as exc:
        print(f"[Congress/Senate] Fetch error: {exc}")
    return []


def fetch_congressional_trades(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch recent congressional stock trades from both House and Senate APIs.
    Matches trades to seeded politician entities. Inserts new events.
    Returns count of new events inserted.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    # Combine House + Senate trades; process most recent first
    all_trades = _fetch_house_trades() + _fetch_senate_trades()
    print(f"[Congress] Fetched {len(all_trades)} raw trade records")

    seen: set[str] = set()  # deduplicate within this batch

    for trade in all_trades:
        # Representative/Senator name
        raw_name = (
            trade.get("representative")
            or trade.get("Senator")
            or trade.get("senator")
            or trade.get("owner")
            or ""
        )
        canonical = _resolve_name(raw_name.strip())
        if not canonical:
            continue  # Not one of our seeded politicians

        entity_id = entity_map.get(canonical)
        if not entity_id:
            continue

        ticker     = (trade.get("ticker") or "").strip()
        asset      = (trade.get("asset_description") or trade.get("asset_name") or ticker or "Unknown").strip()
        trade_type = (trade.get("type") or trade.get("transaction_type") or "purchase").strip()
        amount_str = trade.get("amount") or ""
        amount     = _parse_amount(amount_str)
        tx_date    = (
            trade.get("transaction_date")
            or trade.get("date_received")
            or trade.get("filed_at_date")
            or ""
        )

        headline = _build_headline(canonical, ticker, asset, trade_type)

        # Skip duplicates within this batch
        dedup_key = f"{entity_id}|{headline}|{tx_date}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Skip if already in DB
        exists = db_conn.execute(
            "SELECT 1 FROM events WHERE entity_id=? AND headline=? AND occurred_at=?",
            (entity_id, headline, tx_date),
        ).fetchone()
        if exists:
            continue

        # Compute algorithmic importance score
        from backend.scoring import score_event
        event_draft = {
            "headline": headline,
            "amount": amount,
            "event_type": "congressional_trade",
            "source_name": "House Stock Watcher",
        }
        importance = score_event(event_draft)

        db_conn.execute(
            """INSERT INTO events
               (id, entity_id, event_type, headline, amount, currency,
                source_url, source_name, occurred_at, ingested_at, importance)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                entity_id,
                "congressional_trade",   # proper standalone type (migration enables this)
                headline,
                amount,
                "USD",
                trade.get("ptr_link") or trade.get("link") or "",
                "House Stock Watcher",
                tx_date,
                now,
                importance,
            ),
        )
        inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[Congress] ✓ Inserted {inserted} new congressional trades")
    return inserted
