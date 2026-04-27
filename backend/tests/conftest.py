"""Shared fixtures for all backend tests."""
import sqlite3
import uuid
import tempfile
import os
from datetime import datetime, timezone
import pytest


@pytest.fixture
def db():
    """Temp-file SQLite DB with full schema applied."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    os.environ['DB_PATH'] = db_path
    try:
        from backend.database import init_db, get_connection
        init_db()
        conn = get_connection()
        yield conn
        conn.close()
    finally:
        del os.environ['DB_PATH']
        try:
            os.unlink(db_path)
        except OSError:
            pass


@pytest.fixture
def sample_entity(db):
    eid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO entities (id, name, type, sector, created_at) VALUES (?,?,?,?,?)",
        (eid, 'Test Corp', 'company', 'Technology', datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return eid


@pytest.fixture
def sample_event(db, sample_entity):
    evid = str(uuid.uuid4())
    db.execute(
        "INSERT INTO events (id, entity_id, event_type, headline, ingested_at) VALUES (?,?,?,?,?)",
        (evid, sample_entity, 'news', 'Test Corp announces record earnings', datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return evid
