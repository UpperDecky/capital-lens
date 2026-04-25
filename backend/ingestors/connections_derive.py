"""
Connections derive ingestor -- builds entity_connections from ingested events.

Derives edges from three sources:
  1. Congressional trade events  -> politician --political_trade--> company
  2. Acquisition events          -> acquirer   --acquisition-->     target
  3. Analysis JSON relationships -> entity     --various-->         entity

Upserts into entity_connections with confidence and source metadata.
Valid_to is set to NULL (active) for all derived edges.
Runs every 6 hours via scheduler (after main ingestors complete).
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def _upsert_connection(
    conn: Any,
    src_id: str,
    tgt_id: str,
    etype: str,
    label: str,
    weight: int,
    confidence: str,
    derived_from: str,
    source_url: str | None = None,
    now: str | None = None,
) -> bool:
    """
    Insert connection or update label/weight/confidence if it already exists.
    Returns True if a new row was inserted.
    """
    if not src_id or not tgt_id or src_id == tgt_id:
        return False
    if not now:
        now = datetime.now(timezone.utc).isoformat()

    existing = conn.execute(
        "SELECT id, confidence FROM entity_connections "
        "WHERE source_id=? AND target_id=? AND edge_type=?",
        (src_id, tgt_id, etype),
    ).fetchone()

    if existing:
        # Only upgrade confidence, never downgrade
        conf_rank = {"low": 0, "medium": 1, "high": 2}
        if conf_rank.get(confidence, 0) > conf_rank.get(existing["confidence"], 0):
            conn.execute(
                "UPDATE entity_connections SET confidence=?, label=?, weight=? "
                "WHERE source_id=? AND target_id=? AND edge_type=?",
                (confidence, label, weight, src_id, tgt_id, etype),
            )
        return False

    conn.execute(
        """INSERT INTO entity_connections
           (id, source_id, target_id, edge_type, label, weight,
            confidence, derived_from, source_url, valid_from, valid_to, ingested_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,NULL,?)""",
        (
            str(uuid.uuid4()), src_id, tgt_id, etype, label, weight,
            confidence, derived_from, source_url, now, now,
        ),
    )
    return True


def derive_congressional_trade_connections(conn: Any) -> int:
    """
    Congressional trade events -> politician --political_trade--> company edge.
    Weight is proportional to trade amount.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    name_to_id = {
        r["name"].lower(): r["id"]
        for r in conn.execute("SELECT id, name FROM entities").fetchall()
    }
    id_to_type = {
        r["id"]: r["type"]
        for r in conn.execute("SELECT id, type FROM entities").fetchall()
    }

    rows = conn.execute(
        """SELECT e.entity_id, e.headline, e.amount, e.source_url
           FROM events e
           WHERE e.event_type = 'congressional_trade'
              OR e.subtype    = 'congressional_trade'
           ORDER BY e.occurred_at DESC
           LIMIT 500"""
    ).fetchall()

    for row in rows:
        politician_id = row["entity_id"]
        if id_to_type.get(politician_id) != "individual":
            continue
        headline_lower = (row["headline"] or "").lower()
        amount = row["amount"] or 0

        # Match company name in headline
        for name_lower, company_id in name_to_id.items():
            if (
                company_id != politician_id
                and len(name_lower) > 3
                and id_to_type.get(company_id) == "company"
                and name_lower in headline_lower
            ):
                weight = max(1, min(5, int(amount / 50_000))) if amount else 2
                pol_obj = conn.execute(
                    "SELECT name FROM entities WHERE id=?", (politician_id,)
                ).fetchone()
                pol_name = pol_obj["name"] if pol_obj else "politician"
                label = f"{pol_name} -- congressional trade"
                if _upsert_connection(
                    conn, politician_id, company_id,
                    "congressional_trade", label, weight,
                    "high", "event_congressional_trade",
                    row["source_url"], now,
                ):
                    inserted += 1
                break

    if inserted:
        conn.commit()
        print(f"[Connections] Derived {inserted} congressional trade connections")
    return inserted


def derive_acquisition_connections(conn: Any) -> int:
    """
    Acquisition events -> acquirer --acquisition--> target company edge.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    name_to_id = {
        r["name"].lower(): r["id"]
        for r in conn.execute("SELECT id, name FROM entities").fetchall()
    }

    rows = conn.execute(
        """SELECT e.entity_id, e.headline, e.source_url
           FROM events e WHERE e.event_type = 'acquisition'
           LIMIT 200"""
    ).fetchall()

    for row in rows:
        acquirer_id = row["entity_id"]
        headline_lower = (row["headline"] or "").lower()

        for name_lower, target_id in name_to_id.items():
            if (
                target_id != acquirer_id
                and len(name_lower) > 4
                and name_lower in headline_lower
            ):
                if _upsert_connection(
                    conn, acquirer_id, target_id,
                    "acquisition", "acquired", 5,
                    "high", "event_acquisition",
                    row["source_url"], now,
                ):
                    inserted += 1
                break

    if inserted:
        conn.commit()
        print(f"[Connections] Derived {inserted} acquisition connections")
    return inserted


def derive_analysis_connections(conn: Any) -> int:
    """
    AI analysis JSON 'relationships' -> entity --type--> entity edges.
    These get confidence='medium' since they are AI-inferred.
    """
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    name_to_id = {
        r["name"].lower(): r["id"]
        for r in conn.execute("SELECT id, name FROM entities").fetchall()
    }

    # Helper for fuzzy name resolution
    def resolve(name: str) -> str | None:
        if not name:
            return None
        nl = name.lower().strip()
        if nl in name_to_id:
            return name_to_id[nl]
        for key, eid in name_to_id.items():
            if nl in key or key in nl:
                return eid
        return None

    label_map = {
        "supplier":   "supplies",
        "customer":   "customer of",
        "competitor": "competes with",
        "partner":    "partners with",
        "investor":   "invested in",
        "subsidiary": "subsidiary of",
        "investment": "invested in",
    }

    rows = conn.execute(
        """SELECT e.entity_id, e.analysis
           FROM events e
           WHERE e.analysis IS NOT NULL
           LIMIT 500"""
    ).fetchall()

    for row in rows:
        try:
            analysis = json.loads(row["analysis"])
        except Exception:
            continue

        for rel in analysis.get("relationships", []):
            target_name = (rel.get("entity") or "").strip()
            direction = rel.get("direction", "partner")
            label = label_map.get(direction, direction)
            tgt_id = resolve(target_name)
            if tgt_id and tgt_id != row["entity_id"]:
                if _upsert_connection(
                    conn, row["entity_id"], tgt_id,
                    direction, label, 2,
                    "medium", "event_analysis",
                    None, now,
                ):
                    inserted += 1

    if inserted:
        conn.commit()
        print(f"[Connections] Derived {inserted} analysis-based connections")
    return inserted


def expire_stale_connections(conn: Any, days: int = 180) -> int:
    """
    Mark connections derived from events as expired if no recent supporting event.
    Only applies to non-seed edges (derived_from starts with 'event_').
    Seed structural edges (board, investment) never expire automatically.
    """
    from datetime import timedelta
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=days)
    ).isoformat()

    # Find derived connections with no supporting event in the last 'days' days
    result = conn.execute(
        """UPDATE entity_connections
           SET valid_to = ?
           WHERE derived_from LIKE 'event_%'
             AND valid_to IS NULL
             AND ingested_at < ?
             AND edge_type IN ('congressional_trade','acquisition')""",
        (datetime.now(timezone.utc).isoformat(), cutoff),
    )
    expired = result.rowcount
    if expired:
        conn.commit()
        print(f"[Connections] Expired {expired} stale event-derived connections")
    return expired


def run_connections_derive(conn: Any) -> int:
    """Main entry point. Returns total connections derived/updated."""
    total = 0
    total += derive_congressional_trade_connections(conn)
    total += derive_acquisition_connections(conn)
    total += derive_analysis_connections(conn)
    expire_stale_connections(conn)
    return total
