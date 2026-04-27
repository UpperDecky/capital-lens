"""Load S&P 500 and additional companies into the entities table."""
import uuid
import re
from datetime import datetime, timezone
import httpx
from backend.database import get_connection


ADDITIONAL_COMPANIES = [
    ('NVDA',  'NVIDIA Corporation',   'Technology'),
    ('TSLA',  'Tesla Inc',            'Automotive'),
    ('META',  'Meta Platforms',       'Technology'),
    ('AMZN',  'Amazon.com Inc',       'E-Commerce'),
    ('GOOG',  'Alphabet Inc',         'Technology'),
    ('MSFT',  'Microsoft Corporation','Technology'),
    ('AAPL',  'Apple Inc',            'Technology'),
    ('NFLX',  'Netflix',              'Technology'),
    ('AMD',   'Advanced Micro Devices','Technology'),
    ('INTC',  'Intel Corporation',    'Technology'),
    ('PYPL',  'PayPal Holdings',      'Finance'),
    ('SQ',    'Block Inc',            'Finance'),
    ('COIN',  'Coinbase Global',      'Finance'),
    ('RBLX',  'Roblox Corporation',   'Technology'),
    ('SNAP',  'Snap Inc',             'Technology'),
    ('PINS',  'Pinterest',            'Technology'),
    ('TWTR',  'Twitter X Corp',       'Technology'),
    ('LYFT',  'Lyft Inc',             'Technology'),
    ('UBER',  'Uber Technologies',    'Technology'),
    ('ABNB',  'Airbnb Inc',           'Technology'),
    ('DASH',  'DoorDash Inc',         'E-Commerce'),
    ('RIVN',  'Rivian Automotive',    'Automotive'),
    ('LCID',  'Lucid Group',          'Automotive'),
    ('NIO',   'NIO Inc',              'Automotive'),
    ('BIDU',  'Baidu Inc',            'Technology'),
    ('BABA',  'Alibaba Group',        'E-Commerce'),
    ('JD',    'JD.com Inc',           'E-Commerce'),
    ('PDD',   'PDD Holdings',         'E-Commerce'),
    ('SNOW',  'Snowflake Inc',        'Technology'),
    ('DDOG',  'Datadog Inc',          'Technology'),
    ('NET',   'Cloudflare Inc',       'Technology'),
    ('ZS',    'Zscaler Inc',          'Technology'),
    ('CRWD',  'CrowdStrike Holdings', 'Technology'),
    ('S',     'SentinelOne Inc',      'Technology'),
    ('OKTA',  'Okta Inc',             'Technology'),
    ('TWLO',  'Twilio Inc',           'Technology'),
    ('MDB',   'MongoDB Inc',          'Technology'),
    ('ESTC',  'Elastic NV',           'Technology'),
    ('HCP',   'HashiCorp',            'Technology'),
    ('GTLB',  'GitLab Inc',           'Technology'),
    ('PATH',  'UiPath Inc',           'Technology'),
    ('AI',    'C3.ai Inc',            'Technology'),
    ('BBAI',  'BigBear.ai Holdings',  'Technology'),
    ('SOUN',  'SoundHound AI',        'Technology'),
    ('PLTR',  'Palantir Technologies','Technology'),
    ('IONQ',  'IonQ Inc',             'Technology'),
    ('RGTI',  'Rigetti Computing',    'Technology'),
    ('QBTS',  'D-Wave Quantum',       'Technology'),
    ('QUBT',  'Quantum Computing',    'Technology'),
    ('SMCI',  'Super Micro Computer', 'Technology'),
    ('ARM',   'ARM Holdings',         'Technology'),
    ('AVGO',  'Broadcom Inc',         'Technology'),
    ('QCOM',  'QUALCOMM Inc',         'Technology'),
    ('TXN',   'Texas Instruments',    'Technology'),
    ('MU',    'Micron Technology',    'Technology'),
    ('WDC',   'Western Digital',      'Technology'),
    ('STX',   'Seagate Technology',   'Technology'),
    ('ORCL',  'Oracle Corporation',   'Technology'),
    ('SAP',   'SAP SE',               'Technology'),
    ('CRM',   'Salesforce Inc',       'Technology'),
    ('NOW',   'ServiceNow Inc',       'Technology'),
    ('WDAY',  'Workday Inc',          'Technology'),
    ('ADBE',  'Adobe Inc',            'Technology'),
    ('INTU',  'Intuit Inc',           'Technology'),
    ('ROP',   'Roper Technologies',   'Technology'),
    ('ANSS',  'ANSYS Inc',            'Technology'),
    ('CDNS',  'Cadence Design Systems','Technology'),
    ('SNPS',  'Synopsys Inc',         'Technology'),
    ('GS',    'Goldman Sachs Group',  'Finance'),
    ('MS',    'Morgan Stanley',       'Finance'),
    ('BAC',   'Bank of America',      'Finance'),
    ('C',     'Citigroup Inc',        'Finance'),
    ('WFC',   'Wells Fargo',          'Finance'),
    ('AXP',   'American Express',     'Finance'),
    ('MA',    'Mastercard Inc',       'Finance'),
    ('V',     'Visa Inc',             'Finance'),
    ('SCHW',  'Charles Schwab',       'Finance'),
    ('BLK',   'BlackRock Inc',        'Finance'),
    ('BX',    'Blackstone Inc',       'Finance'),
    ('KKR',   'KKR & Co Inc',         'Finance'),
    ('APO',   'Apollo Global Mgmt',   'Finance'),
    ('CG',    'Carlyle Group',        'Finance'),
    ('ARES',  'Ares Management',      'Finance'),
]


def load_additional_companies(conn) -> int:
    """Insert hand-curated growth/tech companies. Skip duplicates."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for ticker, name, sector in ADDITIONAL_COMPANIES:
        existing = conn.execute(
            "SELECT id FROM entities WHERE name=?", (name,)
        ).fetchone()
        if existing:
            # Update ticker if missing
            conn.execute(
                "UPDATE entities SET ticker=? WHERE name=? AND (ticker IS NULL OR ticker='')",
                (ticker, name),
            )
            continue
        try:
            conn.execute(
                """INSERT INTO entities
                   (id, name, type, sector, description, ticker, created_at)
                   VALUES (?, ?, 'company', ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    name,
                    sector,
                    f"Ticker: {ticker}",
                    ticker,
                    now,
                ),
            )
            inserted += 1
        except Exception as exc:
            print(f"[EntityLoader] Error inserting {name}: {exc}")
    conn.commit()
    return inserted


def load_sp500_from_wikipedia(conn) -> int:
    """Scrape S&P 500 list from Wikipedia and insert new entities."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        resp = httpx.get(url, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[EntityLoader] Wikipedia fetch failed: {exc}")
        return 0

    # Parse ticker/name/sector from the first wiki table
    row_pattern = re.compile(
        r'<tr[^>]*>.*?<td[^>]*><a[^>]*href="[^"]*"[^>]*>([A-Z]{1,5})</a></td>'
        r'.*?<td[^>]*><a[^>]*>([^<]+)</a></td>'
        r'.*?<td[^>]*>([^<\n]+)</td>',
        re.DOTALL,
    )
    matches = row_pattern.findall(resp.text)

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for ticker, company_name, sector in matches:
        ticker = ticker.strip()
        company_name = company_name.strip()
        sector = sector.strip().split('\n')[0].strip()
        if not company_name or not ticker:
            continue

        existing = conn.execute(
            "SELECT id FROM entities WHERE name=?", (company_name,)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE entities SET ticker=? WHERE name=? AND (ticker IS NULL OR ticker='')",
                (ticker, company_name),
            )
            continue

        try:
            conn.execute(
                """INSERT INTO entities
                   (id, name, type, sector, description, ticker, created_at)
                   VALUES (?, ?, 'company', ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    company_name,
                    sector if sector else 'Other',
                    f"S&P 500 company. Ticker: {ticker}",
                    ticker,
                    now,
                ),
            )
            inserted += 1
        except Exception as exc:
            print(f"[EntityLoader] Insert error {company_name}: {exc}")

    conn.commit()
    return inserted


def load_all_entities() -> dict:
    """Run all entity loaders. Called from admin endpoint or startup."""
    conn = get_connection()
    try:
        additional = load_additional_companies(conn)
        sp500 = load_sp500_from_wikipedia(conn)
        total = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        return {
            'additional_inserted': additional,
            'sp500_inserted': sp500,
            'total_entities': total,
        }
    finally:
        conn.close()
