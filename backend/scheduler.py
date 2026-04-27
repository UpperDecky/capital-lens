"""
APScheduler background jobs for Capital Lens.
All jobs run inside the FastAPI lifespan context.
IMPORTANT: Claude enrichment is called ONLY from here, never on page load.
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import (
    EDGAR_INTERVAL_MINUTES,
    RSS_INTERVAL_MINUTES,
    MARKET_INTERVAL_MINUTES,
    FORBES_INTERVAL_HOURS,
)

_scheduler: BackgroundScheduler | None = None


def _run_monitored(name: str, func, *args, **kwargs) -> None:
    """Run ingestor func wrapped with data quality monitoring."""
    try:
        from backend.services.data_quality_monitor import monitor
        run_id = monitor.log_ingestor_start(name)
        import time
        t0 = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - t0
            inserted = result if isinstance(result, int) else 0
            monitor.log_ingestor_success(run_id, inserted, inserted, duration, None)
            if inserted > 0:
                print(f"[Scheduler/{name}] {inserted} new records")
        except Exception as exc:
            duration = time.perf_counter() - t0
            monitor.log_ingestor_failure(run_id, str(exc), duration)
            print(f"[Scheduler/{name}] Error: {exc}")
    except Exception as exc:
        print(f"[Scheduler/{name}] Monitor error: {exc}")


def _job_edgar() -> None:
    from backend.database import get_connection
    from backend.ingestors.edgar import run_edgar_sync
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = run_edgar_sync(conn, emap)
    conn.close()
    return n


def _job_rss() -> None:
    from backend.database import get_connection
    from backend.ingestors.news_rss import fetch_rss_news
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_rss_news(conn, emap)
    conn.close()
    return n


def _job_market() -> None:
    from backend.database import get_connection
    from backend.ingestors.market import fetch_market_prices
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_market_prices(conn, emap)
    conn.close()
    return n


def _job_congress() -> None:
    from backend.database import get_connection
    from backend.ingestors.congress import fetch_congressional_trades
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_congressional_trades(conn, emap)
    conn.close()
    return n


def _job_usaspending() -> None:
    from backend.database import get_connection
    from backend.ingestors.usaspending import fetch_federal_contracts
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_federal_contracts(conn, emap)
    conn.close()
    return n


def _job_fred() -> None:
    from backend.database import get_connection
    from backend.ingestors.fred import fetch_fred_indicators
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_fred_indicators(conn, emap)
    conn.close()
    return n


def _job_fec() -> None:
    from backend.database import get_connection
    from backend.ingestors.fec import fetch_campaign_finance
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_campaign_finance(conn, emap)
    conn.close()
    return n


def _job_polygon() -> None:
    from backend.database import get_connection
    from backend.ingestors.polygon import fetch_polygon_news
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_polygon_news(conn, emap)
    conn.close()
    return n


def _job_gdelt() -> None:
    from backend.database import get_connection
    from backend.ingestors.gdelt import fetch_gdelt_events
    conn = get_connection()
    n = fetch_gdelt_events(conn)
    conn.close()
    return n


# -- New expanded data stream jobs

def _job_adsb() -> None:
    from backend.database import get_connection
    from backend.ingestors.adsb import fetch_adsb_data
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_adsb_data(conn, emap)
    conn.close()
    return n


def _job_maritime() -> None:
    from backend.database import get_connection
    from backend.ingestors.maritime import fetch_maritime_data
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_maritime_data(conn, emap)
    conn.close()
    return n


def _job_geopolitical() -> None:
    from backend.database import get_connection
    from backend.ingestors.geopolitical import fetch_geopolitical_events
    conn = get_connection()
    n = fetch_geopolitical_events(conn)
    conn.close()
    return n


def _job_satellite() -> None:
    from backend.database import get_connection
    from backend.ingestors.satellite import fetch_satellite_fires
    conn = get_connection()
    n = fetch_satellite_fires(conn)
    conn.close()
    return n


def _job_infrastructure() -> None:
    from backend.database import get_connection
    from backend.ingestors.infrastructure import fetch_infrastructure_events
    conn = get_connection()
    n = fetch_infrastructure_events(conn)
    conn.close()
    return n


def _job_prediction() -> None:
    from backend.database import get_connection
    from backend.ingestors.prediction import fetch_prediction_markets
    conn = get_connection()
    emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
    n = fetch_prediction_markets(conn, emap)
    conn.close()
    return n


def _job_telegram() -> None:
    from backend.database import get_connection
    from backend.ingestors.telegram_osint import fetch_telegram_osint
    conn = get_connection()
    n = fetch_telegram_osint(conn)
    conn.close()
    return n


def _job_enrich() -> None:
    try:
        from backend.database import get_connection
        from backend.enrichment import enrich_pending_events
        conn = get_connection()
        n = enrich_pending_events(conn, batch_size=5)
        if n > 0:
            print(f"[Scheduler/Enrich] Enriched {n} events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Enrich] Error: {exc}")


def _job_valuation() -> None:
    from backend.database import get_connection
    from backend.ingestors.valuation import run_valuation_update
    conn = get_connection()
    n = run_valuation_update(conn)
    conn.close()
    return n


def _job_onchain() -> None:
    from backend.database import get_connection
    from backend.ingestors.onchain import fetch_onchain_flows
    conn = get_connection()
    n = fetch_onchain_flows(conn)
    conn.close()
    return n


def _job_ofac() -> None:
    from backend.database import get_connection
    from backend.ingestors.ofac import fetch_ofac_actions
    conn = get_connection()
    n = fetch_ofac_actions(conn)
    conn.close()
    return n


def _job_vcflow() -> None:
    from backend.database import get_connection
    from backend.ingestors.vcflow import promote_events_to_flows
    conn = get_connection()
    n = promote_events_to_flows(conn)
    conn.close()
    return n


def _job_connections_derive() -> None:
    from backend.database import get_connection
    from backend.ingestors.connections_derive import run_connections_derive
    conn = get_connection()
    n = run_connections_derive(conn)
    conn.close()
    return n


def _wrap(name: str, fn):
    """Return a no-arg callable that runs fn inside the monitoring wrapper."""
    def _wrapped():
        _run_monitored(name, fn)
    _wrapped.__name__ = f"_monitored_{name}"
    return _wrapped


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler()

    # Financial data jobs
    _scheduler.add_job(_wrap("edgar",       _job_edgar),       trigger=IntervalTrigger(minutes=EDGAR_INTERVAL_MINUTES), id="edgar",       replace_existing=True)
    _scheduler.add_job(_wrap("rss",         _job_rss),         trigger=IntervalTrigger(minutes=RSS_INTERVAL_MINUTES),   id="rss",         replace_existing=True)
    _scheduler.add_job(_wrap("market",      _job_market),      trigger=IntervalTrigger(minutes=MARKET_INTERVAL_MINUTES), id="market",      replace_existing=True)
    _scheduler.add_job(_wrap("congress",    _job_congress),    trigger=IntervalTrigger(hours=6),                        id="congress",    replace_existing=True)
    _scheduler.add_job(_wrap("usaspending", _job_usaspending), trigger=IntervalTrigger(hours=12),                       id="usaspending", replace_existing=True)
    _scheduler.add_job(_wrap("fred",        _job_fred),        trigger=IntervalTrigger(hours=6),                        id="fred",        replace_existing=True)
    _scheduler.add_job(_wrap("fec",         _job_fec),         trigger=IntervalTrigger(hours=24),                       id="fec",         replace_existing=True)
    _scheduler.add_job(_wrap("polygon",     _job_polygon),     trigger=IntervalTrigger(minutes=30),                     id="polygon",     replace_existing=True)
    _scheduler.add_job(_wrap("gdelt",       _job_gdelt),       trigger=IntervalTrigger(hours=3),                        id="gdelt",       replace_existing=True)

    # Intelligence stream jobs
    _scheduler.add_job(_wrap("adsb",         _job_adsb),         trigger=IntervalTrigger(minutes=30), id="adsb",         replace_existing=True)
    _scheduler.add_job(_wrap("maritime",     _job_maritime),     trigger=IntervalTrigger(minutes=15), id="maritime",     replace_existing=True)
    _scheduler.add_job(_wrap("geopolitical", _job_geopolitical), trigger=IntervalTrigger(hours=6),    id="geopolitical", replace_existing=True)
    _scheduler.add_job(_wrap("satellite",    _job_satellite),    trigger=IntervalTrigger(hours=3),    id="satellite",    replace_existing=True)
    _scheduler.add_job(_wrap("infrastructure", _job_infrastructure),trigger=IntervalTrigger(minutes=15), id="infra",        replace_existing=True)
    _scheduler.add_job(_wrap("prediction",   _job_prediction),   trigger=IntervalTrigger(minutes=10), id="prediction",   replace_existing=True)
    _scheduler.add_job(_wrap("telegram",     _job_telegram),     trigger=IntervalTrigger(hours=1),    id="telegram",     replace_existing=True)

    # Enrichment always runs last (not monitored -- it's the enricher, not an ingestor)
    _scheduler.add_job(_job_enrich, trigger=IntervalTrigger(minutes=5), id="enrich", replace_existing=True)

    # Data accuracy jobs
    _scheduler.add_job(_wrap("valuation",   _job_valuation),          trigger=IntervalTrigger(hours=6), id="valuation",   replace_existing=True)
    _scheduler.add_job(_wrap("connections", _job_connections_derive),  trigger=IntervalTrigger(hours=6), id="connections", replace_existing=True)

    # Cash flow jobs
    _scheduler.add_job(_wrap("onchain", _job_onchain), trigger=IntervalTrigger(minutes=5), id="onchain", replace_existing=True)
    _scheduler.add_job(_wrap("ofac",    _job_ofac),    trigger=IntervalTrigger(hours=1),   id="ofac",    replace_existing=True)
    _scheduler.add_job(_wrap("vcflow",  _job_vcflow),  trigger=IntervalTrigger(hours=6),   id="vcflow",  replace_existing=True)

    _scheduler.start()
    print(
        "[Scheduler] Started --\n"
        "  Financial:    EDGAR(15m) RSS(10m) Market(6h) Congress(6h)"
        " USASpending(12h) FRED(6h) FEC(24h) Polygon(30m) GDELT(3h)\n"
        "  Intelligence: ADS-B(30m) Maritime(15m) Geopolitical(6h)"
        " Satellite(3h) Infra(15m) Polymarket(10m) Telegram(1h)\n"
        "  Accuracy:     Valuation(6h) Connections(6h)\n"
        "  Enrichment:   Claude enrichment(5m)\n"
        "  Cash Flow:    OnChain(5m) OFAC(1h) VCFlow(6h)"
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped")
