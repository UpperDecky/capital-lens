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


def _job_edgar() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.edgar import run_edgar_sync
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = run_edgar_sync(conn, emap)
        print(f"[Scheduler/EDGAR] Inserted {n} new events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/EDGAR] Error: {exc}")


def _job_rss() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.news_rss import fetch_rss_news
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_rss_news(conn, emap)
        print(f"[Scheduler/RSS] Inserted {n} new news events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/RSS] Error: {exc}")


def _job_market() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.market import fetch_market_prices
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        prices = fetch_market_prices(conn, emap)
        print(f"[Scheduler/Market] Updated {prices} entity prices")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Market] Error: {exc}")


def _job_congress() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.congress import fetch_congressional_trades
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_congressional_trades(conn, emap)
        print(f"[Scheduler/Congress] Inserted {n} new trades")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Congress] Error: {exc}")


def _job_usaspending() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.usaspending import fetch_federal_contracts
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_federal_contracts(conn, emap)
        print(f"[Scheduler/USASpending] Inserted {n} new contract events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/USASpending] Error: {exc}")


def _job_fred() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.fred import fetch_fred_indicators
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_fred_indicators(conn, emap)
        print(f"[Scheduler/FRED] Inserted {n} new macro events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/FRED] Error: {exc}")


def _job_fec() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.fec import fetch_campaign_finance
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_campaign_finance(conn, emap)
        print(f"[Scheduler/FEC] Inserted {n} new campaign finance events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/FEC] Error: {exc}")


def _job_polygon() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.polygon import fetch_polygon_news
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_polygon_news(conn, emap)
        if n > 0:
            print(f"[Scheduler/Polygon] Inserted {n} new news events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Polygon] Error: {exc}")


def _job_gdelt() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.gdelt import fetch_gdelt_events
        conn = get_connection()
        n = fetch_gdelt_events(conn)
        if n > 0:
            print(f"[Scheduler/GDELT] Inserted {n} new geo events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/GDELT] Error: {exc}")


# ── New expanded data stream jobs ─────────────────────────────────────────────

def _job_adsb() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.adsb import fetch_adsb_data
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_adsb_data(conn, emap)
        if n > 0:
            print(f"[Scheduler/ADS-B] Stored {n} new aircraft snapshots")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/ADS-B] Error: {exc}")


def _job_maritime() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.maritime import fetch_maritime_data
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_maritime_data(conn, emap)
        if n > 0:
            print(f"[Scheduler/Maritime] Stored {n} new vessel snapshots")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Maritime] Error: {exc}")


def _job_geopolitical() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.geopolitical import fetch_geopolitical_events
        conn = get_connection()
        n = fetch_geopolitical_events(conn)
        if n > 0:
            print(f"[Scheduler/Geopolitical] Inserted {n} new conflict events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Geopolitical] Error: {exc}")


def _job_satellite() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.satellite import fetch_satellite_fires
        conn = get_connection()
        n = fetch_satellite_fires(conn)
        if n > 0:
            print(f"[Scheduler/Satellite] Stored {n} new fire detections")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Satellite] Error: {exc}")


def _job_infrastructure() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.infrastructure import fetch_infrastructure_events
        conn = get_connection()
        n = fetch_infrastructure_events(conn)
        if n > 0:
            print(f"[Scheduler/Infra] Stored {n} new outage events")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Infra] Error: {exc}")


def _job_prediction() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.prediction import fetch_prediction_markets
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n = fetch_prediction_markets(conn, emap)
        if n > 0:
            print(f"[Scheduler/Polymarket] {n} new prediction markets ingested")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Polymarket] Error: {exc}")


def _job_telegram() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.telegram_osint import fetch_telegram_osint
        conn = get_connection()
        n = fetch_telegram_osint(conn)
        if n > 0:
            print(f"[Scheduler/Telegram] Stored {n} new OSINT messages")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Telegram] Error: {exc}")


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
    try:
        from backend.database import get_connection
        from backend.ingestors.valuation import run_valuation_update
        conn = get_connection()
        n = run_valuation_update(conn)
        if n > 0:
            print(f"[Scheduler/Valuation] Updated {n} entity valuations")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Valuation] Error: {exc}")


def _job_onchain() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.onchain import fetch_onchain_flows
        conn = get_connection()
        n = fetch_onchain_flows(conn)
        if n > 0:
            print(f"[Scheduler/OnChain] Stored {n} new whale transactions")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/OnChain] Error: {exc}")


def _job_ofac() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.ofac import fetch_ofac_actions
        conn = get_connection()
        n = fetch_ofac_actions(conn)
        if n > 0:
            print(f"[Scheduler/OFAC] Stored {n} new sanction/seizure flows")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/OFAC] Error: {exc}")


def _job_vcflow() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.vcflow import promote_events_to_flows
        conn = get_connection()
        n = promote_events_to_flows(conn)
        if n > 0:
            print(f"[Scheduler/VCFlow] Promoted {n} events to cash flows")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/VCFlow] Error: {exc}")


def _job_connections_derive() -> None:
    try:
        from backend.database import get_connection
        from backend.ingestors.connections_derive import run_connections_derive
        conn = get_connection()
        n = run_connections_derive(conn)
        if n > 0:
            print(f"[Scheduler/Connections] Derived {n} new connections")
        conn.close()
    except Exception as exc:
        print(f"[Scheduler/Connections] Error: {exc}")


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler()

    # Original financial data jobs
    _scheduler.add_job(_job_edgar,       trigger=IntervalTrigger(minutes=EDGAR_INTERVAL_MINUTES), id="edgar",       replace_existing=True)
    _scheduler.add_job(_job_rss,         trigger=IntervalTrigger(minutes=RSS_INTERVAL_MINUTES),   id="rss",         replace_existing=True)
    _scheduler.add_job(_job_market,      trigger=IntervalTrigger(minutes=MARKET_INTERVAL_MINUTES), id="market",      replace_existing=True)
    _scheduler.add_job(_job_congress,    trigger=IntervalTrigger(hours=6),                        id="congress",    replace_existing=True)
    _scheduler.add_job(_job_usaspending, trigger=IntervalTrigger(hours=12),                       id="usaspending", replace_existing=True)
    _scheduler.add_job(_job_fred,        trigger=IntervalTrigger(hours=6),                        id="fred",        replace_existing=True)
    _scheduler.add_job(_job_fec,         trigger=IntervalTrigger(hours=24),                       id="fec",         replace_existing=True)
    _scheduler.add_job(_job_polygon,     trigger=IntervalTrigger(minutes=30),                     id="polygon",     replace_existing=True)
    _scheduler.add_job(_job_gdelt,       trigger=IntervalTrigger(hours=3),                        id="gdelt",       replace_existing=True)

    # New expanded intelligence stream jobs
    _scheduler.add_job(_job_adsb,          trigger=IntervalTrigger(minutes=30), id="adsb",         replace_existing=True)
    _scheduler.add_job(_job_maritime,      trigger=IntervalTrigger(minutes=15), id="maritime",     replace_existing=True)
    _scheduler.add_job(_job_geopolitical,  trigger=IntervalTrigger(hours=6),    id="geopolitical", replace_existing=True)
    _scheduler.add_job(_job_satellite,     trigger=IntervalTrigger(hours=3),    id="satellite",    replace_existing=True)
    _scheduler.add_job(_job_infrastructure,trigger=IntervalTrigger(minutes=15), id="infra",        replace_existing=True)
    _scheduler.add_job(_job_prediction,    trigger=IntervalTrigger(minutes=10), id="prediction",   replace_existing=True)
    _scheduler.add_job(_job_telegram,      trigger=IntervalTrigger(hours=1),    id="telegram",     replace_existing=True)

    # Enrichment always runs last
    _scheduler.add_job(_job_enrich, trigger=IntervalTrigger(minutes=5), id="enrich", replace_existing=True)

    # Data accuracy jobs
    _scheduler.add_job(_job_valuation,          trigger=IntervalTrigger(hours=6),  id="valuation",    replace_existing=True)
    _scheduler.add_job(_job_connections_derive, trigger=IntervalTrigger(hours=6),  id="connections",  replace_existing=True)

    # Cash flow jobs
    _scheduler.add_job(_job_onchain, trigger=IntervalTrigger(minutes=5),  id="onchain", replace_existing=True)
    _scheduler.add_job(_job_ofac,    trigger=IntervalTrigger(hours=1),    id="ofac",    replace_existing=True)
    _scheduler.add_job(_job_vcflow,  trigger=IntervalTrigger(hours=6),    id="vcflow",  replace_existing=True)

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
