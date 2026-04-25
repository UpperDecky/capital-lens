"""
News RSS ingestor — 150+ feeds covering finance, geopolitics, defense, and tech.
Uses feedparser (already in requirements). No API key required for any feed.
Polls every 10 minutes; entity matching stores relevant articles as news events.
"""
import uuid
import feedparser
from datetime import datetime, timezone
from typing import Any

# ── Master feed list ─────────────────────────────────────────────────────────
RSS_FEEDS: list[str] = [
    # Major wire services
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/Reuters/worldNews",
    "https://feeds.reuters.com/reuters/companyNews",
    "https://feeds.reuters.com/reuters/USenergyNews",
    "https://feeds.apnews.com/rss/apf-topnews",
    "https://feeds.apnews.com/rss/apf-business",
    "https://feeds.apnews.com/rss/apf-technology",
    "https://feeds.apnews.com/rss/apf-politics",
    "https://feeds.apnews.com/rss/apf-WorldNews",
    # BBC
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/news/politics/rss.xml",
    "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "https://feeds.bbci.co.uk/news/world/europe/rss.xml",
    "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
    # Al Jazeera
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://www.aljazeera.com/xml/rss/features.xml",
    # CNN
    "http://rss.cnn.com/rss/cnn_latest.rss",
    "http://rss.cnn.com/rss/money_news_international.rss",
    "http://rss.cnn.com/rss/cnn_world.rss",
    "http://rss.cnn.com/rss/cnn_tech.rss",
    # Financial Times
    "https://www.ft.com/rss/home",
    "https://www.ft.com/rss/home/uk",
    "https://www.ft.com/rss/home/us",
    # Wall Street Journal
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://feeds.a.dj.com/rss/RSSWSJD.xml",
    "https://feeds.a.dj.com/rss/RSSOpinion.xml",
    # Bloomberg
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.bloomberg.com/technology/news.rss",
    "https://feeds.bloomberg.com/politics/news.rss",
    # CNBC
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    "https://www.cnbc.com/id/15839135/device/rss/rss.html",
    # NYT / WaPo
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.washingtonpost.com/rss/world",
    "https://feeds.washingtonpost.com/rss/business",
    "https://feeds.washingtonpost.com/rss/technology",
    # The Economist
    "https://www.economist.com/finance-and-economics/rss.xml",
    "https://www.economist.com/business/rss.xml",
    "https://www.economist.com/international/rss.xml",
    # Asia / Pacific
    "https://asia.nikkei.com/rss/feed/nar",
    "https://www.scmp.com/rss/91/feed",
    "https://www.scmp.com/rss/2/feed",
    "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://english.kyodonews.net/rss/news.xml",
    # Middle East / Gulf
    "https://www.arabnews.com/rss.xml",
    "https://english.alarabiya.net/rss.xml",
    "https://www.timesofisrael.com/feed/",
    "https://www.middleeasteye.net/rss",
    # Africa
    "https://www.allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
    # Europe
    "https://www.euronews.com/rss?format=mrss&level=theme&name=news",
    "https://www.politico.eu/feed/",
    "https://www.dw.com/en/latest-news/s-9097/rss",
    "https://www.lemonde.fr/en/rss/une.xml",
    # Defense & Security
    "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml",
    "https://news.usni.org/feed",
    "https://warontherocks.com/feed/",
    "https://breakingdefense.com/feed/",
    "https://thedefensepost.com/feed/",
    "https://www.c4isrnet.com/arc/outboundfeeds/rss/?outputType=xml",
    "https://taskandpurpose.com/feed/",
    "https://theaviationist.com/feed/",
    "https://ukdefencejournal.org.uk/feed/",
    "https://www.airandspaceforces.com/feed/",
    "https://nationalinterest.org/rss.xml",
    "https://www.19fortyfive.com/feed/",
    # Technology / AI
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://arstechnica.com/feed/",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://www.wired.com/feed/rss",
    "https://spectrum.ieee.org/rss/fulltext",
    # Semiconductors / Supply Chain
    "https://www.tomshardware.com/feeds/all",
    "https://semianalysis.com/feed/",
    # Energy / Commodities
    "https://oilprice.com/rss/main",
    "https://www.eia.gov/rss/news.xml",
    "https://www.mining.com/feed/",
    # Finance / Markets
    "https://feeds.marketwatch.com/marketwatch/topstories",
    "https://feeds.marketwatch.com/marketwatch/marketpulse",
    "https://finance.yahoo.com/rss/topfinstories",
    "https://www.zerohedge.com/fullrss2.xml",
    # Macro / Economic
    "https://www.imf.org/en/News/rss?",
    "https://www.worldbank.org/en/news/all.rss",
    # Crypto / Blockchain
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    # Geopolitics / Think-tanks
    "https://foreignpolicy.com/feed/",
    "https://www.foreignaffairs.com/rss.xml",
    "https://www.chathamhouse.org/rss.xml",
    "https://www.brookings.edu/feed/",
    "https://www.rand.org/blog/rand-review.xml",
    "https://carnegieendowment.org/rss/",
    "https://www.cfr.org/rss.xml",
    # US Government / Policy
    "https://thehill.com/homenews/feed/",
    "https://www.politico.com/rss/politics08.xml",
    "https://www.govexec.com/rss/all/",
    # Cybersecurity
    "https://www.darkreading.com/rss.xml",
    "https://krebsonsecurity.com/feed/",
    "https://www.bleepingcomputer.com/feed/",
    "https://securityweek.com/feed/",
    "https://thehackernews.com/feeds/posts/default",
    # Space / Aerospace
    "https://spaceflightnow.com/feed/",
    "https://www.nasaspaceflight.com/feed/",
    "https://www.space.com/feeds/all",
    "https://aviationweek.com/rss/defense-space",
    # Substack (RSS, no auth required)
    "https://www.geopolitics.world/feed",
    "https://www.notboring.co/feed",
    "https://thedeepdive.substack.com/feed",
    "https://www.exponentialview.co/feed",
]

# ── Entity keyword matching ───────────────────────────────────────────────────
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
    "boeing":   "Boeing",
    "raytheon": "Raytheon",
    "general dynamics": "General Dynamics",
    "federal reserve":  "Federal Reserve",
    "fed rate":         "Federal Reserve",
    "us treasury":      "US Treasury",
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

# Source names indexed by feed URL (used for source_name in events)
FEED_SOURCE_NAMES: dict[str, str] = {
    "reuters.com":     "Reuters",
    "apnews.com":      "AP",
    "bbci.co.uk":      "BBC",
    "aljazeera.com":   "Al Jazeera",
    "cnn.com":         "CNN",
    "ft.com":          "FT",
    "dj.com":          "WSJ",
    "bloomberg.com":   "Bloomberg",
    "cnbc.com":        "CNBC",
    "nytimes.com":     "NYT",
    "washingtonpost":  "WaPo",
    "economist.com":   "Economist",
    "nikkei.com":      "Nikkei",
    "scmp.com":        "SCMP",
    "defensenews.com": "Defense News",
    "usni.org":        "USNI News",
    "warontherocks":   "War on the Rocks",
    "breakingdefense": "Breaking Defense",
    "theaviationist":  "The Aviationist",
    "techcrunch.com":  "TechCrunch",
    "theverge.com":    "The Verge",
    "wired.com":       "Wired",
    "oilprice.com":    "OilPrice",
    "cointelegraph":   "CoinTelegraph",
    "coindesk.com":    "CoinDesk",
    "foreignpolicy":   "Foreign Policy",
    "foreignaffairs":  "Foreign Affairs",
    "cfr.org":         "CFR",
    "brookings.edu":   "Brookings",
    "rand.org":        "RAND",
    "darkreading":     "Dark Reading",
    "krebsonsecurity": "Krebs on Security",
    "spaceflightnow":  "Spaceflight Now",
    "thehill.com":     "The Hill",
    "politico.com":    "Politico",
    "marketwatch":     "MarketWatch",
    "yahoo.com":       "Yahoo Finance",
    "zerohedge":       "ZeroHedge",
    "imf.org":         "IMF",
    "worldbank.org":   "World Bank",
    "arabnews.com":    "Arab News",
    "timesofisrael":   "Times of Israel",
    "middleeasteye":   "Middle East Eye",
    "euronews.com":    "Euronews",
    "dw.com":          "DW",
    "chathamhouse":    "Chatham House",
    "substack.com":    "Substack",
}


def _source_name_from_url(url: str) -> str:
    """Infer a clean source name from a feed URL."""
    for fragment, name in FEED_SOURCE_NAMES.items():
        if fragment in url:
            return name
    # Fall back to domain extraction
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "").replace("feeds.", "")
        return domain.split(".")[0].title()
    except Exception:
        return "News"


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
    Pull all RSS feeds and store entity-matched articles as news events.
    Returns count of new events inserted.
    """
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            source_name = _source_name_from_url(feed_url)

            for entry in feed.entries[:20]:
                title   = entry.get("title", "")
                summary = entry.get("summary", "")
                link    = entry.get("link", "")
                published = entry.get("published", "")

                # Normalise date
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
                if db_conn.execute("SELECT 1 FROM events WHERE source_url=?", (link,)).fetchone():
                    continue

                # Compute importance score
                from backend.scoring import score_event
                entity_row = db_conn.execute(
                    "SELECT net_worth FROM entities WHERE id=?", (entity_id,)
                ).fetchone()
                entity_data = {"net_worth": entity_row[0] if entity_row else 0}
                importance = score_event(
                    {"headline": title, "event_type": "news", "source_name": source_name},
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
                        source_name,
                        date_str,
                        now,
                        importance,
                    ),
                )
                inserted += 1

        except Exception as exc:
            # Never crash the whole job over one bad feed
            print(f"[RSS] {feed_url[:60]}: {exc}")

    db_conn.commit()
    return inserted
