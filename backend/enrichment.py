"""
Capital Lens — AI enrichment via OpenRouter.
Called ONLY from the background scheduler, never on individual HTTP requests.

OpenRouter is an aggregator that routes to free and paid models automatically.
We send a `models` array so it tries each in order and falls back on rate-limit/error.
Sign up free at https://openrouter.ai — no credit card required for the free tier.
"""
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

from openai import OpenAI, RateLimitError, APIError

from backend.config import OPENROUTER_API_KEY

# ── Model priority lists ─────────────────────────────────────────────────────
# All IDs verified against this account's available free models.
# We iterate these ourselves — OpenRouter's `route: fallback` doesn't trigger
# on rate-limit responses for free models, only on hard errors.
#
# Core enrichment: biggest/smartest models first for best plain-English quality.
# `openrouter/free` is OpenRouter's own auto-router — it picks whichever model
# has live capacity at that moment, making it the most reliable free option.
# Small models (3B-4B) are last-resort fallbacks; rarely congested.
# Credits unlocked — best quality models now available with proper rate limits.
CORE_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",  # 405B — highest quality
    "meta-llama/llama-3.3-70b-instruct:free",     # 70B — excellent fallback
    "openrouter/free",                             # Auto-router if above are busy
]

ANALYSIS_MODELS = [
    "qwen/qwen3-coder:free",                      # Best at strict JSON output
    "openai/gpt-oss-20b:free",                    # Fast GPT OSS
    "openrouter/free",                             # Auto-router fallback
]

# ── System prompt (exact spec — do not modify) ───────────────────────────────
SYSTEM_PROMPT = (
    "You are a financial intelligence engine. Your job is to take raw financial events "
    "and return structured JSON that any person — including someone with no financial "
    "background — can understand. Never use jargon without explaining it. Be precise. "
    "Be brief. Return ONLY valid JSON, no preamble, no markdown fences."
)

# ── Core enrichment prompt (exact spec) ─────────────────────────────────────
USER_PROMPT_TEMPLATE = (
    "Entity: {entity_name} ({entity_type}, {sector}) | "
    "Event: {headline} | "
    "Amount: {amount} {currency} | "
    "Source: {source_name} | "
    "Date: {occurred_at}\n\n"
    "Return JSON with exactly these keys:\n"
    '{{"plain_english": "One sentence, 12-year-old level, no jargon", '
    '"market_impact": "Two sentences, what this does to surrounding industries and why", '
    '"invest_signal": "Two sentences, what this signals for investors, name adjacent plays", '
    '"for_you": "Two sentences, direct personal takeaway specific to this event", '
    '"sector_tags": ["tag1","tag2","tag3"], '
    '"importance": <integer 1-5 — '
    '5=market-moving (>$10B deal/acquisition, major earnings beat/miss, government action affecting whole sector), '
    '4=significant (>$1B deal, large insider trade, major gov contract, congressional stock trade), '
    '3=notable (>$100M, routine earnings with disclosures, noteworthy news), '
    '2=minor (small amounts, routine quarterly filings), '
    '1=minimal (admin filings, tiny trades under $50k)>}}'
)

# ── Extended analysis prompt ─────────────────────────────────────────────────
ANALYSIS_PROMPT_TEMPLATE = (
    "Entity: {entity_name} ({entity_type}, {sector}) | "
    "Event: {headline} | "
    "Amount: {amount} {currency} | "
    "Date: {occurred_at}\n\n"
    "Return a JSON object with exactly these keys:\n"
    '"relationships": array of up to 4 objects, each: {{"entity": "name", '
    '"relationship": "one sentence how they connect to {entity_name}", '
    '"direction": "supplier|customer|competitor|partner|investor|subsidiary"}}.\n'
    '"affected_sectors": array of up to 4 objects, each: {{"sector": "name", '
    '"impact": "positive|negative|neutral", "reason": "one sentence why", '
    '"timeframe": "immediate|short_term|medium_term|long_term"}}.\n'
    '"timeline": array of exactly 3 objects for short/medium/long-term consequences, each: '
    '{{"period": "human label e.g. 2-4 weeks", "event": "what will likely happen", '
    '"likelihood": "high|medium|low"}}.\n'
    '"context": "one paragraph (3-5 sentences) explaining the broader strategic significance".\n'
    "Return ONLY valid JSON."
)


def _format_amount(amount: Optional[float], currency: str) -> str:
    if amount is None:
        return "N/A"
    if amount >= 1e12:
        return f"${amount/1e12:.2f}T"
    if amount >= 1e9:
        return f"${amount/1e9:.1f}B"
    if amount >= 1e6:
        return f"${amount/1e6:.0f}M"
    return f"${amount:,.0f}"


def _get_client() -> Optional[OpenAI]:
    """Return an OpenRouter-backed OpenAI client, or None if no key is set."""
    if not OPENROUTER_API_KEY:
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "https://capital-lens.local",
            "X-Title": "Capital Lens",
        },
    )


def _call_openrouter(
    system: str,
    user: str,
    models: list[str],
    max_tokens: int = 700,
) -> Optional[str]:
    """
    Try each model in order, moving immediately to the next on rate-limit.
    OpenRouter's own `route: fallback` only triggers on hard errors, not 429s,
    so we manage the fallback loop ourselves.
    Returns raw text content, or None if every model fails.
    """
    client = _get_client()
    if client is None:
        print("[Enrichment] OPENROUTER_API_KEY not set — skipping.")
        return None

    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]

    for model in models:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,
            )
            raw = (response.choices[0].message.content or "").strip()
            # Strip markdown fences if the model wraps output anyway
            if raw.startswith("```"):
                raw = "\n".join(raw.split("\n")[1:])
                raw = raw.rstrip("`").rstrip()
            print(f"[Enrichment] Used model: {model.split('/')[-1]}")
            return raw

        except RateLimitError:
            print(f"[Enrichment] {model.split('/')[-1]} rate limited — trying next model")
            time.sleep(2)   # brief pause before next model
            continue

        except APIError as exc:
            # 400/422 = bad request (won't get better by retrying), skip model
            # 5xx = transient, worth one retry on next model
            print(f"[Enrichment] {model.split('/')[-1]} error: {str(exc)[:80]} — trying next model")
            time.sleep(1)
            continue

        except Exception as exc:
            print(f"[Enrichment] Unexpected error with {model.split('/')[-1]}: {exc}")
            continue

    print("[Enrichment] All models exhausted — enrichment skipped for this event")
    return None


def _parse_json(raw: Optional[str], event_id: str, label: str) -> Optional[dict]:
    """Parse raw JSON string with helpful error logging."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting a JSON object if there's surrounding text
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        print(f"[Enrichment] {label} JSON parse failed for event {event_id}. Raw:\n{raw[:200]}")
        return None


# ── Public API ───────────────────────────────────────────────────────────────

def enrich_event(
    event: dict[str, Any],
    entity: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Generate core enrichment (plain_english, market_impact, invest_signal,
    for_you, sector_tags) for a single event via OpenRouter.
    """
    user_msg = USER_PROMPT_TEMPLATE.format(
        entity_name=entity["name"],
        entity_type=entity["type"],
        sector=entity["sector"],
        headline=event["headline"],
        amount=_format_amount(event.get("amount"), event.get("currency", "USD")),
        currency=event.get("currency", "USD"),
        source_name=event.get("source_name") or "Unknown",
        occurred_at=event.get("occurred_at") or "Unknown",
    )
    raw = _call_openrouter(SYSTEM_PROMPT, user_msg, CORE_MODELS, max_tokens=1200)
    return _parse_json(raw, event.get("id", "?"), "core")


def enrich_analysis(
    event: dict[str, Any],
    entity: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """
    Generate deep analysis (relationships, affected_sectors, timeline, context)
    for a single event. Called only from the scheduler.
    """
    user_msg = ANALYSIS_PROMPT_TEMPLATE.format(
        entity_name=entity["name"],
        entity_type=entity["type"],
        sector=entity["sector"],
        headline=event["headline"],
        amount=_format_amount(event.get("amount"), event.get("currency", "USD")),
        currency=event.get("currency", "USD"),
        occurred_at=event.get("occurred_at") or "Unknown",
    )
    raw = _call_openrouter(SYSTEM_PROMPT, user_msg, ANALYSIS_MODELS, max_tokens=2500)
    return _parse_json(raw, event.get("id", "?"), "analysis")


def enrich_pending_events(db_conn: Any, batch_size: int = 5) -> int:
    """
    Find up to batch_size unenriched events and enrich them.
    Returns count of successfully enriched events.
    """
    cur = db_conn.cursor()
    rows = cur.execute(
        """SELECT e.id, e.entity_id, e.headline, e.amount, e.currency,
                  e.source_name, e.occurred_at, e.event_type,
                  en.name as entity_name, en.type as entity_type, en.sector
           FROM events e
           JOIN entities en ON e.entity_id = en.id
           WHERE e.enriched_at IS NULL
           ORDER BY e.ingested_at DESC
           LIMIT ?""",
        (batch_size,),
    ).fetchall()

    enriched_count = 0
    for row in rows:
        event  = dict(row)
        entity = {
            "name":   event["entity_name"],
            "type":   event["entity_type"],
            "sector": event["sector"],
        }

        result = enrich_event(event, entity)
        if result is None:
            continue

        # Brief pause between the two calls — free tier allows ~20 req/min on 70B
        time.sleep(4)

        # Also generate deep analysis
        analysis_result = enrich_analysis(event, entity)
        analysis_json   = json.dumps(analysis_result) if analysis_result else None

        # Pause between events in the batch for the same reason
        time.sleep(4)

        sector_tags_json = json.dumps(result.get("sector_tags", []))
        # Clamp importance to valid 1–5 range; default 3 if missing/invalid
        raw_importance = result.get("importance")
        try:
            importance = max(1, min(5, int(raw_importance)))
        except (TypeError, ValueError):
            importance = 3

        cur.execute(
            """UPDATE events
               SET plain_english=?, market_impact=?, invest_signal=?,
                   for_you=?, sector_tags=?, analysis=?, importance=?, enriched_at=?
               WHERE id=?""",
            (
                result.get("plain_english", ""),
                result.get("market_impact", ""),
                result.get("invest_signal", ""),
                result.get("for_you", ""),
                sector_tags_json,
                analysis_json,
                importance,
                datetime.now(timezone.utc).isoformat(),
                event["id"],
            ),
        )
        db_conn.commit()
        enriched_count += 1
        print(f"[Enrichment] ✓ P{importance} {event['headline'][:65]}")

    return enriched_count


def enrich_all_pending(db_conn: Any) -> int:
    """Enrich ALL unenriched events — used by /admin/enrich endpoint."""
    total = 0
    while True:
        n = enrich_pending_events(db_conn, batch_size=5)
        total += n
        if n == 0:
            break
    return total
