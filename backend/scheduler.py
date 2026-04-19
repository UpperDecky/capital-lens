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
        print(f"[Scheduler/Market] Fetched prices for {len(prices)} entities")
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


def start_scheduler() -> None:
    global _scheduler
    _scheduler = BackgroundScheduler()

    _scheduler.add_job(_job_edgar,       trigger=IntervalTrigger(minutes=EDGAR_INTERVAL_MINUTES), id="edgar",       replace_existing=True)
    _scheduler.add_job(_job_rss,         trigger=IntervalTrigger(minutes=RSS_INTERVAL_MINUTES),   id="rss",         replace_existing=True)
    _scheduler.add_job(_job_market,      trigger=IntervalTrigger(hours=24),                       id="market",      replace_existing=True)
    _scheduler.add_job(_job_congress,    trigger=IntervalTrigger(hours=6),                        id="congress",    replace_existing=True)
    _scheduler.add_job(_job_usaspending, trigger=IntervalTrigger(hours=12),                       id="usaspending", replace_existing=True)
    _scheduler.add_job(_job_fred,        trigger=IntervalTrigger(hours=6),                        id="fred",        replace_existing=True)
    _scheduler.add_job(_job_fec,         trigger=IntervalTrigger(hours=24),                       id="fec",         replace_existing=True)
    _scheduler.add_job(_job_polygon,     trigger=IntervalTrigger(minutes=30),                     id="polygon",     replace_existing=True)
    _scheduler.add_job(_job_enrich,      trigger=IntervalTrigger(minutes=5),                      id="enrich",      replace_existing=True)

    _scheduler.start()
    print(
        "[Scheduler] Started -- EDGAR(15m), RSS(10m), Market(24h), Congress(6h), "
        "USASpending(12h), FRED(6h), FEC(24h), Polygon(30m), Enrich(5m)"
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped")
