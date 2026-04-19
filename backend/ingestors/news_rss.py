"""Reuters RSS news ingestor — pulls business news every 10 minutes."""
import uuid
import feedparser
from datetime import datetime, timezone
from typing import Any

RSS_FEEDS: list[str] = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
]

# Keywords that map to our seeded entities
ENTITY_KEYWORDS: dict[str, str] = {
    # Companies
    "apple":    "Apple",     "aapl":       "Apple",
    "nvidia":   "Nvidia",    "nvda":       "Nvidia",
    "microsoft":"Microsoft", "msft":       "Microsoft",
    "alphabet": "Alphabet",  "google":     "Alphabet",  "googl": "Alphabet",
    "meta":     "Meta",      "facebook":   "Meta",
    "amazon":   "Amazon",    "amzn":       "Amazon",
    "tesla":    "Tesla",     "tsla":       "Tesla",
    "berkshire":"Berkshire Hathaway",
    "jpmorgan": "JPMorgan",  "jp morgan":  "JPMorgan",
    "goldman":  "Goldman Sachs",
    "blackrock":"BlackRock",
    "exxon":    "ExxonMobil","exxonmobil": "ExxonMobil",
    "lockheed": "Lockheed Martin",
    "pfizer":   "Pfizer",
    "walmart":  "Walmart",
    "visa":     "Visa",
    "palantir": "Palantir",
    "spacex":   "SpaceX",
    "openai":   "OpenAI",
    "anthropic":"Anthropic",
    # Individuals
    "elon musk":"Elon Musk", "musk":            "Elon Musk",
    "bezos":    "Jeff Bezos","jeff bezos":       "Jeff Bezos",
    "bill gates":"Bill Gates","gates":           "Bill Gates",
    "zuckerberg":"Mark Zuckerberg","mark zuckerberg":"Mark Zuckerberg",
    "warren buffett":"Warren Buffett","buffett":  "Warren Buffett",
    "larry ellison":"Larry Ellison","ellison":    "Larry Ellison",
    "ken griffin":"Ken Griffin",
    "ray dalio":"Ray Dalio",
    "george soros":"George Soros","soros":        "George Soros",
    "carl icahn":"Carl Icahn","icahn":            "Carl Icahn",
    # Politicians
    "nancy pelosi":"Nancy Pelosi","pelosi":       "Nancy Pelosi",
    "donald trump":"Donald Trump","trump":        "Donald Trump",
    "mitch mcconnell":"Mitch McConnell","mcconnell":"Mitch McConnell",
    "mitt romney":"Mitt Romney","romney":         "Mitt Romney",
    "tommy tuberville":"Tommy Tuberville","tuberville":"Tommy Tuberville",
    "ro khanna":"Ro Khanna",
    "alexandria ocasio-cortez":"Alexandria Ocasio-Cortez","aoc":"Alexandria Ocasio-Cortez",
    "dan crenshaw":"Dan Crenshaw",
    "gavin newsom":"Gavin Newsom","newsom":       "Gavin Newsom",
    "pete buttigieg":"Pete Buttigieg","buttigieg":"Pete Buttigieg",
}


def _find_entity(title: str, summary: str, entity_map: dict[str, str]) -> tuple[str | None, str | None]:
    """Return (entity_name, entity_id) for the first keyword match."""
    text = (title + " " + summary).lower()
    for keyword, entity_name in ENTITY_KEYWORDS.items():
        if keyword in text:
            entity_id = entity_map.get(entity_name)
            if entity_id:
                return entity_name, entity_id
    return None, None


def fetch_rss_news(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Pull Reuters RSS feeds and store relevant articles as news events.
    Returns count of new events inserted.
    """
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                # Normalize date
                try:
                    import email.utils
                    dt = email.utils.parsedate_to_datetime(published)
                    date_str = dt.date().isoformat()
                except Exception:
                    date_str = now[:10]

                entity_name, entity_id = _find_entity(title, summary, entity_map)
                if not entity_id:
                    continue

                # Deduplicate by source_url
                exists = db_conn.execute(
                    "SELECT 1 FROM events WHERE source_url=?", (link,)
                ).fetchone()
                if exists:
                    continue

                # Compute algorithmic importance score
                from backend.scoring import score_event
                entity_row = db_conn.execute(
                    "SELECT net_worth FROM entities WHERE id=?", (entity_id,)
                ).fetchone()
                entity_data = {"net_worth": entity_row[0] if entity_row else 0}
                importance = score_event(
                    {"headline": title, "event_type": "news", "source_name": "Reuters"},
                    entity_data,
                )

                db_conn.execute(
                    """INSERT INTO events
                       (id, entity_id, event_type, headline, source_url,
                        source_name, occurred_at, ingested_at, importance)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        entity_id,
                        "news",
                        title[:500],
                        link,
                        "Reuters",
                        date_str,
                        now,
                        importance,
                    ),
                )
                inserted += 1
        except Exception as exc:
            print(f"[RSS] {feed_url}: {exc}")

    db_conn.commit()
    return inserted
