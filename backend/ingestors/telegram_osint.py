"""
Telegram OSINT channel ingestor — Pyrogram.
Reads public channels without joining them.
Requires a free Telegram API app registration at https://my.telegram.org/apps
Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION in .env

TELEGRAM_SESSION is a base64 StringSession string generated on first run
by running this module directly:
    python -m backend.ingestors.telegram_osint --setup

Only public channels are accessed. Respect Telegram's Terms of Service.
"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from backend.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION

# Public OSINT channels to monitor (username without @)
OSINT_CHANNELS: list[dict] = [
    {"username": "intelslava",       "label": "Intel Slava Z",     "region": "UA"},
    {"username": "OSINTdefender",    "label": "OSINTdefender",     "region": "Global"},
    {"username": "warmonitor",       "label": "War Monitor",       "region": "Global"},
    {"username": "wartranslated",    "label": "War Translated",    "region": "UA"},
    {"username": "auroraborealis",   "label": "Aurora Intel",      "region": "Global"},
    {"username": "GeoConfirmed",     "label": "GeoConfirmed",      "region": "Global"},
    {"username": "UkraineNow",       "label": "Ukraine Now",       "region": "UA"},
    {"username": "rybar",            "label": "Rybar (RU mil)",    "region": "RU"},
    {"username": "militarymaps",     "label": "Military Maps",     "region": "Global"},
    {"username": "conflictnews",     "label": "Conflict News",     "region": "Global"},
    {"username": "mod_russia_en",    "label": "RU MoD (EN)",       "region": "RU"},
    {"username": "IsraelWarRoom",    "label": "Israel War Room",   "region": "IL"},
    {"username": "paxreport",        "label": "Pax Report",        "region": "Global"},
]

LOOKBACK_HOURS = 6    # only fetch messages from the last 6 hours
MAX_MSGS_PER_CHANNEL = 20


async def _collect_messages_async(api_id: int, api_hash: str, session: str) -> list[dict]:
    """Use Pyrogram to read recent messages from each OSINT channel."""
    try:
        from pyrogram import Client  # type: ignore
        from pyrogram.errors import FloodWait, ChannelPrivate, UsernameNotOccupied  # type: ignore
        from pyrogram.types import Message  # type: ignore
    except ImportError:
        print("[Telegram] pyrogram not installed — run: pip install pyrogram tgcrypto")
        return []

    results: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    # StringSession allows stateless auth (no session file needed on disk)
    try:
        from pyrogram.storage import MemoryStorage  # type: ignore
        storage = MemoryStorage(session)
    except Exception:
        storage = None  # fallback; Pyrogram will prompt for auth

    try:
        app = Client(
            name=":memory:",
            api_id=api_id,
            api_hash=api_hash,
            session_string=session if session else None,
            no_updates=True,
            in_memory=True,
        )
    except Exception as exc:
        print(f"[Telegram] Client init error: {exc}")
        return []

    try:
        async with app:
            for ch in OSINT_CHANNELS:
                username = ch["username"]
                label    = ch["label"]
                region   = ch["region"]
                try:
                    async for msg in app.get_chat_history(username, limit=MAX_MSGS_PER_CHANNEL):
                        if not isinstance(msg, Message):
                            continue
                        msg_date = msg.date
                        if msg_date and msg_date < cutoff:
                            break  # messages are in reverse chronological order

                        text = msg.text or msg.caption or ""
                        if not text or len(text) < 30:
                            continue  # skip very short messages (photos, reactions)

                        # Skip forwarded messages to avoid duplicates across channels
                        if msg.forward_origin:
                            continue

                        results.append({
                            "channel":    username,
                            "label":      label,
                            "region":     region,
                            "message_id": msg.id,
                            "text":       text[:800],
                            "date":       msg_date.isoformat() if msg_date else datetime.now(timezone.utc).isoformat(),
                            "url":        f"https://t.me/{username}/{msg.id}",
                        })

                except FloodWait as fw:
                    print(f"[Telegram] FloodWait {fw.value}s on {username} — skipping")
                    await asyncio.sleep(fw.value)
                except (ChannelPrivate, UsernameNotOccupied) as exc:
                    print(f"[Telegram] Channel {username} not accessible: {exc}")
                except Exception as exc:
                    print(f"[Telegram] Error reading {username}: {exc}")

    except Exception as exc:
        print(f"[Telegram] Session error — re-run setup: {exc}")

    return results


def _store_messages(db_conn: Any, messages: list[dict]) -> int:
    """Store Telegram messages in geo_events table (source = 'Telegram OSINT')."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for msg in messages:
        url = msg["url"]
        exists = db_conn.execute(
            "SELECT 1 FROM geo_events WHERE url=?", (url,)
        ).fetchone()
        if exists:
            continue

        region = msg.get("region", "Global")
        # Map region label to ISO2 where possible
        iso2_map = {"UA": "UA", "RU": "RU", "IL": "IL", "Global": None}
        iso2 = iso2_map.get(region)

        # Truncate text to headline length for the headline field
        text = msg["text"]
        headline = f"[{msg['label']}] " + text[:200].replace("\n", " ")

        db_conn.execute(
            """INSERT INTO geo_events
               (id, iso2, headline, url, source, occurred_at, tone, themes, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                iso2,
                headline,
                url,
                f"Telegram/{msg['channel']}",
                msg["date"],
                0.0,   # tone calculated by enrichment if needed
                '["osint","telegram","conflict","intelligence"]',
                now,
            ),
        )
        inserted += 1

    if inserted:
        db_conn.commit()
    return inserted


def fetch_telegram_osint(db_conn: Any) -> int:
    """
    Pull recent messages from public OSINT Telegram channels.
    Requires TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION.
    Returns count of new geo_events rows inserted.
    """
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("[Telegram] TELEGRAM_API_ID / TELEGRAM_API_HASH not set — skipping.")
        return 0

    if not TELEGRAM_SESSION:
        print(
            "[Telegram] TELEGRAM_SESSION not set. "
            "Run: python -m backend.ingestors.telegram_osint --setup"
        )
        return 0

    try:
        api_id = int(TELEGRAM_API_ID)
    except ValueError:
        print("[Telegram] TELEGRAM_API_ID must be a number.")
        return 0

    messages = asyncio.run(_collect_messages_async(api_id, TELEGRAM_API_HASH, TELEGRAM_SESSION))

    if not messages:
        print("[Telegram] No new messages collected.")
        return 0

    inserted = _store_messages(db_conn, messages)
    print(f"[Telegram] ✓ {inserted} new messages stored from {len(OSINT_CHANNELS)} channels")
    return inserted


# ── One-time setup helper ────────────────────────────────────────────────────

async def _generate_session(api_id: int, api_hash: str) -> str:
    """Interactively log in and print a StringSession for TELEGRAM_SESSION."""
    try:
        from pyrogram import Client  # type: ignore
    except ImportError:
        print("Install pyrogram first: pip install pyrogram tgcrypto")
        return ""

    app = Client(
        ":memory:",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True,
    )
    async with app:
        session_string = await app.export_session_string()
        print("\n✓ Your TELEGRAM_SESSION string (add to .env):\n")
        print(session_string)
        print("\nStore this in TELEGRAM_SESSION= in your .env file.\n")
        return session_string


if __name__ == "__main__":
    import sys
    if "--setup" in sys.argv:
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            print("Set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env first, then re-run.")
            sys.exit(1)
        asyncio.run(_generate_session(int(TELEGRAM_API_ID), TELEGRAM_API_HASH))
    else:
        print("Usage: python -m backend.ingestors.telegram_osint --setup")
