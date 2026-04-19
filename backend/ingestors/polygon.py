"""
Polygon.io news ingestor — ticker-specific news with sentiment.

Optional — only runs if POLYGON_API_KEY is set in .env.
Free tier available at https://polygon.io (signup required).
Paid tier ($29/mo) adds real-time data and options flow.

This ingestor pulls the latest news articles for each tracked company
from Polygon's news API, which is higher quality than Reuters RSS
because it's ticker-specific and includes sentiment scores.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
import httpx

from backend.config import POLYGON_API_KEY

BASE_URL = "https://api.polygon.io/v2"

HEADERS = {
    "User-Agent": "CapitalLens research@capitallens.dev",
    "Accept": "application/json",
}

# Ticker → entity name mapping for seeded companies
TICKER_MAP: dict[str, str] = {
    "AAPL":  "Apple",
    "NVDA":  "Nvidia",
    "MSFT":  "Microsoft",
    "GOOGL": "Alphabet",
    "META":  "Meta",
    "AMZN":  "Amazon",
    "TSLA":  "Tesla",
    "BRK.B": "Berkshire Hathaway",
    "JPM":   "JPMorgan",
    "GS":    "Goldman Sachs",
    "BLK":   "BlackRock",
    "XOM":   "ExxonMobil",
    "LMT":   "Lockheed Martin",
    "PFE":   "Pfizer",
    "WMT":   "Walmart",
    "V":     "Visa",
    "PLTR":  "Palantir",
    "BA":    "Boeing",
    "RTX":   "Raytheon",
    "GD":    "General Dynamics",
}

# Sentiment tiers for importance bumping
SENTIMENT_BOOST: dict[str, int] = {
    "positive": 1,
    "negative": 1,  # Negative news is equally important
    "neutral":  0,
}


def _fetch_ticker_news(ticker: str, days_back: int = 7) -> list[dict]:
    """Fetch recent news articles for a ticker from Polygon."""
    if not POLYGON_API_KEY:
        return []

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with httpx.Client(headers=HEADERS, timeout=20) as client:
            resp = client.get(
                f"{BASE_URL}/reference/news",
                params={
                    "apiKey":       POLYGON_API_KEY,
                    "ticker":       ticker,
                    "published_utc.gte": cutoff,
                    "order":        "desc",
                    "limit":        10,
                    "sort":         "published_utc",
                },
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as exc:
        if "403" in str(exc) or "401" in str(exc):
            print(f"[Polygon] Auth error — check your POLYGON_API_KEY")
        else:
            print(f"[Polygon] Error fetching news for {ticker}: {exc}")
    return []


def fetch_polygon_news(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch ticker-specific news from Polygon.io for all tracked companies.
    Skips gracefully if POLYGON_API_KEY is not set.

    Returns count of new events inserted.
    """
    if not POLYGON_API_KEY:
        # Silently skip — Polygon is optional
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for ticker, entity_name in TICKER_MAP.items():
        entity_id = entity_map.get(entity_name)
        if not entity_id:
            continue

        articles = _fetch_ticker_news(ticker)

        for article in articles:
            title       = (article.get("title") or "").strip()
            article_url = (article.get("article_url") or "").strip()
            source      = (article.get("publisher", {}) or {}).get("name", "Polygon News")
            pub_date    = (article.get("published_utc") or "")[:10]  # YYYY-MM-DD

            if not title:
                continue

            # Build headline
            headline = f"{title} [{ticker}] — {source}"

            # Deduplicate by source URL
            exists = db_conn.execute(
                "SELECT 1 FROM events WHERE source_url=? OR (entity_id=? AND headline=?)",
                (article_url, entity_id, headline),
            ).fetchone()
            if exists:
                continue

            # Sentiment insight from Polygon
            insights = article.get("insights", [])
            ticker_insight = next(
                (i for i in insights if i.get("ticker") == ticker),
                None
            )
            sentiment = (ticker_insight or {}).get("sentiment", "neutral")
            sentiment_reasoning = (ticker_insight or {}).get("sentiment_reasoning", "")

            # Score and optionally bump for non-neutral sentiment
            from backend.scoring import score_event
            event_draft = {
                "headline":   headline,
                "amount":     None,
                "event_type": "news",
                "source_name": source,
            }
            base_importance = score_event(event_draft)
            importance = min(5, base_importance + SENTIMENT_BOOST.get(sentiment, 0))

            # Include sentiment reasoning in plain_english if available
            # (pre-fill so enrichment can build on it)
            pre_enriched = (
                f"Polygon sentiment: {sentiment}. {sentiment_reasoning}"
                if sentiment_reasoning else None
            )

            db_conn.execute(
                """INSERT INTO events
                   (id, entity_id, event_type, headline, amount, currency,
                    source_url, source_name, occurred_at, ingested_at, importance, plain_english)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    entity_id,
                    "news",
                    headline,
                    None,   # Polygon news articles don't have a $ amount
                    "USD",
                    article_url,
                    source,
                    pub_date,
                    now,
                    importance,
                    pre_enriched,
                ),
            )
            inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[Polygon] ✓ Inserted {inserted} new ticker news events")
    return inserted
