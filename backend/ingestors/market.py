"""
Alpha Vantage market price ingestor.
Free tier: 25 requests/day — we fetch all tickers ONCE per day.
Prices are stored in entities.last_price so entity profiles show live data.
"""
import httpx
import time
from datetime import datetime, timezone
from typing import Any

from backend.config import ALPHA_VANTAGE_API_KEY

AV_BASE = "https://www.alphavantage.co/query"

# Ticker map — 17 companies, fits within 25 req/day limit when run once daily
TICKER_MAP: dict[str, str] = {
    "Apple":              "AAPL",
    "Nvidia":             "NVDA",
    "Microsoft":          "MSFT",
    "Alphabet":           "GOOGL",
    "Meta":               "META",
    "Amazon":             "AMZN",
    "Tesla":              "TSLA",
    "Berkshire Hathaway": "BRK.B",
    "JPMorgan":           "JPM",
    "Goldman Sachs":      "GS",
    "BlackRock":          "BLK",
    "ExxonMobil":         "XOM",
    "Lockheed Martin":    "LMT",
    "Pfizer":             "PFE",
    "Walmart":            "WMT",
    "Visa":               "V",
    "Palantir":           "PLTR",
}


def fetch_market_prices(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch latest closing prices from Alpha Vantage and persist them on
    the entities table (last_price, price_updated_at, ticker).
    Returns number of prices successfully stored.
    Runs once per day — 17 tickers uses 17 of the 25 daily free requests.
    """
    if not ALPHA_VANTAGE_API_KEY:
        print("[Market] ALPHA_VANTAGE_API_KEY not set — skipping.")
        return 0

    cur = db_conn.cursor()
    stored = 0
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=15) as client:
        for entity_name, ticker in TICKER_MAP.items():
            entity_id = entity_map.get(entity_name)
            if not entity_id:
                continue
            try:
                resp = client.get(AV_BASE, params={
                    "function": "GLOBAL_QUOTE",
                    "symbol":   ticker,
                    "apikey":   ALPHA_VANTAGE_API_KEY,
                })
                data = resp.json()

                # Detect rate-limit message from Alpha Vantage
                if "Note" in data or "Information" in data:
                    msg = data.get("Note") or data.get("Information", "")
                    print(f"[Market] Rate limit hit: {msg[:80]}")
                    break  # Stop fetching — quota exhausted for today

                quote = data.get("Global Quote", {})
                price_str = quote.get("05. price", "")
                change_str = quote.get("10. change percent", "").replace("%", "").strip()

                if not price_str:
                    print(f"[Market] No price returned for {ticker}")
                    continue

                price = float(price_str)
                change_pct = float(change_str) if change_str else None

                # Persist to entities table
                cur.execute(
                    """UPDATE entities
                       SET last_price=?, price_updated_at=?, ticker=?
                       WHERE id=?""",
                    (price, now, ticker, entity_id),
                )
                db_conn.commit()
                stored += 1

                change_label = ""
                if change_pct is not None:
                    arrow = "▲" if change_pct >= 0 else "▼"
                    change_label = f" {arrow}{abs(change_pct):.2f}%"

                print(f"[Market] {entity_name} ({ticker}): ${price:,.2f}{change_label}")

                # Respect Alpha Vantage rate limit — 5 req/min on free tier
                time.sleep(12)

            except Exception as exc:
                print(f"[Market] {entity_name} ({ticker}): {exc}")

    return stored
