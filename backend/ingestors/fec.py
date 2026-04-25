"""
FEC (Federal Election Commission) campaign finance ingestor.

Tracks who is donating to — and receiving money from — tracked politicians.
Shows the financial relationships between corporations and political figures.

Free API key via api.data.gov: https://api.open.fec.gov/developers/
Key in .env: FEC_API_KEY
"""
import uuid
from datetime import datetime, timezone
from typing import Any
import httpx

from backend.config import FEC_API_KEY

BASE_URL = "https://api.open.fec.gov/v1"

HEADERS = {
    "User-Agent": "CapitalLens research@capitallens.dev",
    "Accept": "application/json",
}

# Hardcoded FEC candidate IDs — permanent identifiers that never change.
# Only federal candidates appear in FEC; state-level politicians (Newsom, Buttigieg
# post-USDOT) are intentionally omitted.
# Source: https://www.fec.gov/data/candidates/
POLITICIAN_CANDIDATE_IDS: dict[str, str] = {
    "Nancy Pelosi":            "H8CA05036",
    "Donald Trump":            "P80001571",
    "Mitch McConnell":         "S8KY00012",
    "Mitt Romney":             "S2UT00436",
    "Alexandria Ocasio-Cortez":"H8NY15148",
    "Tommy Tuberville":        "S0AL00289",
    "Ro Khanna":               "H6CA17148",
    "Dan Crenshaw":            "H8TX02095",
}

# Corporate entities to track for PAC/lobbying contributions
CORPORATE_DONORS: list[str] = [
    "Apple", "Microsoft", "Alphabet", "Meta", "Amazon",
    "Goldman Sachs", "JPMorgan", "BlackRock",
    "Palantir", "Lockheed Martin", "Boeing", "Raytheon",
    "Pfizer", "ExxonMobil", "Visa",
]

# Corporate name → FEC contributor name fragment
CORPORATE_ALIASES: dict[str, str] = {
    "Apple":          "apple",
    "Microsoft":      "microsoft",
    "Alphabet":       "google",
    "Meta":           "meta platforms",
    "Amazon":         "amazon",
    "Goldman Sachs":  "goldman sachs",
    "JPMorgan":       "jpmorgan",
    "BlackRock":      "blackrock",
    "Palantir":       "palantir",
    "Lockheed Martin":"lockheed",
    "Boeing":         "boeing",
    "Raytheon":       "raytheon",
    "Pfizer":         "pfizer",
    "ExxonMobil":     "exxonmobil",
    "Visa":           "visa",
}


def _fetch_top_donors(candidate_id: str, cycle: int = 2024) -> list[dict]:
    """Fetch top individual/PAC donors to a candidate."""
    if not FEC_API_KEY:
        return []

    try:
        with httpx.Client(headers=HEADERS, timeout=20) as client:
            resp = client.get(
                f"{BASE_URL}/schedules/schedule_a/",
                params={
                    "api_key":        FEC_API_KEY,
                    "candidate_id":   candidate_id,
                    "two_year_transaction_period": cycle,
                    "per_page":       20,
                    "sort":           "-contribution_receipt_amount",
                    "is_individual":  "false",  # include PACs / orgs
                },
            )
            resp.raise_for_status()
            return resp.json().get("results", [])
    except Exception as exc:
        print(f"[FEC] Donor fetch error for candidate {candidate_id}: {exc}")
    return []


def _fetch_candidate_totals(candidate_id: str) -> tuple[dict | None, int]:
    """
    Fetch the most recent fundraising totals for a candidate.
    Tries cycles from most recent backwards — candidates who didn't run
    in 2024 (e.g. McConnell, Romney) will have data in an earlier cycle.
    Returns (totals_dict, cycle_year) or (None, 0).
    """
    if not FEC_API_KEY:
        return None, 0

    for cycle in [2024, 2022, 2020, 2018]:
        try:
            with httpx.Client(headers=HEADERS, timeout=20) as client:
                resp = client.get(
                    f"{BASE_URL}/candidates/{candidate_id}/totals/",
                    params={
                        "api_key":  FEC_API_KEY,
                        "cycle":    cycle,
                        "per_page": 1,
                    },
                )
                if resp.status_code == 404:
                    continue  # no data for this cycle — try older
                resp.raise_for_status()
                results = resp.json().get("results", [])
                if results:
                    return results[0], cycle
        except Exception as exc:
            print(f"[FEC] Totals error for {candidate_id} cycle {cycle}: {exc}")
    return None, 0


def fetch_campaign_finance(db_conn: Any, entity_map: dict[str, str]) -> int:
    """
    Fetch FEC campaign finance data for tracked politicians.
    Creates events showing fundraising totals and notable donor relationships.
    Skips if FEC_API_KEY is not set.

    Returns count of new events inserted.
    """
    if not FEC_API_KEY:
        print("[FEC] No API key set — skipping (set FEC_API_KEY in .env)")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for politician_name, candidate_id in POLITICIAN_CANDIDATE_IDS.items():
        entity_id = entity_map.get(politician_name)
        if not entity_id:
            continue  # Not a seeded entity

        # --- Event 1: Fundraising totals (most recent cycle available) ---
        totals, current_cycle = _fetch_candidate_totals(candidate_id)
        if totals:
            total_raised = totals.get("receipts") or 0
            total_spent  = totals.get("disbursements") or 0

            if total_raised and total_raised > 0:
                raised_str = f"${total_raised:,.0f}"
                headline = (
                    f"{politician_name} raised {raised_str} in {current_cycle} election cycle"
                    f" — FEC campaign finance disclosure"
                )

                exists = db_conn.execute(
                    "SELECT 1 FROM events WHERE entity_id=? AND headline=?",
                    (entity_id, headline),
                ).fetchone()

                if not exists:
                    from backend.scoring import score_event
                    event_draft = {
                        "headline":   headline,
                        "amount":     total_raised,
                        "event_type": "filing",
                        "source_name": "FEC",
                    }
                    importance = score_event(event_draft)

                    db_conn.execute(
                        """INSERT INTO events
                           (id, entity_id, event_type, headline, amount, currency,
                            source_url, source_name, occurred_at, ingested_at, importance)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            str(uuid.uuid4()),
                            entity_id,
                            "filing",
                            headline,
                            total_raised,
                            "USD",
                            f"https://www.fec.gov/data/candidate/{candidate_id}/",
                            "Federal Election Commission",
                            f"{current_cycle}-01-01",
                            now,
                            importance,
                        ),
                    )
                    inserted += 1

        # --- Event 2: Top institutional donors (same cycle) ---
        donors = _fetch_top_donors(candidate_id, current_cycle) if current_cycle else []
        for donor in donors[:5]:  # Top 5 institutional donors only
            contributor = (donor.get("contributor_name") or "").strip()
            amount      = donor.get("contribution_receipt_amount")
            date_str    = donor.get("contribution_receipt_date") or f"{current_cycle}-01-01"

            if not contributor or not amount or amount < 5000:
                continue

            # Check if this donor is a tracked corporate entity
            matched_corp = None
            contrib_lower = contributor.lower()
            for corp_name, alias in CORPORATE_ALIASES.items():
                if alias in contrib_lower:
                    matched_corp = corp_name
                    break

            amount_str = f"${amount:,.0f}"
            if matched_corp:
                headline = (
                    f"{matched_corp} donated {amount_str} to {politician_name}'s campaign"
                    f" — FEC filing {current_cycle}"
                )
                corp_id = entity_map.get(matched_corp)
                # Store under the POLITICIAN entity (they received the money)
                target_id = entity_id
            else:
                headline = (
                    f"{contributor} contributed {amount_str} to {politician_name}'s campaign"
                    f" — FEC filing {current_cycle}"
                )
                target_id = entity_id

            exists = db_conn.execute(
                "SELECT 1 FROM events WHERE entity_id=? AND headline=?",
                (target_id, headline),
            ).fetchone()
            if exists:
                continue

            from backend.scoring import score_event
            event_draft = {
                "headline":   headline,
                "amount":     amount,
                "event_type": "filing",
                "source_name": "FEC",
            }
            importance = score_event(event_draft)

            db_conn.execute(
                """INSERT INTO events
                   (id, entity_id, event_type, headline, amount, currency,
                    source_url, source_name, occurred_at, ingested_at, importance)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    str(uuid.uuid4()),
                    target_id,
                    "filing",
                    headline,
                    float(amount),
                    "USD",
                    f"https://www.fec.gov/data/candidate/{candidate_id}/",
                    "Federal Election Commission",
                    date_str,
                    now,
                    importance,
                ),
            )
            inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[FEC] ✓ Inserted {inserted} new campaign finance events")
    return inserted
