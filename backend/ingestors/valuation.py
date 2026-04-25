"""
Valuation ingestor -- private companies and individual net worth.

Public company market caps are handled by market.py via Twelve Data
(price x shares_outstanding). This module only covers:
  - Private companies: latest funding round valuations
  - Individuals:       curated Forbes/Bloomberg estimates (April 2025)

Update PRIVATE_VALUATIONS and INDIVIDUAL_NET_WORTH each quarter.
Runs every 6 hours via scheduler.
"""
from datetime import datetime, timezone
from typing import Any


# ---- Private company valuations (last known from funding rounds / reports) --
# Update manually when a new round or secondary market valuation is reported.
# Format: name -> (valuation_usd, source_description)

PRIVATE_VALUATIONS: dict[str, tuple[float, str]] = {
    "SpaceX":    (3.5e11, "SpaceX secondary market Dec 2024"),
    "OpenAI":    (3.0e11, "OpenAI Series E Mar 2025 -- $300B valuation"),
    "Anthropic": (6.1e10, "Anthropic Series E Jan 2025 -- $61B valuation"),
}

# ---- Individual net worth (Forbes/Bloomberg estimates, April 2025) -----------
# These are inherently approximate. Update quarterly from Forbes Real-Time list.

INDIVIDUAL_NET_WORTH: dict[str, tuple[float, str]] = {
    "Elon Musk":          (3.0e11,  "Forbes Real-Time Apr 2025"),
    "Jeff Bezos":         (2.2e11,  "Forbes Real-Time Apr 2025"),
    "Mark Zuckerberg":    (2.1e11,  "Forbes Real-Time Apr 2025"),
    "Larry Ellison":      (1.85e11, "Forbes Real-Time Apr 2025"),
    "Warren Buffett":     (1.55e11, "Forbes Real-Time Apr 2025"),
    "Bill Gates":         (1.3e11,  "Forbes Real-Time Apr 2025"),
    "Ken Griffin":        (4.3e10,  "Forbes Apr 2025"),
    "Ray Dalio":          (1.8e10,  "Forbes Apr 2025"),
    "George Soros":       (7.0e9,   "Forbes Apr 2025"),
    "Carl Icahn":         (6.5e9,   "Forbes Apr 2025"),
    "Donald Trump":       (6.5e9,   "Forbes Apr 2025 -- DJT stock + real estate"),
    "Nancy Pelosi":       (2.5e8,   "Center for Responsive Politics 2024 disclosure"),
    "Mitt Romney":        (3.0e8,   "Senate SODR 2024"),
    "Mitch McConnell":    (3.5e7,   "Senate SODR 2024"),
    "Tommy Tuberville":   (1.5e7,   "Senate SODR 2024"),
    "Ro Khanna":          (2.5e7,   "House SODR 2024"),
    "Gavin Newsom":       (2.3e7,   "Forbes est. Apr 2025"),
    "Dan Crenshaw":       (4.0e6,   "House SODR 2024"),
    "Pete Buttigieg":     (7.0e6,   "Forbes est. 2024"),
    "Alexandria Ocasio-Cortez": (2.0e5, "House SODR 2024 -- minimal assets"),
}


def update_private_valuations(conn: Any) -> int:
    """Update private company valuations from curated funding round data."""
    now = datetime.now(timezone.utc).isoformat()
    updated = 0

    rows = conn.execute("SELECT id, name FROM entities WHERE type = 'company'").fetchall()
    name_to_id = {r["name"]: r["id"] for r in rows}

    for entity_name, (valuation, source) in PRIVATE_VALUATIONS.items():
        entity_id = name_to_id.get(entity_name)
        if not entity_id:
            continue
        conn.execute(
            """UPDATE entities
               SET net_worth = ?, net_worth_updated_at = ?, net_worth_source = ?
               WHERE id = ?""",
            (valuation, now, source, entity_id),
        )
        updated += 1
        print(f"[Valuation] {entity_name}: ${valuation/1e9:.1f}B (private est.)")

    if updated:
        conn.commit()
        print(f"[Valuation] Updated {updated} private company valuations")
    return updated


def update_individual_net_worth(conn: Any) -> int:
    """Update individual net worth from curated estimates."""
    now = datetime.now(timezone.utc).isoformat()
    updated = 0

    rows = conn.execute("SELECT id, name FROM entities WHERE type = 'individual'").fetchall()
    name_to_id = {r["name"]: r["id"] for r in rows}

    for entity_name, (net_worth, source) in INDIVIDUAL_NET_WORTH.items():
        entity_id = name_to_id.get(entity_name)
        if not entity_id:
            continue
        conn.execute(
            """UPDATE entities
               SET net_worth = ?, net_worth_updated_at = ?, net_worth_source = ?
               WHERE id = ?""",
            (net_worth, now, source, entity_id),
        )
        updated += 1

    if updated:
        conn.commit()
        print(f"[Valuation] Updated {updated} individual net worth estimates")
    return updated


def run_valuation_update(conn: Any) -> int:
    """Main entry point -- update private companies and individuals. Returns total updated."""
    total = 0
    total += update_private_valuations(conn)
    total += update_individual_net_worth(conn)
    return total
