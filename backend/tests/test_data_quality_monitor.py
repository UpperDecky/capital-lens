"""Tests for the IngestorMonitor service."""
import time
import uuid
import pytest
from datetime import datetime, timezone


@pytest.fixture
def mon(db):
    from backend.services.data_quality_monitor import IngestorMonitor
    return IngestorMonitor()


def test_log_success_cycle(mon):
    run_id = mon.log_ingestor_start('test_source')
    assert run_id is not None
    mon.log_ingestor_success(run_id, events_fetched=10, events_inserted=5, duration_seconds=1.5)
    status = mon.get_ingestor_status('test_source')
    assert status['status'] == 'success'
    assert status['consecutive_failures'] == 0


def test_log_failure_cycle(mon):
    run_id = mon.log_ingestor_start('failing_source')
    mon.log_ingestor_failure(run_id, error_message='Connection timeout', duration_seconds=0.2)
    status = mon.get_ingestor_status('failing_source')
    assert status['status'] == 'failed'
    assert status['consecutive_failures'] == 1


def test_never_run_status(mon):
    status = mon.get_ingestor_status('brand_new_ingestor')
    assert status['status'] == 'never_run'


def test_get_last_n_runs(mon):
    for _ in range(3):
        run_id = mon.log_ingestor_start('rss')
        mon.log_ingestor_success(run_id, 5, 5, 0.5)
    runs = mon.get_last_n_runs('rss', limit=2)
    assert len(runs) == 2


def test_consecutive_failures_increment(mon):
    for i in range(3):
        run_id = mon.log_ingestor_start('bad_source')
        mon.log_ingestor_failure(run_id, 'err', 0.1)
    status = mon.get_ingestor_status('bad_source')
    assert status['consecutive_failures'] == 3


def test_success_resets_failures(mon):
    for _ in range(2):
        run_id = mon.log_ingestor_start('recover_source')
        mon.log_ingestor_failure(run_id, 'err', 0.1)
    run_id = mon.log_ingestor_start('recover_source')
    mon.log_ingestor_success(run_id, 1, 1, 0.5)
    status = mon.get_ingestor_status('recover_source')
    assert status['consecutive_failures'] == 0
