"""
Connections seed ingestor -- migrates hardcoded SEED_EDGES and POLITICAL_EDGES
from flow.py into the entity_connections table with proper metadata.

Only inserts rows that do not already exist (safe to call on every startup).
High-confidence seeded edges get confidence='high'; political trade edges get 'medium'.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

# These are duplicated from flow.py intentionally so flow.py can later
# read purely from the DB and this file becomes the single source of truth.

SEED_EDGES = [
    # (source_name, target_name, edge_type, label, weight, confidence)
    ("Elon Musk",          "Tesla",             "board",             "CEO",                         5, "high"),
    ("Elon Musk",          "SpaceX",            "board",             "CEO & founder",               5, "high"),
    ("Jeff Bezos",         "Amazon",            "board",             "founder",                     5, "high"),
    ("Mark Zuckerberg",    "Meta",              "board",             "CEO & founder",               5, "high"),
    ("Warren Buffett",     "Berkshire Hathaway","board",             "CEO",                         5, "high"),
    ("Bill Gates",         "Microsoft",         "board",             "co-founder",                  4, "high"),
    ("Larry Ellison",      "Berkshire Hathaway","investment",        "major holder",                3, "high"),
    ("BlackRock",          "Apple",             "investment",        "largest shareholder",         5, "high"),
    ("BlackRock",          "Microsoft",         "investment",        "largest shareholder",         5, "high"),
    ("BlackRock",          "Nvidia",            "investment",        "top 3 holder",                4, "high"),
    ("BlackRock",          "Alphabet",          "investment",        "major holder",                4, "high"),
    ("BlackRock",          "Amazon",            "investment",        "major holder",                4, "high"),
    ("Berkshire Hathaway", "Apple",             "investment",        "$170B+ stake",                5, "high"),
    ("Berkshire Hathaway", "Goldman Sachs",     "investment",        "former holder",               2, "medium"),
    ("Berkshire Hathaway", "JPMorgan",          "investment",        "former holder",               2, "medium"),
    ("Amazon",             "Anthropic",         "investment",        "invested $4B",                5, "high"),
    ("Microsoft",          "OpenAI",            "investment",        "invested $13B",               5, "high"),
    ("Elon Musk",          "OpenAI",            "competitor",        "rival xAI",                   3, "high"),
    ("George Soros",       "Alphabet",          "investment",        "holds position",              3, "medium"),
    ("Ken Griffin",        "Visa",              "investment",        "holds position",              2, "medium"),
    ("Tesla",              "SpaceX",            "partner",           "shared leadership",           3, "high"),
    ("Palantir",           "Lockheed Martin",   "partner",           "defense AI partner",          4, "high"),
    ("Palantir",           "JPMorgan",          "partner",           "financial analytics",         3, "high"),
    ("Visa",               "JPMorgan",          "partner",           "card network partner",        4, "high"),
    ("Visa",               "Goldman Sachs",     "partner",           "card network partner",        3, "high"),
    ("Goldman Sachs",      "JPMorgan",          "competitor",        "investment banking",          3, "high"),
    ("BlackRock",          "Goldman Sachs",     "competitor",        "asset management",            3, "high"),
    ("ExxonMobil",         "BlackRock",         "shareholder",       "ESG engagement",              2, "medium"),
    ("Lockheed Martin",    "Palantir",          "customer",          "AI/data analytics",           3, "high"),
    ("OpenAI",             "Anthropic",         "competitor",        "AI research",                 4, "high"),
    ("Nvidia",             "OpenAI",            "partner",           "GPU supplier",                5, "high"),
    ("Nvidia",             "Microsoft",         "partner",           "Azure AI compute",            4, "high"),
    ("Nvidia",             "Alphabet",          "partner",           "GCP AI compute",              3, "high"),
    ("Nvidia",             "Amazon",            "partner",           "AWS AI compute",              3, "high"),
    ("Apple",              "OpenAI",            "partner",           "Apple Intelligence",          4, "high"),
    ("SpaceX",             "Palantir",          "partner",           "satellite data",              3, "high"),
    ("Elon Musk",          "Donald Trump",      "political",         "administration ally",         4, "medium"),
]

POLITICAL_EDGES = [
    # (source_name, target_name, edge_type, label, weight, confidence)
    ("Nancy Pelosi",    "Nvidia",             "political_trade", "purchased calls",          4, "high"),
    ("Nancy Pelosi",    "Microsoft",          "political_trade", "holds stock",              3, "high"),
    ("Nancy Pelosi",    "Alphabet",           "political_trade", "holds stock",              3, "high"),
    ("Nancy Pelosi",    "Apple",              "political_trade", "holds stock",              3, "high"),
    ("Nancy Pelosi",    "Amazon",             "political_trade", "holds stock",              2, "high"),
    ("Tommy Tuberville","Nvidia",             "political_trade", "purchased stock",          3, "high"),
    ("Tommy Tuberville","Tesla",              "political_trade", "purchased stock",          2, "high"),
    ("Mitt Romney",     "Goldman Sachs",      "investment",      "Bain Capital ties",        3, "medium"),
    ("Mitt Romney",     "Berkshire Hathaway", "investment",      "disclosed holding",        2, "high"),
    ("Mitch McConnell", "BlackRock",          "political",       "donor relationship",       2, "low"),
    ("Donald Trump",    "Goldman Sachs",      "political",       "Treasury relationship",    3, "medium"),
    ("Donald Trump",    "JPMorgan",           "political",       "banking relationship",     2, "medium"),
    ("Ro Khanna",       "Nvidia",             "political_trade", "holds position",           2, "high"),
    ("Ro Khanna",       "Apple",              "political_trade", "holds position",           2, "high"),
    ("Gavin Newsom",    "Tesla",              "political",       "CA EV policy",             3, "medium"),
    ("Gavin Newsom",    "Alphabet",           "political",       "CA tech policy",           2, "medium"),
    ("Pete Buttigieg",  "Tesla",              "political",       "EV infrastructure",        3, "medium"),
    ("Pete Buttigieg",  "Lockheed Martin",    "political",       "DOT oversight",            2, "medium"),
]


def seed_connections(conn: Any) -> int:
    """
    Insert SEED_EDGES and POLITICAL_EDGES into entity_connections.
    Skips existing rows (idempotent). Returns count inserted.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    name_to_id = {
        r["name"].lower(): r["id"]
        for r in conn.execute("SELECT id, name FROM entities").fetchall()
    }

    all_edges = [
        (src, tgt, etype, label, weight, conf, "seed_structural")
        for src, tgt, etype, label, weight, conf in SEED_EDGES
    ] + [
        (src, tgt, etype, label, weight, conf, "seed_political")
        for src, tgt, etype, label, weight, conf in POLITICAL_EDGES
    ]

    for src_name, tgt_name, etype, label, weight, confidence, derived_from in all_edges:
        src_id = name_to_id.get(src_name.lower())
        tgt_id = name_to_id.get(tgt_name.lower())
        if not src_id or not tgt_id or src_id == tgt_id:
            continue

        # Check for existing
        existing = conn.execute(
            "SELECT id FROM entity_connections WHERE source_id=? AND target_id=? AND edge_type=?",
            (src_id, tgt_id, etype),
        ).fetchone()
        if existing:
            continue

        conn.execute(
            """INSERT INTO entity_connections
               (id, source_id, target_id, edge_type, label, weight,
                confidence, derived_from, valid_from, valid_to, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,NULL,?)""",
            (
                str(uuid.uuid4()), src_id, tgt_id, etype, label, weight,
                confidence, derived_from, now, now,
            ),
        )
        inserted += conn.execute("SELECT changes()").fetchone()[0]

    if inserted:
        conn.commit()
        print(f"[Connections] Seeded {inserted} structural connections")
    return inserted
