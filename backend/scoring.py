"""
Capital Lens — Algorithmic event importance scoring.

Produces a 1-5 priority score from objective, measurable factors BEFORE
AI enrichment runs. The AI then validates/adjusts ±1 based on context.

Scoring breakdown (max 100 points):
  Amount factor   0-35 pts  (log scale: transaction/deal size)
  Entity tier     0-20 pts  (market cap / net worth of the entity)
  Event type      0-25 pts  (acquisition > congressional > insider > news > filing)
  Keyword signals 0-20 pts  (critical / high / political headline terms)

Thresholds → 1-5:
  80-100  → 5  Critical   (market-moving, sector-wide impact)
  60-79   → 4  High       (significant, multi-sector attention)
  35-59   → 3  Notable    (worth tracking, moderate signal)
  15-34   → 2  Low        (routine, limited broader impact)
  0-14    → 1  Minimal    (admin/maintenance, noise)
"""

from __future__ import annotations

# ── Amount tier scores (logarithmic scale) ──────────────────────────────────
# Ordered descending — first threshold crossed wins.
AMOUNT_TIERS: list[tuple[float, int]] = [
    (100_000_000_000, 35),   # $100B+
    (50_000_000_000,  33),   # $50B+
    (10_000_000_000,  30),   # $10B+
    (1_000_000_000,   24),   # $1B+
    (500_000_000,     19),   # $500M+
    (100_000_000,     14),   # $100M+
    (10_000_000,       9),   # $10M+
    (1_000_000,        5),   # $1M+
    (100_000,          2),   # $100K+
]

# ── Entity tier scores (market cap / net worth) ──────────────────────────────
ENTITY_TIERS: list[tuple[float, int]] = [
    (2_000_000_000_000, 20),  # $2T+  (Apple, Microsoft)
    (500_000_000_000,   16),  # $500B+
    (100_000_000_000,   12),  # $100B+
    (10_000_000_000,     8),  # $10B+
    (1_000_000_000,      5),  # $1B+
    (0,                  2),  # any known entity
]

# ── Event type base scores ────────────────────────────────────────────────────
EVENT_TYPE_SCORES: dict[str, int] = {
    "acquisition":        25,
    "congressional_trade": 18,  # Political intelligence premium
    "insider_sale":        13,
    "news":                11,
    "filing":               7,
}

# ── Headline keyword tiers ────────────────────────────────────────────────────
# CRITICAL (20 pts) — events that typically move markets
CRITICAL_KEYWORDS: list[str] = [
    "acquisition", "merger", "acquires", "acquired",
    "bankrupt", "bankruptcy", "chapter 11",
    "fraud", "indicted", "criminal charges", "sec charges", "sec investigation",
    "record revenue", "record profit", "record earnings", "all-time high",
    "ceo resign", "ceo fired", "ceo steps down",
    "first ever", "historic", "unprecedented",
    "antitrust", "monopoly ruling", "break up",
    "whistleblower", "data breach",
]

# HIGH (13 pts) — materially significant events
HIGH_KEYWORDS: list[str] = [
    "billion", "quarterly earnings", "annual report",
    "ipo", "initial public offering", "spac",
    "layoffs", "restructuring", "workforce reduction",
    "contract", "awarded", "partnership",
    "dividend", "buyback", "share repurchase",
    "raises", "funding round", "valuation",
    "fine", "penalty", "settlement", "lawsuit filed",
    "short seller", "downgrade", "upgrade",
]

# POLITICAL / GOVERNMENT (8 pts) — regulatory & government-related
POLITICAL_KEYWORDS: list[str] = [
    "government contract", "federal contract", "defense contract",
    "pentagon", "department of defense", "dod", "darpa",
    "executive order", "regulation", "regulatory",
    "congress", "senate", "house of representatives",
    "sec rule", "ftc", "doj", "department of justice",
    "sanctions", "export ban", "tariff",
]


def _tier_score(value: float, tiers: list[tuple[float, int]]) -> int:
    """Return the score for the first tier threshold the value meets."""
    for threshold, pts in sorted(tiers, reverse=True, key=lambda t: t[0]):
        if value >= threshold:
            return pts
    return 0


def score_event(event: dict, entity: dict | None = None) -> int:
    """
    Compute a deterministic 1-5 importance score for an event.

    Args:
        event:  Event dict (needs headline, amount, event_type).
        entity: Entity dict (needs net_worth). Pass None to skip entity tier.

    Returns:
        Integer 1-5 (1=minimal, 5=critical).
    """
    total = 0

    # 1. Amount factor
    amount = event.get("amount") or 0
    total += _tier_score(amount, AMOUNT_TIERS)

    # 2. Entity tier
    if entity:
        net_worth = entity.get("net_worth") or 0
        total += _tier_score(net_worth, ENTITY_TIERS)
    else:
        total += 2  # default — we have an entity, just no net_worth

    # 3. Event type
    etype = event.get("event_type") or ""
    total += EVENT_TYPE_SCORES.get(etype, 5)

    # 4. Keyword signals (headline + source_name)
    text = (
        (event.get("headline") or "")
        + " "
        + (event.get("source_name") or "")
    ).lower()

    if any(kw in text for kw in CRITICAL_KEYWORDS):
        total += 20
    elif any(kw in text for kw in HIGH_KEYWORDS):
        total += 13
    elif any(kw in text for kw in POLITICAL_KEYWORDS):
        total += 8

    # Map to 1-5
    if total >= 80:
        return 5  # Critical
    if total >= 60:
        return 4  # High
    if total >= 35:
        return 3  # Notable
    if total >= 15:
        return 2  # Low
    return 1       # Minimal


def importance_label(score: int) -> str:
    """Human-readable label for an importance score."""
    return {1: "Minimal", 2: "Low", 3: "Notable", 4: "High", 5: "Critical"}.get(score, "Unknown")
