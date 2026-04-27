# Capital Lens

**Self-hosted financial and geopolitical intelligence platform.**

Fuses SEC filings, congressional trades, campaign finance, federal contracts, macroeconomic indicators, geopolitical conflicts, aircraft tracking, maritime vessel tracking, satellite fire detection, infrastructure outages, and prediction markets into a single AI-enriched real-time feed.

---

## What It Does

Every data source ingested by Capital Lens is enriched by Claude (via OpenRouter) to produce:
- **Plain-English summary** — what happened, explained simply
- **Market impact** — which industries and asset classes are affected
- **Investment signal** — actionable implications for investors
- **Personal takeaway** — why it matters to you
- **Importance score** — 1–5 scale, 5 = market-moving event

All enrichment runs in the background on a scheduler. No enrichment happens inside HTTP routes.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI 0.111, SQLite3 |
| Scheduler | APScheduler 3.10.4 (17 jobs) |
| AI Enrichment | Claude via OpenRouter (free tier compatible) |
| Auth | JWT (python-jose) + TOTP MFA (pyotp) + bcrypt |
| Frontend | React 18, Vite, Tailwind CSS |
| Mapping | D3.js v7, TopoJSON, world-atlas |
| Charts | Recharts |

---

## Features

### Intelligence Feed
- Real-time event stream with filters (sector, type, amount, date, importance)
- SEC EDGAR filings (13F, 4, 8-K, 10-K, DEF 14A)
- Congressional stock trades (House + Senate disclosures)
- Campaign finance (FEC PAC contributions)
- Federal contracts (USASpending.gov)
- FRED macroeconomic indicators (Fed rate, CPI, unemployment, GDP)
- Reuters/AP/Bloomberg RSS (117 feeds)
- Polygon.io financial news

### World Intelligence Map
- D3 Natural Earth choropleth — conflict status or political lean mode
- **Conflict pins** — ACLED + UCDP + GDELT geolocated events (up to 1,000, 14-day window)
- **Aircraft overlay** — ADS-B live positions via OpenSky (up to 2,000)
- **Maritime overlay** — AIS vessel positions via aisstream.io (up to 1,000)
- **Satellite fires** — NASA FIRMS thermal anomalies (up to 2,000, 7-day)
- **Entity overlay** — all tracked entities pinned to capital cities by sector
- **Landmarks overlay** — 25 strategic locations (chokepoints, military bases, exchanges, diplomatic hubs)
- **Infrastructure overlay** — Cloudflare Radar outage events
- Tabbed live ticker: All / Geo / Infra / Markets
- Country detail panel with conflict status, leadership, alliances, live news, prediction markets, and entity events

### Entity Profiles
- Company and individual profiles with net worth, sector, type
- Portfolio view: all events linked to the entity
- Price chart (Twelve Data + CoinGecko)
- Entity connection graph (Flow Map)

### Prediction Markets
- Polymarket real-time market data (yes/no prices, volume)
- Linked to relevant entities
- Visible in map ticker and country detail panels

### Telegram OSINT
- Monitors configurable Telegram channels for geopolitical signals
- Ingested as geo_events with iso2 tagging

### Authentication & Security
- JWT-based auth with configurable expiry
- TOTP MFA (Google Authenticator compatible) with QR code setup
- 8 one-time backup codes (bcrypt-hashed, consumed on use)
- Scope-restricted pending tokens for MFA two-step flow
- Security headers on every response (CSP, X-Frame-Options, HSTS in prod)
- Tier system: free / pro / admin

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Clone and configure

```bash
git clone https://github.com/UpperDecky/capital-lens.git
cd capital-lens
cp .env.example .env
# Edit .env with your API keys (see API Keys section below)
```

### 2. Start the backend

```powershell
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

The database is created automatically on first run and seeded with 43 entities and 50 countries.

### 3. Start the frontend

```powershell
cd frontend
npm install --legacy-peer-deps
npm run dev
```

### 4. Open the app

| URL | Description |
|-----|-------------|
| http://localhost:5173 | Frontend |
| http://localhost:8000/docs | API docs (Swagger) |
| http://localhost:8000/health | Health check |

Register an account, then start ingesting data via the admin endpoints.

---

## API Keys

All keys are optional — the platform degrades gracefully when keys are missing. Free-tier keys are available for all services marked with a link.

| Key | Service | Required For |
|-----|---------|-------------|
| `OPENROUTER_API_KEY` | [OpenRouter](https://openrouter.ai) | AI enrichment (plain-English summaries) |
| `TWELVE_DATA_API_KEY` | [Twelve Data](https://twelvedata.com) | Stock price charts |
| `POLYGON_API_KEY` | [Polygon.io](https://polygon.io) | Financial news |
| `FRED_API_KEY` | [FRED](https://fred.stlouisfed.org/docs/api/) | Macro indicators |
| `FEC_API_KEY` | [FEC](https://api.open.fec.gov/developers/) | Campaign finance |
| `AISSTREAM_API_KEY` | [aisstream.io](https://aisstream.io) | Maritime vessel tracking |
| `NASA_FIRMS_MAP_KEY` | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) | Satellite fire detection |
| `ACLED_EMAIL` + `ACLED_KEY` | [ACLED](https://acleddata.com) | Conflict event data |
| `CLOUDFLARE_API_TOKEN` | [Cloudflare](https://dash.cloudflare.com) | Infrastructure outage tracking |
| `TELEGRAM_API_ID/HASH/SESSION` | [my.telegram.org](https://my.telegram.org) | Telegram OSINT |
| `OPENSKY_USER` + `OPENSKY_PASS` | [OpenSky](https://opensky-network.org) | Higher ADS-B rate limits |

---

## Admin Endpoints

Protected by `X-Admin-Secret` header (set `ADMIN_SECRET` in `.env`; leave blank for local dev).

```bash
# Trigger AI enrichment of pending events
curl -X POST http://localhost:8000/admin/enrich

# Run all data ingestors immediately
curl -X POST http://localhost:8000/admin/ingest

# Promote a user's tier
curl -X POST http://localhost:8000/admin/promote \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "tier": "pro"}'
```

---

## Telegram OSINT Setup

One-time setup to generate a session string:

```powershell
python -m backend.ingestors.telegram_osint --setup
```

Copy the printed session string into `TELEGRAM_SESSION` in your `.env`.

---

## Scheduler Jobs

17 background jobs run automatically after startup:

| Source | Interval | Key Required |
|--------|----------|-------------|
| SEC EDGAR | 15 min | No |
| RSS (117 feeds) | 10 min | No |
| Congressional trades | 6 h | No |
| USA Spending contracts | 12 h | No |
| GDELT geopolitical | 3 h | No |
| ADS-B aircraft | 30 min | No (optional OpenSky creds) |
| Prediction markets | 10 min | No |
| Polygon news | 30 min | POLYGON_API_KEY |
| Market prices | 6 h | TWELVE_DATA_API_KEY |
| FRED macro | 6 h | FRED_API_KEY |
| FEC campaign finance | 24 h | FEC_API_KEY |
| Maritime vessels | 15 min | AISSTREAM_API_KEY |
| Geopolitical (ACLED/UCDP) | 6 h | ACLED_EMAIL + ACLED_KEY |
| Satellite fires | 3 h | NASA_FIRMS_MAP_KEY |
| Infrastructure outages | 15 min | CLOUDFLARE_API_TOKEN |
| Telegram OSINT | 1 h | TELEGRAM credentials |
| AI Enrichment | 5 min | OPENROUTER_API_KEY |

---

## Environment Variables

```env
# AI enrichment
OPENROUTER_API_KEY=

# Auth
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRY_DAYS=7

# CORS / deployment
ALLOWED_ORIGINS=http://localhost:5173
HTTPS_REDIRECT=false

# Admin protection
ADMIN_SECRET=

# Data sources (all optional)
TWELVE_DATA_API_KEY=
POLYGON_API_KEY=
FRED_API_KEY=
FEC_API_KEY=
AISSTREAM_API_KEY=
NASA_FIRMS_MAP_KEY=
ACLED_EMAIL=
ACLED_KEY=
CLOUDFLARE_API_TOKEN=
OPENSKY_USER=
OPENSKY_PASS=
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_SESSION=
```

---

## Project Structure

```
capital-lens/
├── backend/
│   ├── main.py              # FastAPI app + lifespan
│   ├── database.py          # Schema (10 tables), init, seed
│   ├── config.py            # All env vars
│   ├── enrichment.py        # Claude enrichment (scheduler only)
│   ├── scheduler.py         # 17 APScheduler jobs
│   ├── models/              # Pydantic models
│   ├── routers/             # API route handlers
│   │   ├── auth.py          # JWT + MFA
│   │   ├── feed.py          # Event feed
│   │   ├── entities.py      # Entity profiles
│   │   ├── geo.py           # World map + intelligence
│   │   ├── flow.py          # Entity connection graph
│   │   ├── search.py        # Full-text search
│   │   ├── intel.py         # Intelligence reports
│   │   └── cashflow.py      # Cash flow analysis
│   ├── ingestors/           # 17 data source ingestors
│   ├── middleware/          # Tier tracking, rate limiting
│   └── services/            # Audit logging, compliance, analytics
├── frontend/
│   └── src/
│       ├── App.jsx           # Router with auth guards
│       ├── pages/            # Feed, GeoMap, Entities, FlowMap, etc.
│       ├── components/       # EventCard, NavBar, PriceChart, etc.
│       ├── hooks/            # useAuth, useAlerts
│       └── lib/              # api.js, format.js
├── .env.example
├── requirements.txt
└── CLAUDE.md                 # Development guidelines
```

---

## License

Private — all rights reserved. Not licensed for redistribution or commercial use.
