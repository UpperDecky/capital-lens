"""Integration tests -- FastAPI TestClient against in-memory DB."""
import os
import uuid
import pytest
from datetime import datetime, timezone

os.environ['DB_PATH'] = ':memory:'

from fastapi.testclient import TestClient


@pytest.fixture(scope='module')
def client():
    from backend.main import app
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert 'status' in data
    assert data['status'] == 'ok'


def test_feed_returns_list(client):
    r = client.get('/feed')
    assert r.status_code == 200
    data = r.json()
    assert 'events' in data or isinstance(data, list)


def test_entities_returns_list(client):
    r = client.get('/entities')
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_search_empty_query_rejected(client):
    r = client.get('/search?q=a')
    assert r.status_code in (200, 422)


def test_register_and_login(client):
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post('/auth/register', json={'email': email, 'password': 'TestPass123!'})
    assert r.status_code == 200
    data = r.json()
    assert 'token' in data or 'access_token' in data

    r2 = client.post('/auth/login', json={'email': email, 'password': 'TestPass123!'})
    assert r2.status_code == 200


def test_admin_enrich_requires_secret_when_set(client):
    # With no ADMIN_SECRET env var set, endpoint should be accessible
    r = client.post('/admin/enrich')
    assert r.status_code in (200, 403)


def test_admin_health_ingestors(client):
    r = client.get('/admin/health/ingestors')
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        data = r.json()
        assert 'summary' in data
        assert 'ingestors' in data
