"""Capital Lens FastAPI application entry point."""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.config import ALLOWED_ORIGINS, HTTPS_REDIRECT

# Optional admin secret — set ADMIN_SECRET in .env to protect /admin/* routes.
# If left empty, admin routes are accessible without a secret (local dev mode).
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")

from backend.database import init_db, seed_db, seed_events, seed_countries
from backend.ingestors.connections_seed import seed_connections
from backend.routers import feed, entities, themes, search, auth, flow, geo, intel, cashflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB, seed, start scheduler. Shutdown: stop scheduler."""
    init_db()
    seed_db()
    seed_events()
    seed_countries()

    from backend.database import get_connection as _gc
    _c = _gc()
    seed_connections(_c)
    _c.close()

    from backend.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    stop_scheduler()


app = FastAPI(
    title="Capital Lens API",
    description="Real-time financial intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Attach security headers to every response. HTTPS redirect is opt-in (prod only)."""
    if HTTPS_REDIRECT and request.url.scheme == "http":
        return RedirectResponse(str(request.url).replace("http://", "https://", 1), status_code=301)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]          = "DENY"
    response.headers["X-XSS-Protection"]         = "1; mode=block"
    response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]       = "geolocation=(), microphone=(), camera=()"
    if HTTPS_REDIRECT:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    return response

app.include_router(feed.router)
app.include_router(entities.router)
app.include_router(themes.router)
app.include_router(search.router)
app.include_router(auth.router)
app.include_router(flow.router)
app.include_router(geo.router)
app.include_router(intel.router)
app.include_router(cashflow.router)


@app.get("/health")
def health() -> dict:
    from backend.database import get_connection
    conn = get_connection()
    entity_count    = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    event_count     = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    enriched_count  = conn.execute("SELECT COUNT(*) FROM events WHERE enriched_at IS NOT NULL").fetchone()[0]
    unenriched      = event_count - enriched_count
    conn.close()
    return {
        "status":    "ok",
        "entities":  entity_count,
        "events":    event_count,
        "enriched":  enriched_count,
        "pending":   unenriched,
    }


def _check_admin(x_admin_secret: str | None) -> None:
    """Raise 403 if ADMIN_SECRET is set and the header doesn't match."""
    if ADMIN_SECRET and x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Admin-Secret header")


@app.post("/admin/enrich")
def admin_enrich(
    background_tasks: BackgroundTasks,
    x_admin_secret: str | None = Header(default=None),
) -> dict:
    """Enrich all pending events in the background. Protected by ADMIN_SECRET if set."""
    _check_admin(x_admin_secret)
    def _run():
        from backend.database import get_connection
        from backend.enrichment import enrich_all_pending
        conn = get_connection()
        n = enrich_all_pending(conn)
        conn.close()
        print(f"[Admin] Enriched {n} events")
    background_tasks.add_task(_run)
    return {"status": "started", "message": "Enrichment running in background — refresh the feed in ~30 seconds"}


@app.post("/admin/ingest")
def admin_ingest(
    background_tasks: BackgroundTasks,
    x_admin_secret: str | None = Header(default=None),
) -> dict:
    """Run all ingestors in the background. Protected by ADMIN_SECRET if set."""
    _check_admin(x_admin_secret)
    def _run():
        from backend.database import get_connection
        from backend.ingestors.edgar import run_edgar_sync
        from backend.ingestors.news_rss import fetch_rss_news
        from backend.ingestors.congress import fetch_congressional_trades
        from backend.ingestors.usaspending import fetch_federal_contracts
        from backend.ingestors.fred import fetch_fred_indicators
        from backend.ingestors.fec import fetch_campaign_finance
        from backend.ingestors.polygon import fetch_polygon_news
        conn = get_connection()
        emap = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM entities").fetchall()}
        n_edgar       = run_edgar_sync(conn, emap)
        n_rss         = fetch_rss_news(conn, emap)
        n_congress    = fetch_congressional_trades(conn, emap)
        n_usaspending = fetch_federal_contracts(conn, emap)
        n_fred        = fetch_fred_indicators(conn, emap)
        n_fec         = fetch_campaign_finance(conn, emap)
        n_polygon     = fetch_polygon_news(conn, emap)
        conn.close()
        print(
            f"[Admin] Ingested {n_edgar} EDGAR + {n_rss} RSS + {n_congress} congressional + "
            f"{n_usaspending} contracts + {n_fred} FRED + {n_fec} FEC + {n_polygon} Polygon"
        )
    background_tasks.add_task(_run)
    return {
        "status": "started",
        "message": (
            "Ingesting from all sources: EDGAR, Reuters RSS, congressional trades, "
            "USA Spending contracts, FRED macro indicators, FEC campaign finance, "
            "and Polygon news. Check /health for new events in ~15 seconds."
        ),
    }


@app.post("/admin/promote")
def admin_promote(
    body: dict,
    x_admin_secret: str | None = Header(default=None),
) -> dict:
    """Set any user's tier. Body: {email, tier} where tier is free/pro/admin."""
    _check_admin(x_admin_secret)
    email = body.get("email", "").strip().lower()
    tier  = body.get("tier", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    if tier not in ("free", "pro", "admin"):
        raise HTTPException(status_code=400, detail="tier must be free, pro, or admin")

    from backend.database import get_connection
    conn = get_connection()
    row = conn.execute("SELECT id FROM users WHERE LOWER(email)=?", (email,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No user found with email {email}")
    conn.execute("UPDATE users SET tier=? WHERE LOWER(email)=?", (tier, email))
    conn.commit()
    conn.close()
    return {"status": "ok", "email": email, "tier": tier}
