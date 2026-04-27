"""Database schema and migration tests."""
import uuid
from datetime import datetime, timezone
import pytest


def test_all_tables_exist(db):
    tables = {
        row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    required = {
        'entities', 'events', 'users', 'countries',
        'geo_events', 'adsb_events', 'maritime_events',
        'satellite_events', 'prediction_markets', 'infra_events',
        'entity_connections', 'cash_flows', 'ingestor_runs',
    }
    missing = required - tables
    assert not missing, f"Missing tables: {missing}"


def test_insert_entity(db):
    eid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO entities (id, name, type, sector, created_at) VALUES (?,?,?,?,?)",
        (eid, 'ACME Inc', 'company', 'Technology', datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    row = db.execute("SELECT name FROM entities WHERE id=?", (eid,)).fetchone()
    assert row['name'] == 'ACME Inc'


def test_insert_event_with_fk(db, sample_entity):
    evid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO events (id, entity_id, event_type, headline, ingested_at) VALUES (?,?,?,?,?)",
        (evid, sample_entity, 'news', 'Big announcement', datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    row = db.execute("SELECT headline FROM events WHERE id=?", (evid,)).fetchone()
    assert row['headline'] == 'Big announcement'


def test_fk_enforced(db):
    with pytest.raises(Exception):
        db.execute(
            "INSERT INTO events (id, entity_id, event_type, headline, ingested_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), 'nonexistent-id', 'news', 'x', datetime.now(timezone.utc).isoformat()),
        )
        db.commit()


def test_events_importance_default(db, sample_entity):
    evid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO events (id, entity_id, event_type, headline, ingested_at) VALUES (?,?,?,?,?)",
        (evid, sample_entity, 'news', 'Test', datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    row = db.execute("SELECT importance FROM events WHERE id=?", (evid,)).fetchone()
    assert row['importance'] == 3


def test_ingestor_runs_table(db):
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        """INSERT INTO ingestor_runs
           (id, ingestor_name, started_at, status, events_inserted, run_duration_seconds)
           VALUES (?,?,?,?,?,?)""",
        (run_id, 'test_ingestor', now, 'success', 5, 1.23),
    )
    db.commit()
    row = db.execute("SELECT * FROM ingestor_runs WHERE id=?", (run_id,)).fetchone()
    assert row['ingestor_name'] == 'test_ingestor'
    assert row['events_inserted'] == 5


def test_user_tier_constraint(db):
    with pytest.raises(Exception):
        db.execute(
            "INSERT INTO users (id, email, password_hash, tier, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), 'bad@test.com', 'hash', 'superadmin', datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
