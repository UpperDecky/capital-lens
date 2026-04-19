"""Database connection, schema, and seed data for Capital Lens."""
import sqlite3
import uuid
import os
from datetime import datetime, timezone
from pathlib import Path


def get_db_path() -> str:
    env_path = os.getenv("DB_PATH")
    if env_path:
        return env_path
    return str(Path(__file__).parent.parent / "capital_lens.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL CHECK(type IN ('company','individual')),
            sector      TEXT NOT NULL,
            net_worth   REAL,
            description TEXT,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id            TEXT PRIMARY KEY,
            entity_id     TEXT NOT NULL REFERENCES entities(id),
            event_type    TEXT NOT NULL CHECK(event_type IN ('filing','insider_sale','acquisition','news')),
            headline      TEXT NOT NULL,
            amount        REAL,
            currency      TEXT DEFAULT 'USD',
            source_url    TEXT,
            source_name   TEXT,
            occurred_at   TEXT,
            ingested_at   TEXT NOT NULL,
            plain_english TEXT,
            market_impact TEXT,
            invest_signal TEXT,
            for_you       TEXT,
            sector_tags   TEXT,
            enriched_at   TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_events_entity   ON events(entity_id);
        CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_type     ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_ingested ON events(ingested_at DESC);

        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tier          TEXT NOT NULL DEFAULT 'free' CHECK(tier IN ('free','pro')),
            created_at    TEXT NOT NULL
        );
    """)
    for col_def in [
        "ALTER TABLE events ADD COLUMN analysis TEXT",
        "ALTER TABLE entities ADD COLUMN last_price REAL",
        "ALTER TABLE entities ADD COLUMN price_updated_at TEXT",
        "ALTER TABLE entities ADD COLUMN ticker TEXT",
        "ALTER TABLE entities ADD COLUMN funding_sources TEXT",
        "ALTER TABLE events ADD COLUMN importance INTEGER DEFAULT 3",
        "ALTER TABLE events ADD COLUMN subtype TEXT",
    ]:
        try:
            conn.execute(col_def)
            conn.commit()
        except Exception:
            pass

    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_importance ON events(importance DESC)")
        conn.commit()
    except Exception:
        pass

    try:
        probe_entity = conn.execute("SELECT id FROM entities LIMIT 1").fetchone()
        if probe_entity:
            conn.execute(
                "INSERT INTO events (id, entity_id, event_type, headline, ingested_at) "
                "VALUES ('__probe_ct__', ?, 'congressional_trade', 'probe', 'probe')",
                (probe_entity[0],),
            )
            conn.execute("DELETE FROM events WHERE id='__probe_ct__'")
            conn.commit()
    except Exception:
        conn.rollback()
        conn.executescript("""
            PRAGMA foreign_keys=OFF;
            CREATE TABLE events_v2 (
                id            TEXT PRIMARY KEY,
                entity_id     TEXT NOT NULL REFERENCES entities(id),
                event_type    TEXT NOT NULL CHECK(event_type IN (
                              'filing','insider_sale','acquisition',
                              'news','congressional_trade')),
                subtype       TEXT,
                headline      TEXT NOT NULL,
                amount        REAL,
                currency      TEXT DEFAULT 'USD',
                source_url    TEXT,
                source_name   TEXT,
                occurred_at   TEXT,
                ingested_at   TEXT NOT NULL,
                plain_english TEXT,
                market_impact TEXT,
                invest_signal TEXT,
                for_you       TEXT,
                sector_tags   TEXT,
                enriched_at   TEXT,
                analysis      TEXT,
                importance    INTEGER DEFAULT 3
            );
            INSERT INTO events_v2
                (id, entity_id, event_type, subtype, headline, amount, currency,
                 source_url, source_name, occurred_at, ingested_at,
                 plain_english, market_impact, invest_signal, for_you,
                 sector_tags, enriched_at, analysis, importance)
            SELECT id, entity_id,
                CASE WHEN event_type = 'insider_sale'
                          AND (subtype = 'congressional_trade' OR headline LIKE '%congressional%')
                     THEN 'congressional_trade' ELSE event_type END,
                subtype, headline, amount, currency,
                source_url, source_name, occurred_at, ingested_at,
                plain_english, market_impact, invest_signal, for_you,
                sector_tags, enriched_at, analysis, importance
            FROM events;
            DROP TABLE events;
            ALTER TABLE events_v2 RENAME TO events;
            CREATE INDEX IF NOT EXISTS idx_events_entity     ON events(entity_id);
            CREATE INDEX IF NOT EXISTS idx_events_occurred   ON events(occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_type       ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_ingested   ON events(ingested_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_importance ON events(importance DESC);
            PRAGMA foreign_keys=ON;
        """)
        conn.commit()
        print("[DB] Migrated events table -- congressional_trade type enabled")

    conn.commit()
    conn.close()


def seed_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        ("Apple",              "company",    "Technology",   3.0e12, "Consumer electronics and software"),
        ("Nvidia",             "company",    "Technology",   2.8e12, "AI chips and GPU computing"),
        ("Microsoft",          "company",    "Technology",   3.1e12, "Cloud computing and enterprise software"),
        ("Alphabet",           "company",    "Technology",   2.2e12, "Search, advertising, and cloud"),
        ("Meta",               "company",    "Technology",   1.2e12, "Social media and virtual reality"),
        ("Amazon",             "company",    "E-Commerce",   1.9e12, "E-commerce, cloud, and logistics"),
        ("Tesla",              "company",    "Automotive",   6.0e11, "Electric vehicles and energy storage"),
        ("Berkshire Hathaway", "company",    "Finance",      9.0e11, "Diversified holding conglomerate"),
        ("JPMorgan",           "company",    "Finance",      7.0e11, "Global banking and financial services"),
        ("Goldman Sachs",      "company",    "Finance",      1.5e11, "Investment banking and asset management"),
        ("BlackRock",          "company",    "Finance",      1.3e11, "World's largest asset manager"),
        ("ExxonMobil",         "company",    "Energy",       5.0e11, "Oil and natural gas exploration"),
        ("Lockheed Martin",    "company",    "Defense",      1.3e11, "Aerospace and defense systems"),
        ("Pfizer",             "company",    "Healthcare",   1.7e11, "Pharmaceuticals and vaccines"),
        ("Walmart",            "company",    "Retail",       5.0e11, "Global retail and grocery"),
        ("Visa",               "company",    "Finance",      5.5e11, "Electronic payment network"),
        ("Palantir",           "company",    "Technology",   5.0e10, "Data analytics and AI for government"),
        ("SpaceX",             "company",    "Aerospace",    2.0e11, "Rocket launches and satellite internet"),
        ("OpenAI",             "company",    "Technology",   8.0e10, "AI research and products"),
        ("Anthropic",          "company",    "Technology",   1.8e10, "AI safety research and Claude AI"),
        ("Elon Musk",          "individual", "Technology",   2.3e11, "CEO of Tesla, SpaceX; owner of X"),
        ("Jeff Bezos",         "individual", "E-Commerce",   1.7e11, "Founder of Amazon"),
        ("Bill Gates",         "individual", "Technology",   1.3e11, "Co-founder of Microsoft"),
        ("Mark Zuckerberg",    "individual", "Technology",   1.7e11, "CEO of Meta"),
        ("Warren Buffett",     "individual", "Finance",      1.1e11, "CEO of Berkshire Hathaway"),
        ("Larry Ellison",      "individual", "Technology",   1.4e11, "Co-founder of Oracle"),
        ("Ken Griffin",        "individual", "Finance",      3.5e10, "Founder of Citadel"),
        ("Ray Dalio",          "individual", "Finance",      1.9e10, "Founder of Bridgewater Associates"),
        ("George Soros",       "individual", "Finance",      6.7e9,  "Founder of Soros Fund Management"),
        ("Carl Icahn",         "individual", "Finance",      7.0e9,  "Activist investor"),
        ("Nancy Pelosi",       "individual", "Government",   1.1e8,  "Former Speaker of the US House; known for high-profile stock trades"),
        ("Donald Trump",       "individual", "Government",   7.0e9,  "47th US President; real estate developer; Truth Social owner"),
        ("Mitch McConnell",    "individual", "Government",   3.4e7,  "US Senate Minority Leader; Kentucky senator"),
        ("Mitt Romney",        "individual", "Government",   2.5e8,  "Former US Senator, Utah; private equity veteran (Bain Capital)"),
        ("Tommy Tuberville",   "individual", "Government",   1.1e7,  "US Senator, Alabama; known for active individual stock trading"),
        ("Ro Khanna",          "individual", "Government",   2.0e7,  "US Representative, Silicon Valley; prominent tech policy voice"),
        ("Alexandria Ocasio-Cortez", "individual", "Government", 1.0e6, "US Representative, New York; progressive policy advocate"),
        ("Dan Crenshaw",       "individual", "Government",   3.5e6,  "US Representative, Texas; national security focus"),
        ("Gavin Newsom",       "individual", "Government",   2.0e7,  "Governor of California; clean energy and tech policy shaper"),
        ("Pete Buttigieg",     "individual", "Government",   7.0e6,  "Former US Secretary of Transportation; infrastructure and EV policy"),
        ("Federal Reserve",    "company",    "Finance",      0.0,    "US central bank -- sets interest rates and monetary policy"),
        ("US Treasury",        "company",    "Government",   0.0,    "US Treasury Department -- issues debt, enforces sanctions, manages fiscal policy"),
        ("Boeing",             "company",    "Defense",      1.1e11, "Aerospace manufacturer -- commercial jets and defense systems"),
        ("Raytheon",           "company",    "Defense",      1.6e11, "Defense contractor -- missiles, radar, cybersecurity"),
        ("General Dynamics",   "company",    "Defense",      6.5e10, "Defense and IT services -- ships, submarines, Gulfstream jets"),
    ]
    for name, etype, sector, net_worth, desc in rows:
        exists = cur.execute("SELECT 1 FROM entities WHERE name=?", (name,)).fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO entities (id,name,type,sector,net_worth,description,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (str(uuid.uuid4()), name, etype, sector, net_worth, desc, now),
            )
    conn.commit()
    conn.close()
    print("Seed complete.")


def seed_events() -> None:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id,name FROM entities").fetchall()}
    sample_events = [
        ("Apple",     "filing",      "Apple filed 10-K: record $119B quarterly revenue, iPhone 16 drives growth",
         119_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193",
         "SEC EDGAR", "2025-02-01"),
        ("Nvidia",    "filing",      "Nvidia filed 8-K: Q4 revenue hits $39B, data center revenue up 93% YoY",
         39_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810",
         "SEC EDGAR", "2025-02-26"),
        ("Microsoft", "acquisition", "Microsoft completes $68.7B acquisition of Activision Blizzard",
         68_700_000_000.0, "USD",
         "https://news.microsoft.com/2023/10/13/microsoft-completes-acquisition-of-activision-blizzard/",
         "Microsoft News", "2025-01-10"),
        ("Meta",      "filing",      "Meta filed 8-K: announces $50B share buyback and first-ever dividend",
         50_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001326801",
         "SEC EDGAR", "2025-02-01"),
        ("Tesla",     "insider_sale","Elon Musk filed Form 4: sold 10.5M Tesla shares",
         3_580_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001318605",
         "SEC EDGAR", "2025-01-20"),
        ("Amazon",    "filing",      "Amazon filed 10-K: AWS revenue surpasses $100B annually",
         100_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001018724",
         "SEC EDGAR", "2025-02-03"),
        ("Alphabet",  "filing",      "Alphabet filed 8-K: announces $70B share buyback program",
         70_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001652044",
         "SEC EDGAR", "2025-01-28"),
        ("JPMorgan",  "filing",      "JPMorgan filed 10-K: record $50B full-year profit",
         50_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000019617",
         "SEC EDGAR", "2025-02-06"),
        ("Goldman Sachs", "filing",  "Goldman Sachs filed 10-Q: investment banking fees surge 24%",
         None, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000886982",
         "SEC EDGAR", "2025-02-10"),
        ("ExxonMobil","filing",      "ExxonMobil filed 10-K: $36B net income on high oil prices",
         36_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000034088",
         "SEC EDGAR", "2025-02-14"),
        ("Palantir",  "filing",      "Palantir filed 8-K: US government AI contract worth $480M",
         480_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001321655",
         "SEC EDGAR", "2025-01-25"),
        ("Pfizer",    "acquisition", "Pfizer completes $43B acquisition of Seagen oncology unit",
         43_000_000_000.0, "USD",
         "https://www.pfizer.com/news/press-release/press-release-detail/pfizer-completes-acquisition-seagen",
         "Pfizer IR", "2025-01-08"),
        ("BlackRock", "filing",      "BlackRock 13F-HR: AUM reaches $10.5 trillion milestone",
         10_500_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001364742",
         "SEC EDGAR", "2025-01-15"),
        ("Berkshire Hathaway", "filing", "Berkshire Hathaway 13F-HR: new $4.1B position in Sirius XM",
         4_100_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001067983",
         "SEC EDGAR", "2025-01-12"),
        ("Lockheed Martin", "filing", "Lockheed Martin 8-K: wins $17B US Air Force contract for F-35 jets",
         17_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000936468",
         "SEC EDGAR", "2025-02-07"),
        ("Walmart",   "acquisition", "Walmart acquires smart TV maker Vizio for $2.3B",
         2_300_000_000.0, "USD",
         "https://corporate.walmart.com/news/2024/02/20/walmart-to-acquire-vizio",
         "Walmart IR", "2025-01-30"),
        ("Visa",      "filing",      "Visa filed 10-Q: payment volume up 8% YoY to $3.3T",
         3_300_000_000_000.0, "USD",
         "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001403161",
         "SEC EDGAR", "2025-02-04"),
        ("SpaceX",    "news",        "SpaceX Starship completes orbital test flight successfully",
         None, "USD",
         "https://www.spacex.com/updates/",
         "SpaceX", "2025-01-16"),
        ("OpenAI",    "news",        "OpenAI raises $6.6B Series C at $157B valuation",
         6_600_000_000.0, "USD",
         "https://openai.com/blog/",
         "OpenAI Blog", "2025-01-05"),
        ("Anthropic", "news",        "Anthropic raises $4B from Amazon, total funding exceeds $7.3B",
         4_000_000_000.0, "USD",
         "https://www.anthropic.com/news",
         "Anthropic Blog", "2025-01-18"),
    ]
    inserted = 0
    for (ename, etype, headline, amount, currency, url, source, date) in sample_events:
        entity_id = emap.get(ename)
        if not entity_id:
            continue
        exists = cur.execute(
            "SELECT 1 FROM events WHERE entity_id=? AND headline=?",
            (entity_id, headline),
        ).fetchone()
        if exists:
            continue
        cur.execute(
            "INSERT INTO events "
            "(id, entity_id, event_type, headline, amount, currency, "
            " source_url, source_name, occurred_at, ingested_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), entity_id, etype, headline,
             amount, currency, url, source, date, now),
        )
        inserted += 1
    conn.commit()
    conn.close()
    print(f"Seeded {inserted} sample events.")


if __name__ == "__main__":
    init_db()
    seed_db()
    seed_events()
