"""SEC EDGAR ingestor — fetches recent filings for seeded companies."""
import uuid
import asyncio
import time
from datetime import datetime, timezone
from typing import Any
import httpx

EDGAR_BASE = "https://data.sec.gov/submissions"

HEADERS = {
    "User-Agent": "CapitalLens research@capitallens.dev",
    "Accept":     "application/json",
}

# CIK numbers for seeded companies (zero-padded to 10 digits)
ENTITY_CIK_MAP: dict[str, str] = {
    "Apple":              "0000320193",
    "Nvidia":             "0001045810",
    "Microsoft":          "0000789019",
    "Alphabet":           "0001652044",
    "Meta":               "0001326801",
    "Amazon":             "0001018724",
    "Tesla":              "0001318605",
    "Berkshire Hathaway": "0001067983",
    "JPMorgan":           "0000019617",
    "Goldman Sachs":      "0000886982",
    "BlackRock":          "0001364742",
    "ExxonMobil":         "0000034088",
    "Lockheed Martin":    "0000936468",
    "Pfizer":             "0000078003",
    "Walmart":            "0000104169",
    "Visa":               "0001403161",
    "Palantir":           "0001321655",
}

FORM_TYPE_MAP: dict[str, str] = {
    "4":       "insider_sale",
    "8-K":     "filing",
    "10-K":    "filing",
    "10-Q":    "filing",
    "SC 13G":  "filing",
    "SC 13D":  "filing",
    "13F-HR":  "filing",
    "S-1":     "filing",
    "DEFA14A": "filing",
    "DEF 14A": "filing",
    "424B4":   "filing",
    "6-K":     "filing",
}


def _classify_form(form: str) -> str:
    return FORM_TYPE_MAP.get(form, "filing")


def _build_headline(entity_name: str, form: str) -> str:
    headlines = {
        "4":      f"{entity_name} insider filed Form 4 — change in beneficial ownership",
        "8-K":    f"{entity_name} filed 8-K: material corporate event",
        "10-K":   f"{entity_name} filed annual report (10-K)",
        "10-Q":   f"{entity_name} filed quarterly report (10-Q)",
        "SC 13G": f"{entity_name} large shareholder filed SC 13G — ownership disclosure",
        "SC 13D": f"{entity_name} large shareholder filed SC 13D — ownership disclosure",
        "13F-HR": f"{entity_name} filed 13F-HR: quarterly institutional holdings",
        "S-1":    f"{entity_name} filed S-1 registration statement",
        "6-K":    f"{entity_name} filed 6-K: foreign private issuer report",
    }
    return headlines.get(form, f"{entity_name} filed {form} with the SEC")


def _fetch_cik_sync(cik: str, entity_name: str) -> list[dict] | None:
    """Synchronous single-entity fetch using httpx (no proxy issues on Windows)."""
    url = f"{EDGAR_BASE}/CIK{cik}.json"
    try:
        with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        filings = data.get("filings", {}).get("recent", {})
        forms   = filings.get("form", [])
        dates   = filings.get("filingDate", [])
        accnums = filings.get("accessionNumber", [])
        docs    = filings.get("primaryDocument", [])

        results = []
        seen_forms: set[str] = set()
        for i, form in enumerate(forms):
            # Max 2 filings per entity, skip duplicate form types
            if len(results) >= 2:
                break
            if form in seen_forms:
                continue
            seen_forms.add(form)
            accnum   = (accnums[i] if i < len(accnums) else "").replace("-", "")
            doc      = docs[i] if i < len(docs) else ""
            date_str = dates[i] if i < len(dates) else ""
            cik_int  = int(cik)
            source_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{accnum}/{doc}"
            results.append({
                "form":       form,
                "event_type": _classify_form(form),
                "headline":   _build_headline(entity_name, form),
                "date":       date_str,
                "source_url": source_url,
            })
        return results
    except httpx.HTTPStatusError as e:
        print(f"[EDGAR] HTTP {e.response.status_code} for {entity_name}")
        return None
    except Exception as exc:
        print(f"[EDGAR] Error fetching {entity_name}: {exc}")
        return None


def run_edgar_sync(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch recent SEC filings for all seeded companies synchronously.
    Uses a polite delay between requests to respect EDGAR rate limits.
    Returns count of new events inserted.
    """
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()

    for entity_name, cik in ENTITY_CIK_MAP.items():
        entity_id = entity_map.get(entity_name)
        if not entity_id:
            continue

        filings = _fetch_cik_sync(cik, entity_name)
        if not filings:
            time.sleep(0.5)
            continue

        for f in filings:
            # Deduplicate by entity + headline
            exists = db_conn.execute(
                "SELECT 1 FROM events WHERE entity_id=? AND headline=?",
                (entity_id, f["headline"]),
            ).fetchone()
            if exists:
                continue

            # Look up entity details for scoring
            entity_row = db_conn.execute(
                "SELECT net_worth FROM entities WHERE id=?", (entity_id,)
            ).fetchone()
            entity_data = {"net_worth": entity_row[0] if entity_row else 0}

            from backend.scoring import score_event
            importance = score_event(
                {"headline": f["headline"], "event_type": f["event_type"],
                 "source_name": "SEC EDGAR"},
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
                    f["event_type"],
                    f["headline"],
                    f["source_url"],
                    "SEC EDGAR",
                    f["date"],
                    now,
                    importance,
                ),
            )
            inserted += 1

        db_conn.commit()
        time.sleep(0.15)  # ~6 req/sec — well within EDGAR limits

    return inserted


# Async wrapper kept for compatibility but delegates to sync version
async def fetch_edgar_filings(db_conn: Any, entity_map: dict[str, str]) -> int:
    return run_edgar_sync(db_conn, entity_map)
