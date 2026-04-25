"""
Market data ingestor -- Twelve Data (real-time prices) + CoinGecko (crypto).

Market cap formula: live_price x shares_outstanding (from latest SEC 10-Q filings).
This gives accurate, real-time market cap that tracks NASDAQ/NYSE prices.

SHARES_OUTSTANDING must be updated quarterly when companies file 10-Q/10-K with SEC.
Last updated: Q1 2025 (filings through March 2025).

Twelve Data:   free 800 credits/day -- https://twelvedata.com/register
CoinGecko:     free demo key 30 calls/min -- https://www.coingecko.com/en/api/pricing
Alpha Vantage: legacy 25 req/day fallback -- https://www.alphavantage.co/support/#api-key
"""
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import (
    TWELVE_DATA_API_KEY,
    COINGECKO_API_KEY,
    ALPHA_VANTAGE_API_KEY,
)

# ---- Ticker map -----------------------------------------------------------------

STOCK_TICKER_MAP: dict[str, str] = {
    "Apple":              "AAPL",
    "Nvidia":             "NVDA",
    "Microsoft":          "MSFT",
    "Alphabet":           "GOOGL",
    "Meta":               "META",
    "Amazon":             "AMZN",
    "Tesla":              "TSLA",
    "Berkshire Hathaway": "BRK/B",
    "JPMorgan":           "JPM",
    "Goldman Sachs":      "GS",
    "BlackRock":          "BLK",
    "ExxonMobil":         "XOM",
    "Lockheed Martin":    "LMT",
    "Pfizer":             "PFE",
    "Walmart":            "WMT",
    "Visa":               "V",
    "Palantir":           "PLTR",
    "Boeing":             "BA",
    "Raytheon":           "RTX",
    "General Dynamics":   "GD",
}

# ---- Shares outstanding (from latest SEC 10-Q / 10-K filings) -------------------
# Source: SEC EDGAR quarterly filings, Q1 2025.
# Update this table every quarter after each company files.
# market_cap = last_price x shares_outstanding

SHARES_OUTSTANDING: dict[str, int] = {
    # Ticker  ->  shares (basic, from most recent 10-Q)
    "AAPL":  15_115_823_000,   # Apple Q2 FY2025 10-Q
    "NVDA":  24_440_000_000,   # Nvidia Q4 FY2025 10-Q
    "MSFT":   7_434_000_000,   # Microsoft Q3 FY2025 10-Q
    "GOOGL": 12_176_000_000,   # Alphabet Q1 2025 10-Q (class A+B+C)
    "META":   2_561_000_000,   # Meta Q1 2025 10-Q
    "AMZN":  10_535_000_000,   # Amazon Q1 2025 10-Q
    "TSLA":   3_200_000_000,   # Tesla Q1 2025 10-Q
    "BRK/B":  2_165_000_000,   # Berkshire Q1 2025 (B-equivalent: A*1500 + B)
    "JPM":    2_837_000_000,   # JPMorgan Q1 2025 10-Q
    "GS":       298_000_000,   # Goldman Sachs Q1 2025 10-Q
    "BLK":      150_000_000,   # BlackRock Q1 2025 10-Q
    "XOM":    4_270_000_000,   # ExxonMobil Q1 2025 10-Q
    "LMT":      241_000_000,   # Lockheed Martin Q1 2025 10-Q
    "PFE":    5_638_000_000,   # Pfizer Q1 2025 10-Q
    "WMT":    7_987_000_000,   # Walmart Q4 FY2025 10-K
    "V":      2_065_000_000,   # Visa Q2 FY2025 10-Q
    "PLTR":   2_143_000_000,   # Palantir Q1 2025 10-Q
    "BA":       769_000_000,   # Boeing Q1 2025 10-Q
    "RTX":    1_316_000_000,   # Raytheon Q1 2025 10-Q
    "GD":       243_000_000,   # General Dynamics Q1 2025 10-Q
}

TOP_CRYPTO_IDS: list[str] = [
    "bitcoin", "ethereum", "solana", "binancecoin", "ripple",
    "cardano", "avalanche-2", "polkadot", "chainlink", "uniswap",
    "dogecoin", "shiba-inu", "toncoin", "near", "polygon",
]

_HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept": "application/json",
}


# ---- Twelve Data ----------------------------------------------------------------

def _fetch_twelve_data(entity_map: dict[str, str], db_conn: Any) -> int:
    """
    Batch-fetch real-time prices from Twelve Data (1 API credit for all symbols).
    Computes market_cap = price x shares_outstanding and stores as net_worth.
    Returns number of entities updated.
    """
    if not TWELVE_DATA_API_KEY:
        return 0

    symbols = ",".join(STOCK_TICKER_MAP.values())
    now = datetime.now(timezone.utc).isoformat()
    stored = 0

    try:
        with httpx.Client(headers=_HEADERS, timeout=30) as client:
            resp = client.get(
                "https://api.twelvedata.com/price",
                params={"symbol": symbols, "apikey": TWELVE_DATA_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        print(f"[Market/TwelveData] Fetch error: {exc}")
        return 0

    # Single-symbol response wraps differently from multi-symbol
    if "price" in data and isinstance(data.get("price"), str):
        first_ticker = list(STOCK_TICKER_MAP.values())[0]
        data = {first_ticker: data}

    for entity_name, ticker in STOCK_TICKER_MAP.items():
        entity_id = entity_map.get(entity_name)
        if not entity_id:
            continue

        ticker_data = data.get(ticker, {})
        if not ticker_data or "price" not in ticker_data:
            continue
        if ticker_data.get("status") == "error":
            print(f"[Market/TwelveData] {ticker}: {ticker_data.get('message', 'error')}")
            continue

        try:
            price = float(ticker_data["price"])
        except (TypeError, ValueError):
            continue

        # Compute market cap from live price x verified shares outstanding
        shares = SHARES_OUTSTANDING.get(ticker)
        market_cap = price * shares if shares else None

        if market_cap:
            db_conn.execute(
                """UPDATE entities
                   SET last_price=?, price_updated_at=?, ticker=?,
                       net_worth=?, net_worth_updated_at=?, net_worth_source=?
                   WHERE id=?""",
                (price, now, ticker, market_cap, now, f"twelve_data:{ticker}", entity_id),
            )
            print(
                f"[Market/TwelveData] {entity_name} ({ticker}): "
                f"${price:,.2f} | MCap ${market_cap/1e12:.3f}T"
            )
        else:
            db_conn.execute(
                "UPDATE entities SET last_price=?, price_updated_at=?, ticker=? WHERE id=?",
                (price, now, ticker, entity_id),
            )
            print(f"[Market/TwelveData] {entity_name} ({ticker}): ${price:,.2f}")

        stored += 1

    if stored:
        db_conn.commit()
        print(f"[Market/TwelveData] Updated {stored} prices + market caps")
    return stored


# ---- CoinGecko ------------------------------------------------------------------

def _fetch_coingecko(db_conn: Any) -> dict[str, float]:
    """Fetch top crypto prices + market caps from CoinGecko."""
    ids = ",".join(TOP_CRYPTO_IDS)
    params: dict = {
        "ids": ids,
        "vs_currencies": "usd",
        "include_24hr_change": "true",
        "include_market_cap": "true",
    }
    if COINGECKO_API_KEY:
        params["x_cg_demo_api_key"] = COINGECKO_API_KEY

    prices: dict[str, float] = {}
    try:
        with httpx.Client(headers=_HEADERS, timeout=20) as client:
            resp = client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params=params,
            )
            if resp.status_code == 429:
                print("[Market/CoinGecko] Rate limited -- will retry next cycle")
                return prices
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        print(f"[Market/CoinGecko] Fetch error: {exc}")
        return prices

    for coin_id, info in data.items():
        price  = info.get("usd")
        change = info.get("usd_24h_change")
        mktcap = info.get("usd_market_cap")
        if price is not None:
            prices[coin_id] = float(price)
            change_label = f" ({change:+.1f}% 24h)" if change is not None else ""
            mcap_label   = f" MCap ${mktcap/1e9:.1f}B" if mktcap else ""
            print(f"[Market/CoinGecko] {coin_id}: ${price:,.2f}{change_label}{mcap_label}")

    if prices:
        print(f"[Market/CoinGecko] Fetched {len(prices)} crypto prices")
    return prices


# ---- Alpha Vantage fallback (when no Twelve Data key) --------------------------

def _fetch_alpha_vantage(entity_map: dict[str, str], db_conn: Any) -> int:
    """Legacy Alpha Vantage fallback (25 req/day). Only runs if Twelve Data key absent."""
    if not ALPHA_VANTAGE_API_KEY:
        return 0

    AV_BASE = "https://www.alphavantage.co/query"
    now = datetime.now(timezone.utc).isoformat()
    stored = 0

    with httpx.Client(timeout=15) as client:
        for entity_name, ticker in STOCK_TICKER_MAP.items():
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
                if "Note" in data or "Information" in data:
                    print("[Market/AV] Rate limit hit -- stopping")
                    break
                quote = data.get("Global Quote", {})
                price_str = quote.get("05. price", "")
                if not price_str:
                    continue
                price = float(price_str)
                shares = SHARES_OUTSTANDING.get(ticker)
                market_cap = price * shares if shares else None
                if market_cap:
                    db_conn.execute(
                        """UPDATE entities
                           SET last_price=?, price_updated_at=?, ticker=?,
                               net_worth=?, net_worth_updated_at=?, net_worth_source=?
                           WHERE id=?""",
                        (price, now, ticker, market_cap, now, f"alpha_vantage:{ticker}", entity_id),
                    )
                else:
                    db_conn.execute(
                        "UPDATE entities SET last_price=?, price_updated_at=?, ticker=? WHERE id=?",
                        (price, now, ticker, entity_id),
                    )
                db_conn.commit()
                stored += 1
                time.sleep(12)  # 5 req/min free limit
            except Exception as exc:
                print(f"[Market/AV] {ticker}: {exc}")

    return stored


# ---- Public entry point ---------------------------------------------------------

def fetch_market_prices(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch real-time stock prices, compute live market caps, update net_worth.
    Also fetches crypto prices from CoinGecko.
    Returns count of entities with updated prices.
    """
    total = 0

    if TWELVE_DATA_API_KEY:
        total += _fetch_twelve_data(entity_map, db_conn)
    elif ALPHA_VANTAGE_API_KEY:
        print("[Market] No TWELVE_DATA_API_KEY -- falling back to Alpha Vantage (25 req/day)")
        total += _fetch_alpha_vantage(entity_map, db_conn)
    else:
        print("[Market] No stock API key. Set TWELVE_DATA_API_KEY in .env (free at twelvedata.com)")

    _fetch_coingecko(db_conn)
    return total
