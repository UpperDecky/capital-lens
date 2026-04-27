# Capital Lens — Project Roadmap

Current version: **v2.0**
Last updated: **2026-04-26**

---

## Completed (v1.0 — v2.0)

### Core Platform
- [x] FastAPI backend with SQLite (10-table schema)
- [x] React 18 + Vite + Tailwind CSS frontend
- [x] APScheduler background job system (17 jobs)
- [x] JWT authentication with configurable expiry
- [x] TOTP MFA (Google Authenticator) with QR code setup
- [x] Backup codes (8 x bcrypt-hashed one-time codes)
- [x] Scope-restricted pending tokens for MFA two-step login
- [x] Tier system: free / pro / admin
- [x] Admin bypass for all rate limits and page caps
- [x] Security headers on all responses
- [x] HTTPS redirect support for production

### Data Ingestors
- [x] SEC EDGAR (13F, 4, 8-K, 10-K, DEF 14A)
- [x] Reuters/AP/Bloomberg RSS (117 feeds)
- [x] Congressional stock trades (House + Senate)
- [x] Federal contracts (USASpending.gov)
- [x] Campaign finance (FEC)
- [x] FRED macroeconomic indicators
- [x] Polygon.io financial news
- [x] GDELT geopolitical events
- [x] ADS-B aircraft (OpenSky Network)
- [x] Maritime vessels (aisstream.io AIS)
- [x] Geopolitical conflicts (ACLED + UCDP)
- [x] Satellite fire detection (NASA FIRMS)
- [x] Infrastructure outages (Cloudflare Radar)
- [x] Prediction markets (Polymarket)
- [x] Telegram OSINT (configurable channels)
- [x] Market prices (Twelve Data + CoinGecko)
- [x] Entity connection seeding (43 seeded entities)

### World Intelligence Map
- [x] D3 Natural Earth choropleth (conflict + political lean modes)
- [x] Conflict event pins (ACLED/UCDP/GDELT, up to 1,000)
- [x] ADS-B aircraft overlay (up to 2,000)
- [x] Maritime vessel overlay (up to 1,000)
- [x] Satellite fire overlay (up to 2,000)
- [x] Entity overlay — entities pinned to capital cities by sector
- [x] Landmark overlay — 25 strategic locations (chokepoints, bases, exchanges)
- [x] Infrastructure overlay — outage events pinned by country
- [x] Tabbed live ticker (All / Geo / Infra / Markets)
- [x] Country detail panel with alliances, leadership, live news, prediction markets
- [x] Pulse animation rings for recent events
- [x] Zoom/pan (1–8x), double-click to reset

### AI Enrichment
- [x] OpenRouter integration (Claude via free tier models)
- [x] Plain-English summaries, market impact, investment signals
- [x] Importance scoring (1–5)
- [x] Sector tags (JSON array per event)
- [x] Extended analysis JSON (relationships, affected sectors, timeline)
- [x] Scheduler-only enrichment (never in HTTP routes)

### Frontend Pages
- [x] Feed — paginated event stream with sector/type/amount/date filters
- [x] Entities — company and individual profiles
- [x] Entity Profile — events, portfolio, price chart
- [x] Flow Map — entity connection graph (D3 force layout)
- [x] World Map — full intelligence overlay map
- [x] Search — full-text event and entity search
- [x] Watchlist — saved entities
- [x] Cash Flow — cash flow analysis view
- [x] Settings — MFA setup/disable, account management
- [x] Login — split-panel auth with MFA challenge flow
- [x] Legal pages — Disclaimer, Terms, Privacy, Risk Warning

---

## In Progress / Near-Term (v2.1)

### Map Enhancements
- [ ] Cluster mode for entity/infra pins at high density
- [ ] Search-to-map: clicking a search result zooms the map to that country
- [ ] Time-slider to replay events over a configurable window
- [ ] Export map state as PNG

### Feed Improvements
- [ ] Real-time WebSocket push for new events (remove polling)
- [ ] "Breaking" banner for importance-5 events
- [ ] Saved filters / filter presets per user
- [ ] Feed sharing — shareable URL that encodes current filters

### Alerts System
- [ ] User-defined watchlist alerts (email or in-app notification)
- [ ] Threshold alerts (e.g., entity amount > $X, importance >= 4)
- [ ] Geopolitical escalation alerts (country conflict status change)

### Entity Graph
- [ ] Richer connection data — board memberships, subsidiary relationships
- [ ] Click-through from flow map node to entity profile
- [ ] Export graph as SVG/PNG

---

## Medium-Term (v3.0)

### Portfolio & Investment Tools
- [ ] Portfolio tracker — link entities to positions with cost basis
- [ ] P&L overlay on event timeline (what happened when)
- [ ] Sector exposure heatmap
- [ ] Correlation matrix between entity event frequency and price moves

### Advanced Intelligence
- [ ] Narrative clustering — group related events across sources into "stories"
- [ ] Entity sentiment timeline — aggregate tone score over time
- [ ] Cross-source signal detection (same event appearing in 3+ sources = high confidence)
- [ ] Geopolitical risk score per country (composite index)

### Additional Data Sources
- [ ] Patent filings (USPTO) for R&D intelligence
- [ ] Job postings (LinkedIn/Indeed scrape) for hiring signal
- [ ] Earnings call transcripts — sentiment and key phrase extraction
- [ ] Satellite imagery change detection (commercial API)
- [ ] Dark web mention monitoring (opt-in, legal jurisdictions only)

### Collaboration
- [ ] Multi-user workspaces — shared watchlists and annotations
- [ ] Event annotations — pin notes to specific events
- [ ] Team digest — daily summary email to all workspace members

---

## Long-Term (v4.0+)

### Autonomous Intelligence Agent
- [ ] Proactive agent that monitors for user-defined scenarios
- [ ] Scenario modelling — "if X happens, what are the second-order effects?"
- [ ] Automated briefing generation (daily/weekly PDF report)
- [ ] Natural language query interface — ask questions about the feed

### Deployment & Scale
- [ ] PostgreSQL migration path (replace SQLite for multi-user deployments)
- [ ] Docker Compose one-click deploy
- [ ] Optional cloud sync mode (encrypted backup of local DB)
- [ ] Public SaaS tier with managed hosting

### Compliance & Audit
- [ ] SOC2-style audit log export
- [ ] GDPR data export and deletion tools
- [ ] Role-based access control (RBAC) within workspaces
- [ ] MFA enforcement policy per workspace

---

## Known Issues / Technical Debt

| Priority | Issue | Notes |
|----------|-------|-------|
| High | WebSocket push vs. polling | Feed currently polls every 30s; WebSocket would reduce latency and server load |
| Medium | SQLite concurrency ceiling | Fine for single-user; PostgreSQL needed for team deployments |
| Medium | Entity location inference | Entity map pins use name-based country matching; a dedicated `hq_country` field would be more accurate |
| Medium | Enrichment rate on free tier | ~18 events/hour on OpenRouter free models; pro key unlocks ~10x throughput |
| Low | ADS-B coverage gaps | OpenSky has regional blind spots; ADS-B Exchange API is an alternative |
| Low | GDELT deduplication | GDELT can return the same event under multiple themes; similarity hashing needed |
| Low | Maritime data freshness | aisstream.io WebSocket session resets after 24h; reconnect logic is fragile |

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| v1.0 | 2026-04-24 | Initial platform — feed, entities, flow map, auth, basic world map |
| v2.0 | 2026-04-26 | MFA, admin tier, world map overhaul (landmarks, entities, infra, tabbed ticker), full scheduler expansion |
