"""Tests for entity linker matching logic."""
import uuid
from datetime import datetime, timezone
import pytest


@pytest.fixture
def linker(db):
    now = datetime.now(timezone.utc).isoformat()
    entities = [
        (str(uuid.uuid4()), 'Apple Inc', 'company', 'Technology', 'AAPL'),
        (str(uuid.uuid4()), 'Microsoft Corporation', 'company', 'Technology', 'MSFT'),
        (str(uuid.uuid4()), 'Tesla Inc', 'company', 'Automotive', 'TSLA'),
    ]
    for eid, name, typ, sector, ticker in entities:
        db.execute(
            "INSERT INTO entities (id, name, type, sector, ticker, description, created_at) VALUES (?,?,?,?,?,?,?)",
            (eid, name, typ, sector, ticker, f"Ticker: {ticker}", now),
        )
    db.commit()

    from backend.services.entity_linker import EntityLinker
    return EntityLinker()


def test_ticker_exact_match(linker):
    eid = linker.find_entity('some headline', ticker='AAPL')
    assert eid is not None


def test_name_substring_match(linker):
    eid = linker.find_entity('Apple Inc reports record quarterly earnings')
    assert eid is not None


def test_no_match_returns_none(linker):
    eid = linker.find_entity('Random unrelated text about nothing')
    assert eid is None


def test_ticker_beats_name(linker):
    eid_by_ticker = linker.find_entity('', ticker='TSLA')
    eid_by_name = linker.find_entity('Tesla Inc')
    assert eid_by_ticker == eid_by_name


def test_case_insensitive_ticker(linker):
    eid = linker.find_entity('', ticker='msft')
    assert eid is not None
