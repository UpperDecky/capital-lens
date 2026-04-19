"""
Flow map router — returns nodes + edges for the Obsidian-style graph.

Edge sources (in priority order):
  1. Seeded high-confidence relationships (CEO/founder ties, known investments)
  2. Political seeded edges (known stock holdings, donor relationships)
  3. Congressional trade events → politician owns/trades stock in company
  4. Acquisition events → acquirer controls target
  5. Analysis JSON relationships → AI-derived entity connections
"""
import json
from typing import Optional
from fastapi import APIRouter, Query
from backend.database import get_connection

router = APIRouter()

# ── Seeded relationship graph ─────────────────────────────────────────────────
# (source_name, target_name, edge_type, label, weight 1-5)
# These are high-confidence, human-verified edges.
SEED_EDGES: list[tuple[str, str, str, str, int]] = [
    # Executive / board control edges
    ("Elon Musk",   "Tesla",             "board",      "CEO",             5),
    ("Elon Musk",   "SpaceX",            "board",      "CEO & founder",   5),
    ("Jeff Bezos",  "Amazon",            "board",      "founder",         5),
    ("Mark Zuckerberg", "Meta",          "board",      "CEO & founder",   5),
    ("Warren Buffett", "Berkshire Hathaway", "board",  "CEO",             5),
    ("Bill Gates",  "Microsoft",         "board",      "co-founder",      4),
    ("Larry Ellison", "Berkshire Hathaway", "investment", "major holder", 3),
    # Major institutional holdings
    ("BlackRock",   "Apple",             "investment", "largest shareholder", 5),
    ("BlackRock",   "Microsoft",         "investment", "largest shareholder", 5),
    ("BlackRock",   "Nvidia",            "investment", "top 3 holder",    4),
    ("BlackRock",   "Alphabet",          "investment", "major holder",    4),
    ("BlackRock",   "Amazon",            "investment", "major holder",    4),
    ("Berkshire Hathaway", "Apple",      "investment", "$170B+ stake",    5),
    ("Berkshire Hathaway", "Goldman Sachs", "investment", "former holder", 2),
    ("Berkshire Hathaway", "JPMorgan",   "investment", "former holder",   2),
    # Strategic investments
    ("Amazon",      "Anthropic",         "investment", "invested $4B",    5),
    ("Microsoft",   "OpenAI",            "investment", "invested $13B",   5),
    ("Elon Musk",   "OpenAI",            "competitor", "rival xAI",       3),
    ("George Soros","Alphabet",          "investment", "holds position",  3),
    ("Ken Griffin", "Visa",              "investment", "holds position",  2),
    # Industry / supply chain
    ("Tesla",       "SpaceX",            "partner",    "shared leadership", 3),
    ("Palantir",    "Lockheed Martin",   "partner",    "defense AI partner", 4),
    ("Palantir",    "JPMorgan",          "partner",    "financial analytics", 3),
    ("Visa",        "JPMorgan",          "partner",    "card network partner", 4),
    ("Visa",        "Goldman Sachs",     "partner",    "card network partner", 3),
    ("Goldman Sachs", "JPMorgan",        "competitor", "investment banking", 3),
    ("BlackRock",   "Goldman Sachs",     "competitor", "asset management", 3),
    ("ExxonMobil",  "BlackRock",         "shareholder","ESG engagement",  2),
    ("Lockheed Martin", "Palantir",      "customer",   "AI/data analytics", 3),
    # Tech competition / partnerships
    ("OpenAI",      "Anthropic",         "competitor", "AI research",     4),
    ("Nvidia",      "OpenAI",            "partner",    "GPU supplier",    5),
    ("Nvidia",      "Microsoft",         "partner",    "Azure AI compute", 4),
    ("Nvidia",      "Alphabet",          "partner",    "GCP AI compute",  3),
    ("Nvidia",      "Amazon",            "partner",    "AWS AI compute",  3),
    ("Apple",       "OpenAI",            "partner",    "Apple Intelligence", 4),
    ("SpaceX",      "Palantir",          "partner",    "satellite data",  3),
    # Political / regulatory connections
    ("Elon Musk",   "Donald Trump",      "political",  "administration ally", 4),
    ("Peter Thiel", "Palantir",          "board",      "co-founder",      4),  # note: not seeded but important
]

# Political holdings (documented/reported stock positions)
POLITICAL_EDGES: list[tuple[str, str, str, str, int]] = [
    ("Nancy Pelosi",  "Nvidia",     "political_trade", "purchased calls",  4),
    ("Nancy Pelosi",  "Microsoft",  "political_trade", "holds stock",      3),
    ("Nancy Pelosi",  "Alphabet",   "political_trade", "holds stock",      3),
    ("Nancy Pelosi",  "Apple",      "political_trade", "holds stock",      3),
    ("Nancy Pelosi",  "Amazon",     "political_trade", "holds stock",      2),
    ("Tommy Tuberville", "Nvidia",  "political_trade", "purchased stock",  3),
    ("Tommy Tuberville", "Tesla",   "political_trade", "purchased stock",  2),
    ("Mitt Romney",   "Goldman Sachs", "investment",   "Bain Capital ties", 3),
    ("Mitt Romney",   "Berkshire Hathaway", "investment", "disclosed holding", 2),
    ("Mitch McConnell", "BlackRock", "political",      "donor relationship", 2),
    ("Donald Trump",  "Goldman Sachs", "political",    "Treasury relationship", 3),
    ("Donald Trump",  "JPMorgan",   "political",       "banking relationship", 2),
    ("Ro Khanna",     "Nvidia",     "political_trade", "holds position",   2),
    ("Ro Khanna",     "Apple",      "political_trade", "holds position",   2),
    ("Gavin Newsom",  "Tesla",      "political",       "CA EV policy",     3),
    ("Gavin Newsom",  "Alphabet",   "political",       "CA tech policy",   2),
    ("Pete Buttigieg","Tesla",      "political",       "EV infrastructure", 3),
    ("Pete Buttigieg","Lockheed Martin", "political",  "DOT oversight",    2),
]

EDGE_TYPES_ORDER = [
    "board", "investment", "partner", "competitor",
    "customer", "supplier", "political_trade", "political",
    "congressional_trade", "acquisition",
]


def _resolve_name(name: str, entity_map: dict[str, str]) -> Optional[str]:
    """Try to find entity_id by exact, lowercase, or partial match."""
    if not name:
        return None
    name_l = name.lower().strip()
    # Exact lower match
    if name_l in entity_map:
        return entity_map[name_l]
    # Partial: name is contained in entity name
    for key, eid in entity_map.items():
        if name_l in key or key in name_l:
            return eid
    return None


@router.get("/flow")
def get_flow(
    sector: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None, alias="type"),
    limit: int = Query(80, ge=10, le=150),
) -> dict:
    conn = get_connection()

    # ── Nodes ───────────────────────────────────────────────────────────────
    where_parts = []
    where_params: list = []
    if sector:
        where_parts.append("sector = ?")
        where_params.append(sector)
    if entity_type:
        where_parts.append("type = ?")
        where_params.append(entity_type)
    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    entity_rows = conn.execute(
        f"SELECT * FROM entities {where_clause} ORDER BY net_worth DESC LIMIT ?",
        [*where_params, limit],
    ).fetchall()
    entities = [dict(r) for r in entity_rows]

    # Entity lookup maps
    id_to_entity = {e["id"]: e for e in entities}
    name_to_id   = {e["name"].lower(): e["id"] for e in entities}

    # Event counts per entity
    event_counts = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT entity_id, COUNT(*) FROM events GROUP BY entity_id"
        ).fetchall()
    }
    for e in entities:
        e["event_count"] = event_counts.get(e["id"], 0)

    # ── Edges ───────────────────────────────────────────────────────────────
    edges: list[dict] = []
    seen: set[str] = set()

    def add_edge(
        src_id: str, tgt_id: str, etype: str, label: str, weight: int = 2
    ) -> None:
        if not src_id or not tgt_id or src_id == tgt_id:
            return
        # Both nodes must be in our node set
        if src_id not in id_to_entity or tgt_id not in id_to_entity:
            return
        dedup = f"{src_id}|{tgt_id}|{etype}"
        if dedup in seen:
            return
        seen.add(dedup)
        edges.append({
            "source": src_id,
            "target": tgt_id,
            "type": etype,
            "label": label,
            "weight": weight,
        })

    # 1. Seeded structural edges
    for src_name, tgt_name, etype, label, weight in SEED_EDGES:
        add_edge(
            name_to_id.get(src_name.lower(), ""),
            name_to_id.get(tgt_name.lower(), ""),
            etype, label, weight,
        )

    # 2. Political seeded edges
    for src_name, tgt_name, etype, label, weight in POLITICAL_EDGES:
        add_edge(
            name_to_id.get(src_name.lower(), ""),
            name_to_id.get(tgt_name.lower(), ""),
            etype, label, weight,
        )

    # 3. Congressional trade events → politician → company edges
    congress_rows = conn.execute(
        """SELECT e.entity_id, e.headline, e.amount
           FROM events e
           WHERE e.event_type = 'congressional_trade'
              OR e.subtype = 'congressional_trade'
           LIMIT 200"""
    ).fetchall()
    for row in congress_rows:
        politician_id = row["entity_id"]
        headline = row["headline"].lower()
        # Match ticker/company name in headline against entity names
        for name_lower, company_id in name_to_id.items():
            if company_id != politician_id and len(name_lower) > 3 and name_lower in headline:
                entity_obj = id_to_entity.get(politician_id, {})
                pol_name = entity_obj.get("name", "politician")
                add_edge(politician_id, company_id, "congressional_trade",
                         f"{pol_name} traded", max(1, int((row['amount'] or 0) / 50000)))
                break  # one company per event

    # 4. Acquisition events → acquirer controls target
    acq_rows = conn.execute(
        """SELECT e.entity_id, e.headline
           FROM events e WHERE e.event_type = 'acquisition' LIMIT 100"""
    ).fetchall()
    for row in acq_rows:
        acquirer_id = row["entity_id"]
        headline_lower = row["headline"].lower()
        # Try to find target company name mentioned in headline
        for name_lower, target_id in name_to_id.items():
            if target_id != acquirer_id and len(name_lower) > 4 and name_lower in headline_lower:
                add_edge(acquirer_id, target_id, "acquisition", "acquired", 5)
                break

    # 5. Analysis JSON relationships
    analysis_rows = conn.execute(
        """SELECT e.entity_id, e.analysis
           FROM events e
           WHERE e.analysis IS NOT NULL
           LIMIT 200"""
    ).fetchall()
    for row in analysis_rows:
        try:
            analysis = json.loads(row["analysis"])
            for rel in analysis.get("relationships", []):
                target_name = (rel.get("entity") or "").strip()
                direction = rel.get("direction", "partner")
                label_map = {
                    "supplier":   "supplies",
                    "customer":   "customer of",
                    "competitor": "competes with",
                    "partner":    "partners with",
                    "investor":   "invested in",
                    "subsidiary": "subsidiary of",
                }
                label = label_map.get(direction, direction)
                tgt_id = _resolve_name(target_name, name_to_id)
                if tgt_id:
                    add_edge(row["entity_id"], tgt_id, direction, label, 2)
        except Exception:
            pass

    conn.close()
    return {
        "nodes": entities,
        "edges": edges,
        "edge_types": EDGE_TYPES_ORDER,
    }
