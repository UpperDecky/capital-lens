"""
Prediction market ingestor — Polymarket.
No API key required for read access. Free.
Uses the Gamma API (market metadata) and CLOB API (prices).
API docs: https://docs.polymarket.com
Gamma API: https://gamma-api.polymarket.com/
CLOB API:  https://clob.polymarket.com/
"""
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE  = "https://clob.polymarket.com"

HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept": "application/json",
}

# Keywords that link a prediction market question to a seed entity
ENTITY_KEYWORDS: dict[str, str] = {
    "apple":          "Apple",
    "nvidia":         "Nvidia",
    "microsoft":      "Microsoft",
    "alphabet":       "Alphabet",
    "google":         "Alphabet",
    "meta":           "Meta",
    "facebook":       "Meta",
    "amazon":         "Amazon",
    "tesla":          "Tesla",
    "berkshire":      "Berkshire Hathaway",
    "jpmorgan":       "JPMorgan",
    "goldman":        "Goldman Sachs",
    "blackrock":      "BlackRock",
    "exxon":          "ExxonMobil",
    "lockheed":       "Lockheed Martin",
    "pfizer":         "Pfizer",
    "walmart":        "Walmart",
    "palantir":       "Palantir",
    "spacex":         "SpaceX",
    "openai":         "OpenAI",
    "anthropic":      "Anthropic",
    "elon musk":      "Elon Musk",
    "musk":           "Elon Musk",
    "bezos":          "Jeff Bezos",
    "bill gates":     "Bill Gates",
    "zuckerberg":     "Mark Zuckerberg",
    "warren buffett": "Warren Buffett",
    "buffett":        "Warren Buffett",
    "trump":          "Donald Trump",
    "pelosi":         "Nancy Pelosi",
    "federal reserve":"Federal Reserve",
    "fed rate":       "Federal Reserve",
    "boeing":         "Boeing",
    "raytheon":       "Raytheon",
}

MAX_MARKETS = 200   # max markets to fetch per poll


def _fetch_active_markets() -> list[dict]:
    """Fetch active Polymarket markets via Gamma API."""
    markets: list[dict] = []
    offset = 0
    limit  = 100

    with httpx.Client(headers=HEADERS, timeout=30) as client:
        while len(markets) < MAX_MARKETS:
            try:
                resp = client.get(
                    f"{GAMMA_BASE}/markets",
                    params={
                        "closed":   "false",
                        "active":   "true",
                        "limit":    limit,
                        "offset":   offset,
                        "order":    "volume",
                        "ascending":"false",
                    },
                )
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                markets.extend(batch)
                if len(batch) < limit:
                    break
                offset += limit
            except Exception as exc:
                print(f"[Polymarket] Gamma API error: {exc}")
                break

    return markets


def _match_entity(question: str, entity_map: dict[str, str]) -> tuple[str | None, str | None]:
    """Return (entity_name, entity_id) for first keyword match in question."""
    q_lower = question.lower()
    for keyword, entity_name in ENTITY_KEYWORDS.items():
        if keyword in q_lower:
            entity_id = entity_map.get(entity_name)
            if entity_id:
                return entity_name, entity_id
    return None, None


def _extract_prices(market: dict) -> tuple[float | None, float | None]:
    """
    Extract yes/no prices from the market dict.
    Gamma API returns outcomes as a JSON-like list inside the market object.
    """
    tokens = market.get("tokens", [])
    yes_price: float | None = None
    no_price: float | None = None

    for token in tokens:
        outcome = (token.get("outcome") or "").lower()
        price   = token.get("price")
        if price is None:
            continue
        try:
            p = float(price)
        except (TypeError, ValueError):
            continue
        if outcome == "yes":
            yes_price = p
        elif outcome == "no":
            no_price = p

    # Fall back to outcomePrices string if tokens not present
    if yes_price is None:
        outcome_prices = market.get("outcomePrices", "")
        if outcome_prices:
            try:
                import json
                prices = json.loads(outcome_prices)
                if isinstance(prices, list) and len(prices) >= 2:
                    yes_price = float(prices[0])
                    no_price  = float(prices[1])
            except Exception:
                pass

    return yes_price, no_price


def fetch_prediction_markets(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch active Polymarket markets and store/update them in prediction_markets.
    Markets linked to seed entities get entity_id set.
    Returns count of new rows inserted.
    """
    raw_markets = _fetch_active_markets()
    if not raw_markets:
        print("[Polymarket] No markets returned.")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    updated  = 0

    for mkt in raw_markets:
        cid      = mkt.get("conditionId") or mkt.get("id") or ""
        question = (mkt.get("question") or mkt.get("title") or "").strip()
        category = mkt.get("category") or mkt.get("tags", [{}])[0].get("label", "") if mkt.get("tags") else ""
        end_date = mkt.get("endDate") or mkt.get("endDateIso")
        volume   = mkt.get("volume") or mkt.get("volumeNum")
        liquidity= mkt.get("liquidity") or mkt.get("liquidityNum")

        if not cid or not question:
            continue

        yes_price, no_price = _extract_prices(mkt)
        _, entity_id = _match_entity(question, entity_map)

        try:
            vol  = float(volume)   if volume   else None
            liq  = float(liquidity) if liquidity else None
        except (TypeError, ValueError):
            vol = liq = None

        existing = db_conn.execute(
            "SELECT id FROM prediction_markets WHERE id=?", (cid,)
        ).fetchone()

        if existing:
            # Update prices on existing record
            db_conn.execute(
                """UPDATE prediction_markets
                   SET yes_price=?, no_price=?, volume_usd=?, liquidity_usd=?,
                       entity_id=COALESCE(entity_id,?), fetched_at=?
                   WHERE id=?""",
                (yes_price, no_price, vol, liq, entity_id, now, cid),
            )
            updated += 1
        else:
            db_conn.execute(
                """INSERT INTO prediction_markets
                   (id, question, category, end_date, yes_price, no_price,
                    volume_usd, liquidity_usd, active, entity_id, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    cid,
                    question[:500],
                    str(category)[:100] if category else None,
                    str(end_date)[:30]  if end_date  else None,
                    yes_price,
                    no_price,
                    vol,
                    liq,
                    1,
                    entity_id,
                    now,
                ),
            )
            inserted += 1

    db_conn.commit()
    print(
        f"[Polymarket] ✓ {inserted} new markets | {updated} updated "
        f"(from {len(raw_markets)} active markets)"
    )
    return inserted
