"""
GDELT (Global Database of Events, Language, and Tone) ingestor.
Free, no API key required. Pulls geopolitical news events for tracked countries.
API docs: https://blog.gdeltproject.org/gdelt-2-0-our-global-similarity-graph-in-an-api/
"""
import uuid
from datetime import datetime, timezone
from typing import Any
import httpx

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept": "application/json",
}

# Countries to monitor with their search terms and ISO2 codes
# Focused on active conflicts and high-tension regions
MONITORED_COUNTRIES: list[tuple[str, str, str]] = [
    ("UA", "Ukraine",        "Ukraine war conflict Zelensky"),
    ("RU", "Russia",         "Russia Putin Ukraine sanctions"),
    ("IL", "Israel",         "Israel Gaza war Hamas IDF"),
    ("PS", "Palestine",      "Gaza Palestine ceasefire Hamas"),
    ("IR", "Iran",           "Iran nuclear sanctions IRGC"),
    ("KP", "North Korea",    "North Korea missile Kim Jong Un"),
    ("CN", "China",          "China Taiwan South China Sea Xi Jinping"),
    ("TW", "Taiwan",         "Taiwan China invasion Strait"),
    ("SD", "Sudan",          "Sudan war RSF SAF Darfur"),
    ("MM", "Myanmar",        "Myanmar junta civil war coup"),
    ("YE", "Yemen",          "Yemen Houthi Red Sea shipping"),
    ("SY", "Syria",          "Syria transition reconstruction Assad"),
    ("VE", "Venezuela",      "Venezuela Maduro sanctions opposition"),
    ("HT", "Haiti",          "Haiti gang violence transition"),
    ("AF", "Afghanistan",    "Afghanistan Taliban humanitarian"),
    ("CD", "Congo DRC",      "Congo DRC M23 Rwanda conflict minerals"),
    ("ET", "Ethiopia",       "Ethiopia Amhara Tigray conflict"),
    ("LY", "Libya",          "Libya civil war Haftar GNU"),
    ("ML", "Mali",           "Mali junta Wagner jihadist"),
    ("PK", "Pakistan",       "Pakistan India tensions IMF economy"),
]


def fetch_gdelt_events(db_conn: Any) -> int:
    """
    Pull recent geopolitical news from GDELT for monitored countries.
    Stores new articles in geo_events table.
    Returns count of new events inserted.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for iso2, country_name, query in MONITORED_COUNTRIES:
        try:
            with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
                resp = client.get(
                    GDELT_DOC_URL,
                    params={
                        "query":       query,
                        "mode":        "ArtList",
                        "maxrecords":  10,
                        "format":      "json",
                        "sourcelang":  "english",
                        "sort":        "DateDesc",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            print(f"[GDELT] Error fetching {country_name}: {exc}")
            continue

        articles = data.get("articles", [])
        for art in articles:
            url     = art.get("url", "")
            title   = (art.get("title") or "").strip()
            source  = art.get("domain", "")
            seendate = art.get("seendate", "")   # format: 20250418T123456Z
            tone    = art.get("tone", 0.0)

            if not title or not url:
                continue

            # Parse GDELT's seendate format → ISO
            try:
                occurred_at = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").isoformat() + "Z"
            except Exception:
                occurred_at = now

            # Skip duplicates by URL
            exists = db_conn.execute(
                "SELECT 1 FROM geo_events WHERE url = ?", (url,)
            ).fetchone()
            if exists:
                continue

            db_conn.execute(
                """INSERT INTO geo_events
                   (id, iso2, headline, url, source, occurred_at, tone, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    iso2,
                    title,
                    url,
                    source,
                    occurred_at,
                    float(tone) if tone else 0.0,
                    now,
                ),
            )
            inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[GDELT] ✓ Inserted {inserted} new geo events")
    else:
        print("[GDELT] No new geo events")
    return inserted
