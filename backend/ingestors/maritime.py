"""
Maritime AIS vessel tracking ingestor — aisstream.io.
Uses a WebSocket connection (asyncio) run inside a sync scheduler job.
Registers for a filtered feed covering high-interest sea lanes and ports.
API docs: https://aisstream.io / https://github.com/aisstream/aisstream
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.config import AISSTREAM_API_KEY

AISSTREAM_WSS = "wss://stream.aisstream.io/v0/stream"

# Bounding boxes for high-interest maritime chokepoints
# Format: [[min_lat, min_lon], [max_lat, max_lon]]
BOUNDING_BOXES: list[list[list[float]]] = [
    [[ 25.0,  56.0], [ 28.0,  58.0]],   # Strait of Hormuz
    [[ 11.5,  42.5], [ 15.0,  44.5]],   # Bab el-Mandeb (Red Sea entrance)
    [[ 30.5,  32.0], [ 31.5,  33.0]],   # Suez Canal
    [[  1.0, 103.5], [  1.5, 104.5]],   # Strait of Malacca (Singapore)
    [[ 21.5, 119.5], [ 25.5, 122.0]],   # Taiwan Strait
    [[ 35.0,  27.0], [ 42.0,  32.5]],   # Black Sea / Bosphorus
    [[ 54.0,  18.0], [ 57.0,  21.0]],   # Baltic Sea / Kaliningrad corridor
    [[ 50.0,  -6.0], [ 52.0,   2.0]],   # English Channel
]

# Ship type codes of interest (AIS ITU-R type codes)
# 30=Fishing, 70-79=Cargo, 80-89=Tanker, 35=Military, 37=Pleasure
INTERESTING_TYPES: set[int] = {35, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
                                 80, 81, 82, 83, 84, 85, 86, 87, 88, 89}

COLLECT_SECONDS = 25   # how long to listen before disconnecting


async def _collect_messages(api_key: str) -> list[dict]:
    """Open WebSocket, subscribe, collect messages for COLLECT_SECONDS, close."""
    try:
        import websockets  # type: ignore
    except ImportError:
        print("[Maritime] websockets package not installed — run: pip install websockets")
        return []

    messages: list[dict] = []
    subscribe_msg = {
        "APIKey": api_key,
        "BoundingBoxes": BOUNDING_BOXES,
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

    try:
        async with websockets.connect(AISSTREAM_WSS, ping_interval=10) as ws:
            await ws.send(json.dumps(subscribe_msg))
            deadline = asyncio.get_event_loop().time() + COLLECT_SECONDS
            while asyncio.get_event_loop().time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    msg = json.loads(raw)
                    messages.append(msg)
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
    except Exception as exc:
        print(f"[Maritime] WebSocket error: {exc}")

    return messages


def _parse_position_report(msg: dict) -> dict | None:
    meta = msg.get("MetaData", {})
    pr = msg.get("Message", {}).get("PositionReport", {})
    if not pr:
        return None
    return {
        "mmsi":        str(meta.get("MMSI", "")),
        "ship_name":   (meta.get("ShipName") or "").strip() or None,
        "latitude":    pr.get("Latitude"),
        "longitude":   pr.get("Longitude"),
        "speed_knots": pr.get("Sog"),          # speed over ground
        "heading":     pr.get("TrueHeading"),
        "ship_type":   None,                    # filled from ShipStaticData
        "destination": None,
        "flag_country":None,                    # not in PositionReport; set from static data or MMSI prefix
        "occurred_at": meta.get("time_utc") or datetime.now(timezone.utc).isoformat(),
    }


def _parse_static_data(msg: dict) -> dict | None:
    meta = msg.get("MetaData", {})
    sd = msg.get("Message", {}).get("ShipStaticData", {})
    if not sd:
        return None
    return {
        "mmsi":        str(meta.get("MMSI", "")),
        "ship_name":   (sd.get("Name") or "").strip() or None,
        "ship_type":   sd.get("Type"),
        "destination": (sd.get("Destination") or "").strip() or None,
        "flag_country":sd.get("ImoNumber"),     # ISO country from flag; use MMSI prefix instead
        "occurred_at": meta.get("time_utc") or datetime.now(timezone.utc).isoformat(),
        "latitude":    None,
        "longitude":   None,
        "speed_knots": None,
        "heading":     None,
    }


def _mmsi_to_flag(mmsi: str) -> str | None:
    """Rough country lookup from MMSI 3-digit MID prefix."""
    MID_TO_ISO: dict[str, str] = {
        "232": "GB", "233": "GB", "235": "GB",
        "244": "NL", "245": "NL",
        "211": "DE", "218": "DE",
        "228": "FR", "227": "FR",
        "247": "IT", "248": "IT",
        "271": "TR",
        "316": "CA",
        "338": "US", "367": "US", "369": "US",
        "412": "CN", "413": "CN", "414": "CN",
        "431": "JP", "432": "JP",
        "440": "KR", "441": "KR",
        "477": "HK",
        "525": "ID",
        "548": "PH",
        "563": "SG",
        "574": "VN",
        "636": "LR",
        "657": "KE",
        "710": "BR",
        "725": "CL",
        "775": "AR",
    }
    prefix = mmsi[:3]
    return MID_TO_ISO.get(prefix)


def fetch_maritime_data(db_conn: Any, _entity_map: dict[str, str]) -> int:
    """
    Connect to aisstream.io WebSocket, collect vessel positions for
    COLLECT_SECONDS, store new snapshots in maritime_events.
    Returns count of new rows inserted.
    """
    if not AISSTREAM_API_KEY:
        print("[Maritime] AISSTREAM_API_KEY not set — skipping.")
        return 0

    messages = asyncio.run(_collect_messages(AISSTREAM_API_KEY))

    if not messages:
        print("[Maritime] No messages received.")
        return 0

    # Merge position and static data keyed by MMSI
    vessels: dict[str, dict] = {}
    for msg in messages:
        msg_type = msg.get("MessageType", "")
        parsed: dict | None = None
        if msg_type == "PositionReport":
            parsed = _parse_position_report(msg)
        elif msg_type == "ShipStaticData":
            parsed = _parse_static_data(msg)
        if not parsed or not parsed["mmsi"]:
            continue
        mmsi = parsed["mmsi"]
        if mmsi not in vessels:
            vessels[mmsi] = parsed
        else:
            # Merge: fill in missing fields
            for k, v in parsed.items():
                if v is not None and vessels[mmsi].get(k) is None:
                    vessels[mmsi][k] = v

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for mmsi, v in vessels.items():
        lat = v.get("latitude")
        lon = v.get("longitude")
        if lat is None or lon is None:
            continue  # skip entries with no position

        ship_type_code = v.get("ship_type")
        if ship_type_code is not None and ship_type_code not in INTERESTING_TYPES:
            continue  # skip passenger ferries, recreational, etc.

        # Deduplicate: same MMSI within the same 5-minute window
        minute_prefix = (v.get("occurred_at") or now)[:15]  # YYYY-MM-DDTHH:M
        exists = db_conn.execute(
            "SELECT 1 FROM maritime_events WHERE mmsi=? AND occurred_at LIKE ?",
            (mmsi, minute_prefix + "%"),
        ).fetchone()
        if exists:
            continue

        flag = _mmsi_to_flag(mmsi) or v.get("flag_country")

        db_conn.execute(
            """INSERT INTO maritime_events
               (id, mmsi, ship_name, ship_type, latitude, longitude,
                speed_knots, heading, destination, flag_country, occurred_at, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                mmsi,
                v.get("ship_name"),
                str(ship_type_code) if ship_type_code else None,
                lat,
                lon,
                v.get("speed_knots"),
                v.get("heading"),
                v.get("destination"),
                flag,
                v.get("occurred_at") or now,
                now,
            ),
        )
        inserted += 1

    if inserted:
        db_conn.commit()
        print(f"[Maritime] ✓ {inserted} vessel snapshots stored from {len(messages)} messages")
    else:
        print(f"[Maritime] {len(messages)} messages received, 0 new snapshots (all duplicates or filtered)")

    return inserted
