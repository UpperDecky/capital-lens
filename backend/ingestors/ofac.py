"""
OFAC sanctions and asset seizure ingestor.

Polls the US Treasury OFAC recent-actions RSS feed and maps each
designation/seizure to a cash_flow record with geographic routing
(source: US -> dest: sanctioned entity country).

OFAC RSS: https://home.treasury.gov/system/files/126/ofac_actions_feed.xml
No API key required -- public government data.
"""
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

# ---- Country detection from headline text -----------------------------------

# Maps country/group keywords to ISO2 codes (ordered by specificity)
COUNTRY_KEYWORDS: list[tuple[str, str]] = [
    ("north korea",    "KP"),
    ("dprk",           "KP"),
    ("iran",           "IR"),
    ("iranian",        "IR"),
    ("russia",         "RU"),
    ("russian",        "RU"),
    ("china",          "CN"),
    ("chinese",        "CN"),
    ("venezuela",      "VE"),
    ("venezuelan",     "VE"),
    ("syria",          "SY"),
    ("syrian",         "SY"),
    ("cuba",           "CU"),
    ("myanmar",        "MM"),
    ("belarus",        "BY"),
    ("belarusian",     "BY"),
    ("sudan",          "SD"),
    ("sudanese",       "SD"),
    ("somalia",        "SO"),
    ("somali",         "SO"),
    ("yemen",          "YE"),
    ("houthi",         "YE"),
    ("mali",           "ML"),
    ("ukraine",        "UA"),
    ("ukrainian",      "UA"),
    ("afghanistan",    "AF"),
    ("afghan",         "AF"),
    ("iraq",           "IQ"),
    ("iraqi",          "IQ"),
    ("lebanon",        "LB"),
    ("hezbollah",      "LB"),
    ("hamas",          "PS"),
    ("palestine",      "PS"),
    ("liberia",        "LR"),
    ("zimbabwe",       "ZW"),
    ("turkey",         "TR"),
    ("turkish",        "TR"),
    ("colombia",       "CO"),
    ("mexican",        "MX"),
    ("mexico",         "MX"),
    ("haiti",          "HT"),
    ("serbian",        "RS"),
    ("serbia",         "RS"),
    ("cybercrime",     "RU"),   # most designated cybercriminals are attributed RU
    ("ransomware",     "RU"),
]

COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "US": (37.09,  -95.71),
    "KP": (40.34,  127.51),
    "IR": (32.43,   53.69),
    "RU": (61.52,  105.32),
    "CN": (35.86,  104.20),
    "VE": ( 6.42,  -66.59),
    "SY": (34.80,   38.99),
    "CU": (21.52,  -77.78),
    "MM": (16.87,   96.19),
    "BY": (53.71,   27.95),
    "SD": (12.86,   30.22),
    "SO": ( 5.15,   46.20),
    "YE": (15.55,   48.52),
    "ML": (17.57,   -3.99),
    "UA": (48.38,   31.17),
    "AF": (33.94,   67.71),
    "IQ": (33.22,   43.68),
    "LB": (33.85,   35.86),
    "PS": (31.95,   35.30),
    "LR": ( 6.43,   -9.43),
    "ZW": (-19.02,  29.15),
    "TR": (38.96,   35.24),
    "CO": ( 4.57,  -74.30),
    "MX": (23.63,  -102.55),
    "HT": (18.97,  -72.29),
    "RS": (44.02,   21.01),
    "XX": ( 0.00,    0.00),
}

# Try multiple Treasury / OFAC RSS endpoints (they move periodically)
OFAC_RSS_URLS = [
    "https://home.treasury.gov/system/files/126/ofac_actions_feed.xml",
    "https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/rss.xml",
    "https://home.treasury.gov/news/press-releases/rss.xml",
]

_HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept":     "application/rss+xml, application/xml, text/xml",
}


def _detect_country(text: str) -> str:
    """Return ISO2 for the first country keyword found in text, else XX."""
    lower = text.lower()
    for keyword, iso2 in COUNTRY_KEYWORDS:
        if keyword in lower:
            return iso2
    return "XX"


def _coords(iso2: str) -> tuple[float, float]:
    return COUNTRY_COORDS.get(iso2, COUNTRY_COORDS["XX"])


def _parse_date(date_str: str) -> str:
    """Parse RSS date string to UTC ISO string. Falls back to now."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _classify_flow_type(title: str) -> str:
    """Return 'seizure' or 'ofac_sanction' based on title keywords."""
    lower = title.lower()
    if any(w in lower for w in ("seiz", "forfeit", "frozen", "freeze", "block")):
        return "seizure"
    return "ofac_sanction"


def fetch_ofac_actions(db_conn: Any, entity_map: dict | None = None) -> int:
    """
    Fetch latest OFAC actions from Treasury RSS and store as cash_flows.
    Returns count of new records inserted.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    root = None
    for url in OFAC_RSS_URLS:
        try:
            resp = httpx.get(url, headers=_HEADERS, timeout=20, follow_redirects=True)
            if resp.status_code != 200:
                continue
            # Skip HTML responses (some URLs redirect to web pages)
            ct = resp.headers.get("content-type", "")
            if "html" in ct:
                continue
            content = resp.content
            root = ET.fromstring(content)
            break
        except Exception:
            continue

    if root is None:
        print("[CashFlow/OFAC] All RSS endpoints unavailable or returned HTML -- skipping")
        return 0

    # RSS <channel><item>...</item></channel>
    channel = root.find("channel")
    if channel is None:
        return 0

    items = channel.findall("item")
    for item in items[:20]:
        title       = (item.findtext("title") or "").strip()
        link        = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        pub_date    = item.findtext("pubDate") or ""

        if not title or not link:
            continue

        full_text    = f"{title} {description}"
        dest_iso     = _detect_country(full_text)
        flow_type    = _classify_flow_type(title)
        occurred_at  = _parse_date(pub_date)

        src_lat, src_lon = _coords("US")
        dst_lat, dst_lon = _coords(dest_iso)

        # Amount extraction -- OFAC sometimes mentions dollar figures
        amount_usd: float | None = None
        match = re.search(r"\$([0-9,.]+)\s*(billion|million|B|M)\b", full_text, re.IGNORECASE)
        if match:
            num   = float(match.group(1).replace(",", ""))
            unit  = match.group(2).lower()
            amount_usd = num * 1e9 if unit in ("billion", "b") else num * 1e6

        flow_id  = str(uuid.uuid4())
        headline = title[:300]

        try:
            db_conn.execute(
                """INSERT OR IGNORE INTO cash_flows
                   (id, flow_type, asset, amount_usd,
                    source_label, dest_label,
                    source_country, dest_country,
                    source_lat, source_lon, dest_lat, dest_lon,
                    headline, description, source_name, source_url,
                    occurred_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (flow_id, flow_type, "USD", amount_usd,
                 "US Treasury", "Sanctioned Entity",
                 "US", dest_iso,
                 src_lat, src_lon, dst_lat, dst_lon,
                 headline, description[:500] if description else None,
                 "OFAC / US Treasury", link,
                 occurred_at, now),
            )
            inserted += db_conn.execute("SELECT changes()").fetchone()[0]
        except Exception as exc:
            print(f"[CashFlow/OFAC] DB error: {exc}")

    if inserted:
        db_conn.commit()
        print(f"[CashFlow/OFAC] Stored {inserted} new OFAC actions")
    return inserted
