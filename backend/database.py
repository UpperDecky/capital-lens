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

        CREATE TABLE IF NOT EXISTS countries (
            iso2            TEXT PRIMARY KEY,
            iso3            TEXT,
            iso_num         INTEGER,
            name            TEXT NOT NULL,
            continent       TEXT,
            gov_type        TEXT,
            political_lean  TEXT,
            conflict_status TEXT DEFAULT 'stable',
            alliances       TEXT,
            leader_name     TEXT,
            leader_title    TEXT,
            key_issues      TEXT,
            updated_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS geo_events (
            id          TEXT PRIMARY KEY,
            iso2        TEXT,
            headline    TEXT NOT NULL,
            url         TEXT,
            source      TEXT,
            occurred_at TEXT,
            tone        REAL,
            themes      TEXT,
            ingested_at TEXT NOT NULL
        );

        -- ADS-B aircraft position snapshots (OpenSky Network)
        CREATE TABLE IF NOT EXISTS adsb_events (
            id           TEXT PRIMARY KEY,
            icao24       TEXT NOT NULL,          -- ICAO 24-bit aircraft address
            callsign     TEXT,
            origin_country TEXT,
            latitude     REAL,
            longitude    REAL,
            altitude_m   REAL,
            velocity_ms  REAL,
            heading      REAL,
            on_ground    INTEGER DEFAULT 0,
            occurred_at  TEXT NOT NULL,
            ingested_at  TEXT NOT NULL,
            entity_id    TEXT REFERENCES entities(id)  -- set if aircraft linked to a seed entity
        );

        -- Maritime vessel AIS snapshots (aisstream.io)
        CREATE TABLE IF NOT EXISTS maritime_events (
            id           TEXT PRIMARY KEY,
            mmsi         TEXT NOT NULL,           -- Maritime Mobile Service Identity
            ship_name    TEXT,
            ship_type    TEXT,
            latitude     REAL,
            longitude    REAL,
            speed_knots  REAL,
            heading      REAL,
            destination  TEXT,
            flag_country TEXT,
            occurred_at  TEXT NOT NULL,
            ingested_at  TEXT NOT NULL
        );

        -- Satellite fire detections (NASA FIRMS)
        CREATE TABLE IF NOT EXISTS satellite_events (
            id              TEXT PRIMARY KEY,
            source          TEXT NOT NULL,       -- VIIRS_NOAA20_NRT | MODIS_NRT
            latitude        REAL NOT NULL,
            longitude       REAL NOT NULL,
            brightness      REAL,                -- fire radiative power (MW)
            confidence      TEXT,                -- low | nominal | high
            acq_date        TEXT,
            acq_time        TEXT,
            country_iso2    TEXT,
            ingested_at     TEXT NOT NULL
        );

        -- Prediction market snapshots (Polymarket)
        CREATE TABLE IF NOT EXISTS prediction_markets (
            id              TEXT PRIMARY KEY,    -- Polymarket market conditionId
            question        TEXT NOT NULL,
            category        TEXT,
            end_date        TEXT,
            yes_price       REAL,                -- 0.0–1.0 probability
            no_price        REAL,
            volume_usd      REAL,
            liquidity_usd   REAL,
            active          INTEGER DEFAULT 1,
            entity_id       TEXT REFERENCES entities(id),
            fetched_at      TEXT NOT NULL
        );

        -- ACLED conflict events (geo_events table handles these via source='ACLED')
        -- Cloudflare internet outage events
        CREATE TABLE IF NOT EXISTS infra_events (
            id           TEXT PRIMARY KEY,
            outage_type  TEXT,                   -- nationwide | regional | isp
            scope        TEXT,                   -- country/city/ASN affected
            cause        TEXT,
            iso2         TEXT,
            asn          TEXT,
            started_at   TEXT,
            ended_at     TEXT,
            ingested_at  TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_geo_events_iso2 ON geo_events(iso2);
        CREATE INDEX IF NOT EXISTS idx_geo_events_occurred ON geo_events(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_entity   ON events(entity_id);
        CREATE INDEX IF NOT EXISTS idx_events_occurred ON events(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_events_type     ON events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_ingested ON events(ingested_at DESC);
        CREATE INDEX IF NOT EXISTS idx_adsb_icao ON adsb_events(icao24);
        CREATE INDEX IF NOT EXISTS idx_adsb_occurred ON adsb_events(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_maritime_mmsi ON maritime_events(mmsi);
        CREATE INDEX IF NOT EXISTS idx_satellite_date ON satellite_events(acq_date DESC);
        CREATE INDEX IF NOT EXISTS idx_infra_started ON infra_events(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_pm_entity ON prediction_markets(entity_id);
        CREATE INDEX IF NOT EXISTS idx_pm_fetched ON prediction_markets(fetched_at DESC);

        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tier          TEXT NOT NULL DEFAULT 'free' CHECK(tier IN ('free','pro','admin')),
            created_at    TEXT NOT NULL
        );
    """)
    # entity_connections: structured graph edges with validity + confidence tracking
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS entity_connections (
            id           TEXT PRIMARY KEY,
            source_id    TEXT NOT NULL REFERENCES entities(id),
            target_id    TEXT NOT NULL REFERENCES entities(id),
            edge_type    TEXT NOT NULL,
            label        TEXT,
            weight       INTEGER DEFAULT 2,
            confidence   TEXT NOT NULL DEFAULT 'medium'
                         CHECK(confidence IN ('high','medium','low')),
            source_url   TEXT,
            source_name  TEXT,
            derived_from TEXT,
            valid_from   TEXT,
            valid_to     TEXT,
            ingested_at  TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_ec_source  ON entity_connections(source_id);
        CREATE INDEX IF NOT EXISTS idx_ec_target  ON entity_connections(target_id);
        CREATE INDEX IF NOT EXISTS idx_ec_valid   ON entity_connections(valid_to);
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ec_dedup
            ON entity_connections(source_id, target_id, edge_type);
    """)

    # cash_flows: global capital movement tracking (crypto, sanctions, VC, dark money)
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS cash_flows (
            id              TEXT PRIMARY KEY,
            flow_type       TEXT NOT NULL,
            asset           TEXT,
            amount_usd      REAL,
            source_label    TEXT,
            dest_label      TEXT,
            source_country  TEXT,
            dest_country    TEXT,
            source_lat      REAL,
            source_lon      REAL,
            dest_lat        REAL,
            dest_lon        REAL,
            tx_hash         TEXT,
            headline        TEXT NOT NULL,
            description     TEXT,
            source_name     TEXT,
            source_url      TEXT,
            entity_id       TEXT REFERENCES entities(id),
            anomaly_score   REAL DEFAULT 0,
            occurred_at     TEXT NOT NULL,
            ingested_at     TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cf_tx_hash
            ON cash_flows(tx_hash) WHERE tx_hash IS NOT NULL;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cf_url
            ON cash_flows(source_url) WHERE source_url IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_cf_type     ON cash_flows(flow_type);
        CREATE INDEX IF NOT EXISTS idx_cf_occurred ON cash_flows(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_cf_amount   ON cash_flows(amount_usd DESC);
        CREATE INDEX IF NOT EXISTS idx_cf_src_cty  ON cash_flows(source_country);
        CREATE INDEX IF NOT EXISTS idx_cf_dst_cty  ON cash_flows(dest_country);
    """)
    # ingestor_runs: performance and health tracking for all scheduler jobs
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS ingestor_runs (
            id                   TEXT PRIMARY KEY,
            ingestor_name        TEXT NOT NULL,
            started_at           TEXT NOT NULL,
            completed_at         TEXT,
            status               TEXT CHECK(status IN ('running','success','failed')),
            events_fetched       INTEGER DEFAULT 0,
            events_inserted      INTEGER DEFAULT 0,
            error_message        TEXT,
            run_duration_seconds REAL,
            api_response_time_ms REAL
        );
        CREATE INDEX IF NOT EXISTS idx_ir_name    ON ingestor_runs(ingestor_name);
        CREATE INDEX IF NOT EXISTS idx_ir_started ON ingestor_runs(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ir_status  ON ingestor_runs(status);
    """)
    conn.commit()

    for col_def in [
        "ALTER TABLE events ADD COLUMN analysis TEXT",
        "ALTER TABLE geo_events ADD COLUMN latitude REAL",
        "ALTER TABLE geo_events ADD COLUMN longitude REAL",
        "ALTER TABLE entities ADD COLUMN last_price REAL",
        "ALTER TABLE entities ADD COLUMN price_updated_at TEXT",
        "ALTER TABLE entities ADD COLUMN ticker TEXT",
        "ALTER TABLE entities ADD COLUMN funding_sources TEXT",
        "ALTER TABLE events ADD COLUMN importance INTEGER DEFAULT 3",
        "ALTER TABLE events ADD COLUMN subtype TEXT",
        "ALTER TABLE entities ADD COLUMN net_worth_updated_at TEXT",
        "ALTER TABLE entities ADD COLUMN net_worth_source TEXT",
        # MFA columns
        "ALTER TABLE users ADD COLUMN totp_secret TEXT",
        "ALTER TABLE users ADD COLUMN mfa_enabled INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN mfa_backup_codes TEXT",
        # Tier tracking columns
        "ALTER TABLE users ADD COLUMN daily_event_count INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN daily_reset_at TEXT",
        # Compliance / legal columns
        "ALTER TABLE users ADD COLUMN disclaimers_accepted_at TEXT",
        "ALTER TABLE users ADD COLUMN tos_version TEXT",
    ]:
        try:
            conn.execute(col_def)
            conn.commit()
        except Exception:
            pass

    for idx_def in [
        "CREATE INDEX IF NOT EXISTS idx_events_importance ON events(importance DESC)",
        "CREATE INDEX IF NOT EXISTS idx_events_entity_date ON events(entity_id, ingested_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_events_enriched ON events(enriched_at) WHERE enriched_at IS NULL",
    ]:
        try:
            conn.execute(idx_def)
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
    # Net worth / market cap values reflect best estimates as of April 2025.
    # Public company figures are approximate; the valuation ingestor overwrites
    # these with live Yahoo Finance market cap on first scheduler run.
    rows = [
        # ---- Public companies (market cap Apr 2025) --------------------------
        ("Apple",              "company",    "Technology",   3.12e12, "Consumer electronics and software"),
        ("Nvidia",             "company",    "Technology",   2.55e12, "AI chips and GPU computing"),
        ("Microsoft",          "company",    "Technology",   2.80e12, "Cloud computing and enterprise software"),
        ("Alphabet",           "company",    "Technology",   1.92e12, "Search, advertising, and cloud"),
        ("Meta",               "company",    "Technology",   1.42e12, "Social media and virtual reality"),
        ("Amazon",             "company",    "E-Commerce",   2.15e12, "E-commerce, cloud, and logistics"),
        ("Tesla",              "company",    "Automotive",   7.50e11, "Electric vehicles and energy storage"),
        ("Berkshire Hathaway", "company",    "Finance",      1.02e12, "Diversified holding conglomerate"),
        ("JPMorgan",           "company",    "Finance",      7.25e11, "Global banking and financial services"),
        ("Goldman Sachs",      "company",    "Finance",      1.85e11, "Investment banking and asset management"),
        ("BlackRock",          "company",    "Finance",      1.40e11, "World's largest asset manager"),
        ("ExxonMobil",         "company",    "Energy",       4.60e11, "Oil and natural gas exploration"),
        ("Lockheed Martin",    "company",    "Defense",      1.05e11, "Aerospace and defense systems"),
        ("Pfizer",             "company",    "Healthcare",   1.35e11, "Pharmaceuticals and vaccines"),
        ("Walmart",            "company",    "Retail",       7.80e11, "Global retail and grocery"),
        ("Visa",               "company",    "Finance",      6.20e11, "Electronic payment network"),
        ("Palantir",           "company",    "Technology",   3.42e11, "Data analytics and AI for government"),
        # ---- Private companies (last known valuation) ------------------------
        ("SpaceX",             "company",    "Aerospace",    3.50e11, "Rocket launches and satellite internet"),
        ("OpenAI",             "company",    "Technology",   3.00e11, "AI research and products"),
        ("Anthropic",          "company",    "Technology",   6.10e10, "AI safety research and Claude AI"),
        # ---- Individuals (Forbes/Bloomberg estimates, Apr 2025) --------------
        ("Elon Musk",          "individual", "Technology",   3.00e11, "CEO of Tesla, SpaceX; owner of X"),
        ("Jeff Bezos",         "individual", "E-Commerce",   2.20e11, "Founder of Amazon"),
        ("Mark Zuckerberg",    "individual", "Technology",   2.10e11, "CEO of Meta"),
        ("Larry Ellison",      "individual", "Technology",   1.85e11, "Co-founder of Oracle"),
        ("Warren Buffett",     "individual", "Finance",      1.55e11, "CEO of Berkshire Hathaway"),
        ("Bill Gates",         "individual", "Technology",   1.30e11, "Co-founder of Microsoft"),
        ("Ken Griffin",        "individual", "Finance",      4.30e10, "Founder of Citadel"),
        ("Ray Dalio",          "individual", "Finance",      1.80e10, "Founder of Bridgewater Associates"),
        ("George Soros",       "individual", "Finance",      7.00e9,  "Founder of Soros Fund Management"),
        ("Carl Icahn",         "individual", "Finance",      6.50e9,  "Activist investor"),
        ("Donald Trump",       "individual", "Government",   6.50e9,  "47th US President; real estate and Truth Social"),
        ("Nancy Pelosi",       "individual", "Government",   2.50e8,  "Former Speaker; active stock trader per STOCK Act disclosures"),
        ("Mitt Romney",        "individual", "Government",   3.00e8,  "Former US Senator, Utah; private equity veteran (Bain Capital)"),
        ("Mitch McConnell",    "individual", "Government",   3.50e7,  "US Senate Minority Leader; Kentucky senator"),
        ("Tommy Tuberville",   "individual", "Government",   1.50e7,  "US Senator, Alabama; known for active stock trading"),
        ("Ro Khanna",          "individual", "Government",   2.50e7,  "US Representative, Silicon Valley; prominent tech policy voice"),
        ("Gavin Newsom",       "individual", "Government",   2.30e7,  "Governor of California; clean energy and tech policy shaper"),
        ("Dan Crenshaw",       "individual", "Government",   4.00e6,  "US Representative, Texas; national security focus"),
        ("Pete Buttigieg",     "individual", "Government",   7.00e6,  "Former US Secretary of Transportation; infrastructure and EV policy"),
        ("Alexandria Ocasio-Cortez", "individual", "Government", 2.0e5, "US Representative, New York; progressive policy advocate"),
        # ---- Government institutions -----------------------------------------
        ("Federal Reserve",    "company",    "Finance",      0.0,     "US central bank -- sets interest rates and monetary policy"),
        ("US Treasury",        "company",    "Government",   0.0,     "US Treasury Department -- issues debt, enforces sanctions"),
        # ---- Defense contractors (market cap Apr 2025) -----------------------
        ("Boeing",             "company",    "Defense",      9.50e10, "Aerospace manufacturer -- commercial jets and defense systems"),
        ("Raytheon",           "company",    "Defense",      1.35e11, "Defense contractor -- missiles, radar, cybersecurity"),
        ("General Dynamics",   "company",    "Defense",      6.80e10, "Defense and IT services -- ships, submarines, Gulfstream jets"),
    ]
    for name, etype, sector, net_worth, desc in rows:
        exists = cur.execute("SELECT 1 FROM entities WHERE name=?", (name,)).fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO entities "
                "(id,name,type,sector,net_worth,description,created_at,"
                " net_worth_source,net_worth_updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    str(uuid.uuid4()), name, etype, sector, net_worth, desc, now,
                    "seed_initial", now,
                ),
            )
        else:
            # Update stale seed values if they haven't been refreshed by the live ingestor
            cur.execute(
                """UPDATE entities
                   SET net_worth=?, net_worth_source=?, net_worth_updated_at=?
                   WHERE name=? AND (net_worth_source='seed_initial' OR net_worth_source IS NULL)""",
                (net_worth, "seed_initial", now, name),
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
         "https://www.anthropic.com/",
         "Anthropic Blog", "2025-01-08"),
    ]
    for name, etype, headline, amount, currency, url, source, date in sample_events:
        entity_id = emap.get(name)
        if not entity_id:
            continue
        exists = cur.execute(
            "SELECT 1 FROM events WHERE source_url=? AND headline=?", (url, headline)
        ).fetchone()
        if not exists:
            cur.execute(
                """INSERT INTO events
                   (id, entity_id, event_type, headline, amount, currency,
                    source_url, source_name, occurred_at, ingested_at, importance)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(__import__("uuid").uuid4()),
                    entity_id,
                    etype,
                    headline,
                    amount,
                    currency,
                    url,
                    source,
                    date + "T00:00:00+00:00",
                    __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                    5,  # high importance for seed events
                ),
            )
    conn.commit()
    conn.close()
    print("[DB] Seed events complete.")


def seed_countries() -> None:
    """
    Seed the countries table with geopolitical metadata for ~65 countries.
    Uses ISO 3166 numeric codes for TopoJSON mapping.
    Only inserts new rows — safe to call on every startup.
    """
    conn = get_connection()
    cur = conn.cursor()
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    # fmt: (iso2, iso3, iso_num, name, continent, gov_type, political_lean,
    #        conflict_status, alliances_json, leader_name, leader_title, key_issues_json)
    countries = [
        # ── Active war / conflict zones ─────────────────────────────────────
        ("UA", "UKR", 804, "Ukraine",         "Europe",   "Republic",         "centre_right",
         "war",             '["UN","OSCE"]',              "Volodymyr Zelensky",   "President",
         '["Russian invasion","energy crisis","reconstruction"]'),
        ("RU", "RUS", 643, "Russia",           "Europe",   "Federal Republic",  "authoritarian",
         "war",             '["CIS","SCO","BRICS"]',      "Vladimir Putin",       "President",
         '["Ukraine war","sanctions","economy"]'),
        ("IL", "ISR", 376, "Israel",           "Asia",     "Parliamentary Democracy","centre_right",
         "war",             '["Western allies"]',         "Isaac Herzog",         "President",
         '["Gaza conflict","West Bank","Iran tensions"]'),
        ("PS", "PSE", 275, "Palestine",        "Asia",     "Palestinian Authority","left",
         "war",             '["Arab League"]',            "Mahmoud Abbas",        "President (PA)",
         '["Gaza war","statehood","humanitarian crisis"]'),
        ("SD", "SDN", 729, "Sudan",            "Africa",   "Military Junta",    "authoritarian",
         "war",             '["Arab League"]',            "Abdel Fattah al-Burhan","Commander",
         '["Civil war","RSF conflict","famine","Darfur"]'),
        ("MM", "MMR", 104, "Myanmar",          "Asia",     "Military Junta",    "authoritarian",
         "war",             '["ASEAN"]',                  "Min Aung Hlaing",      "Commander-in-Chief",
         '["Civil war","coup","ethnic conflict","sanctions"]'),
        ("YE", "YEM", 887, "Yemen",            "Asia",     "Transitional",      "unknown",
         "war",             '["Arab League"]',            "Rashad al-Alimi",      "Presidential Council Chair",
         '["Houthi conflict","Red Sea attacks","humanitarian crisis"]'),
        ("ET", "ETH", 231, "Ethiopia",         "Africa",   "Federal Republic",  "left",
         "active_conflict", '["AU","IGAD"]',              "Abiy Ahmed",           "Prime Minister",
         '["Amhara conflict","Tigray aftermath","economy"]'),
        ("CD", "COD", 180, "DR Congo",         "Africa",   "Republic",          "centre",
         "active_conflict", '["AU","SADC"]',              "Félix Tshisekedi",     "President",
         '["M23 rebels","Rwanda tensions","mineral wealth"]'),
        ("LY", "LBY", 434, "Libya",            "Africa",   "Divided Government", "unknown",
         "active_conflict", '["Arab League","UN"]',       "Mohamed al-Menfi",     "Presidential Council Head",
         '["East-West split","Haftar","oil revenues","migration"]'),
        ("ML", "MLI", 466, "Mali",             "Africa",   "Military Junta",    "authoritarian",
         "active_conflict", '["ECOWAS suspended"]',       "Assimi Goïta",         "Transitional President",
         '["Jihadist insurgency","Wagner group","French expulsion"]'),
        ("HT", "HTI", 332, "Haiti",            "Americas", "Transitional",      "unknown",
         "active_conflict", '["CARICOM"]',                "Garry Conille",        "Prime Minister",
         '["Gang violence","political vacuum","humanitarian crisis"]'),
        # ── High tension ────────────────────────────────────────────────────
        ("IR", "IRN", 364, "Iran",             "Asia",     "Islamic Republic",  "theocratic",
         "tension",         '["SCO","BRICS"]',            "Masoud Pezeshkian",    "President",
         '["Nuclear program","IAEA","US sanctions","proxy militias"]'),
        ("KP", "PRK", 408, "North Korea",      "Asia",     "Single-party State", "far_left",
         "tension",         '[]',                         "Kim Jong Un",          "Supreme Leader",
         '["Nuclear weapons","missile tests","sanctions","China relations"]'),
        ("CN", "CHN", 156, "China",            "Asia",     "Single-party State", "authoritarian",
         "tension",         '["SCO","BRICS","RCEP"]',     "Xi Jinping",           "President",
         '["Taiwan Strait","South China Sea","trade war","Xinjiang"]'),
        ("TW", "TWN", 158, "Taiwan",           "Asia",     "Democracy",         "centre_right",
         "tension",         '["informal Western alliances"]',"Lai Ching-te",      "President",
         '["China threat","semiconductor dominance","US arms sales"]'),
        ("VE", "VEN", 862, "Venezuela",        "Americas", "Presidential Republic","far_left",
         "tension",         '["ALBA"]',                   "Nicolás Maduro",       "President",
         '["US sanctions","election dispute","economic collapse","migration"]'),
        ("SY", "SYR", 760, "Syria",            "Asia",     "Transitional",      "unknown",
         "tension",         '["Arab League (readmitted)"]',"Ahmad al-Sharaa",     "Leader (HTS)",
         '["Post-Assad transition","reconstruction","sanctions relief"]'),
        ("AF", "AFG", 4,   "Afghanistan",      "Asia",     "Emirate",           "theocratic",
         "tension",         '[]',                         "Hibatullah Akhundzada","Supreme Leader",
         '["Taliban rule","humanitarian crisis","women rights","sanctions"]'),
        ("PK", "PAK", 586, "Pakistan",         "Asia",     "Federal Republic",  "right",
         "tension",         '["SCO","OIC"]',              "Asif Ali Zardari",     "President",
         '["IMF bailout","India tensions","Khan imprisonment","floods"]'),
        ("IN", "IND", 356, "India",            "Asia",     "Federal Republic",  "right",
         "tension",         '["BRICS","SCO","Quad"]',     "Narendra Modi",        "Prime Minister",
         '["Pakistan border","China border","religious tensions","tech growth"]'),
        ("KR", "KOR", 410, "South Korea",      "Asia",     "Presidential Republic","centre_right",
         "tension",         '["US alliance","G20"]',      "Han Duck-soo",         "Acting President",
         '["North Korea threat","martial law crisis","US alliance","semiconductors"]'),
        ("NG", "NGA", 566, "Nigeria",          "Africa",   "Federal Republic",  "centre",
         "tension",         '["AU","ECOWAS"]',            "Bola Tinubu",          "President",
         '["Boko Haram","oil economy","naira devaluation","banditry"]'),
        ("MX", "MEX", 484, "Mexico",           "Americas", "Federal Republic",  "left",
         "tension",         '["USMCA","G20"]',            "Claudia Sheinbaum",    "President",
         '["Cartel violence","USMCA trade","US relations","judicial reform"]'),
        # ── Stable but geopolitically significant ───────────────────────────
        ("US", "USA", 840, "United States",    "Americas", "Federal Republic",  "centre_right",
         "stable",          '["NATO","G7","Five Eyes","Quad"]',"Donald Trump",    "President",
         '["Tariff policy","Ukraine support","China rivalry","border"]'),
        ("GB", "GBR", 826, "United Kingdom",   "Europe",   "Constitutional Monarchy","centre_right",
         "stable",          '["NATO","G7","Five Eyes","AUKUS"]',"Keir Starmer",  "Prime Minister",
         '["Post-Brexit trade","Ukraine support","NHS","Scotland"]'),
        ("DE", "DEU", 276, "Germany",          "Europe",   "Federal Republic",  "centre_right",
         "stable",          '["NATO","G7","EU"]',         "Friedrich Merz",       "Chancellor",
         '["Energy transition","Ukraine aid","fiscal policy","AfD rise"]'),
        ("FR", "FRA", 250, "France",           "Europe",   "Semi-presidential", "centre",
         "stable",          '["NATO","G7","EU","UN P5"]', "Emmanuel Macron",      "President",
         '["Political fragmentation","Ukraine policy","Africa policy","pension reform"]'),
        ("JP", "JPN", 392, "Japan",            "Asia",     "Constitutional Monarchy","centre_right",
         "stable",          '["G7","Quad","US alliance"]',"Shigeru Ishiba",       "Prime Minister",
         '["Defense buildup","China rivalry","semiconductor policy","aging population"]'),
        ("CA", "CAN", 124, "Canada",           "Americas", "Constitutional Monarchy","centre_left",
         "stable",          '["NATO","G7","Five Eyes","USMCA"]',"Mark Carney",   "Prime Minister",
         '["US tariffs","Quebec separatism","energy policy","immigration"]'),
        ("AU", "AUS", 36,  "Australia",        "Oceania",  "Constitutional Monarchy","centre_left",
         "stable",          '["Five Eyes","AUKUS","Quad"]',"Anthony Albanese",    "Prime Minister",
         '["China relations","AUKUS submarine deal","climate policy"]'),
        ("SA", "SAU", 682, "Saudi Arabia",     "Asia",     "Absolute Monarchy", "authoritarian",
         "stable",          '["G20","Arab League","OPEC+"]',"Mohammed bin Salman","Crown Prince & PM",
         '["OPEC+ oil cuts","Vision 2030","Israel normalization","Yemen"]'),
        ("TR", "TUR", 792, "Turkey",           "Europe",   "Presidential Republic","right",
         "stable",          '["NATO","G20"]',             "Recep Tayyip Erdoğan", "President",
         '["NATO tensions","Syria","inflation","Kurdish issue","mediation role"]'),
        ("BR", "BRA", 76,  "Brazil",           "Americas", "Federal Republic",  "left",
         "stable",          '["BRICS","G20","Mercosur"]', "Luiz Inácio Lula da Silva","President",
         '["Amazon deforestation","economic reform","BRICS leadership","China trade"]'),
        ("ZA", "ZAF", 710, "South Africa",     "Africa",   "Republic",          "centre_left",
         "stable",          '["BRICS","AU","G20"]',       "Cyril Ramaphosa",      "President",
         '["Load shedding","ANC coalition","crime","China-US balancing"]'),
        ("EG", "EGY", 818, "Egypt",            "Africa",   "Presidential Republic","authoritarian",
         "stable",          '["Arab League","AU"]',       "Abdel Fattah el-Sisi", "President",
         '["Gaza mediation","IMF program","Suez Canal","Ethiopia dam dispute"]'),
        ("ID", "IDN", 360, "Indonesia",        "Asia",     "Presidential Republic","centre",
         "stable",          '["ASEAN","G20"]',            "Prabowo Subianto",     "President",
         '["ASEAN chair","South China Sea","nickel dominance","US-China balancing"]'),
        ("IT", "ITA", 380, "Italy",            "Europe",   "Parliamentary Republic","right",
         "stable",          '["NATO","G7","EU"]',         "Giorgia Meloni",        "Prime Minister",
         '["Migration","EU relations","Ukraine support","economy"]'),
        ("ES", "ESP", 724, "Spain",            "Europe",   "Constitutional Monarchy","centre_left",
         "stable",          '["NATO","EU"]',              "Pedro Sánchez",         "Prime Minister",
         '["Catalonia","immigration","economy","Ukraine aid"]'),
        ("PL", "POL", 616, "Poland",           "Europe",   "Parliamentary Republic","centre_right",
         "stable",          '["NATO","EU"]',              "Donald Tusk",           "Prime Minister",
         '["Ukraine border","defense buildup","rule of law","Russia threat"]'),
        ("UA", "UKR", 804, "Ukraine",         "Europe",   "Republic",         "centre_right",
         "war",             '["UN","OSCE"]',              "Volodymyr Zelensky",   "President",
         '["Russian invasion","energy crisis","reconstruction"]'),
        ("NL", "NLD", 528, "Netherlands",      "Europe",   "Constitutional Monarchy","centre_right",
         "stable",          '["NATO","EU"]',              "Dick Schoof",           "Prime Minister",
         '["ASML semiconductor dominance","Ukraine aid","migration","coalition politics"]'),
        ("SE", "SWE", 752, "Sweden",           "Europe",   "Constitutional Monarchy","centre_right",
         "stable",          '["NATO","EU"]',              "Ulf Kristersson",       "Prime Minister",
         '["New NATO membership","Ukraine aid","migration","defense spending"]'),
        ("CH", "CHE", 756, "Switzerland",      "Europe",   "Federal Republic",  "centre",
         "stable",          '[]',                         "Karin Keller-Sutter",   "Federal Council President",
         '["Neutrality debate","banking sector","EU relations","sanctions on Russia"]'),
        ("NO", "NOR", 578, "Norway",           "Europe",   "Constitutional Monarchy","centre_left",
         "stable",          '["NATO"]',                   "Jonas Gahr Støre",      "Prime Minister",
         '["Oil fund ($1.7T sovereign wealth)","Ukraine aid","Arctic security"]'),
        ("UA", "UKR", 804, "Ukraine",         "Europe",   "Republic",         "centre_right",
         "war",             '["UN","OSCE"]',              "Volodymyr Zelensky",   "President",
         '["Russian invasion","energy crisis","reconstruction"]'),
        ("GR", "GRC", 300, "Greece",           "Europe",   "Parliamentary Republic","centre_right",
         "stable",          '["NATO","EU"]',              "Kyriakos Mitsotakis",   "Prime Minister",
         '["Turkey tensions","migration","debt recovery","defense spending"]'),
        ("NG", "NGA", 566, "Nigeria",          "Africa",   "Federal Republic",  "centre",
         "tension",         '["AU","ECOWAS"]',            "Bola Tinubu",           "President",
         '["Boko Haram","oil economy","naira devaluation","banditry"]'),
        ("AR", "ARG", 32,  "Argentina",        "Americas", "Federal Republic",  "right",
         "stable",          '["G20","Mercosur"]',         "Javier Milei",          "President",
         '["Dollarization","IMF debt","austerity","Falklands"]'),
        ("CL", "CHL", 152, "Chile",            "Americas", "Presidential Republic","centre_left",
         "stable",          '["Pacific Alliance"]',       "Gabriel Boric",         "President",
         '["Copper dominance","lithium nationalization","pension reform","Mapuche"]'),
        ("CO", "COL", 170, "Colombia",         "Americas", "Presidential Republic","centre_left",
         "stable",          '["UN","OAS"]',               "Gustavo Petro",         "President",
         '["FARC remnants","drug trade","Venezuela relations","US relations"]'),
        ("UA", "UKR", 804, "Ukraine",         "Europe",   "Republic",         "centre_right",
         "war",             '["UN","OSCE"]',              "Volodymyr Zelensky",   "President",
         '["Russian invasion","energy crisis","reconstruction"]'),
        ("MA", "MAR", 504, "Morocco",          "Africa",   "Constitutional Monarchy","centre",
         "stable",          '["Arab League","AU observer"]',"Mohammed VI",         "King",
         '["Western Sahara","EU migration deal","normalization with Israel"]'),
        ("KE", "KEN", 404, "Kenya",            "Africa",   "Presidential Republic","centre",
         "stable",          '["AU","EAC"]',               "William Ruto",          "President",
         '["East Africa hub","IMF austerity","Somalia peacekeeping","debt"]'),
        ("TH", "THA", 764, "Thailand",         "Asia",     "Constitutional Monarchy","centre",
         "stable",          '["ASEAN"]',                  "Paetongtarn Shinawatra","Prime Minister",
         '["Tourism economy","coup history","China-US balancing","political reform"]'),
        ("VN", "VNM", 704, "Vietnam",          "Asia",     "Single-party State", "far_left",
         "stable",          '["ASEAN"]',                  "To Lam",                "General Secretary",
         '["South China Sea disputes","US-Vietnam trade","FDI growth","bamboo diplomacy"]'),
        ("PH", "PHL", 608, "Philippines",      "Asia",     "Presidential Republic","right",
         "stable",          '["ASEAN","US alliance"]',    "Ferdinand Marcos Jr.",  "President",
         '["South China Sea standoffs","US base expansion","Duterte legacy","China relations"]'),
        ("MY", "MYS", 458, "Malaysia",         "Asia",     "Constitutional Monarchy","centre",
         "stable",          '["ASEAN","OIC"]',            "Anwar Ibrahim",         "Prime Minister",
         '["ASEAN chair 2025","China-US balancing","digital economy","ethnic politics"]'),
        ("AE", "ARE", 784, "UAE",              "Asia",     "Absolute Monarchy", "authoritarian",
         "stable",          '["Arab League","OPEC+"]',    "Mohamed bin Zayed",     "President",
         '["Finance hub","normalization with Israel","Iran relations","AI investment"]'),
        ("QA", "QAT", 634, "Qatar",            "Asia",     "Absolute Monarchy", "authoritarian",
         "stable",          '["Arab League","OPEC+"]',    "Tamim bin Hamad Al Thani","Emir",
         '["Gaza mediation","LNG exports","US base","Hamas diplomacy"]'),
        ("IL", "ISR", 376, "Israel",           "Asia",     "Parliamentary Democracy","centre_right",
         "war",             '["Western allies"]',         "Isaac Herzog",          "President",
         '["Gaza conflict","West Bank","Iran tensions"]'),
    ]

    # Deduplicate by iso2 (take first occurrence)
    seen_iso2 = set()
    unique_countries = []
    for c in countries:
        if c[0] not in seen_iso2:
            seen_iso2.add(c[0])
            unique_countries.append(c)

    for row in unique_countries:
        (iso2, iso3, iso_num, name, continent, gov_type, political_lean,
         conflict_status, alliances, leader_name, leader_title, key_issues) = row
        exists = cur.execute("SELECT 1 FROM countries WHERE iso2=?", (iso2,)).fetchone()
        if not exists:
            cur.execute(
                """INSERT INTO countries
                   (iso2, iso3, iso_num, name, continent, gov_type, political_lean,
                    conflict_status, alliances, leader_name, leader_title, key_issues, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (iso2, iso3, iso_num, name, continent, gov_type, political_lean,
                 conflict_status, alliances, leader_name, leader_title, key_issues, now),
            )
    conn.commit()
    conn.close()
    print(f"[DB] seed_countries complete — {len(unique_countries)} countries seeded.")
