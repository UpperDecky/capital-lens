"""
Infrastructure & internet outage ingestor — Cloudflare Radar.
Free API — generate a token at: dash.cloudflare.com → My Profile → API Tokens
Required permission: Radar:Read (read-only template works)
API docs: https://developers.cloudflare.com/radar/investigate/outages/
License: CC BY-NC 4.0
"""
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import CLOUDFLARE_API_TOKEN

CF_RADAR_BASE = "https://api.cloudflare.com/client/v4/radar"

HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept": "application/json",
}


def _auth_headers() -> dict[str, str]:
    return {**HEADERS, "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}


def _fetch_outages() -> list[dict]:
    """Retrieve latest verified internet outages from Cloudflare Radar."""
    try:
        with httpx.Client(headers=_auth_headers(), timeout=20) as client:
            resp = client.get(
                f"{CF_RADAR_BASE}/annotations/outages",
                params={"limit": 50, "format": "json"},
            )
            if resp.status_code == 401:
                print("[Infra] Cloudflare API token invalid or expired — check CLOUDFLARE_API_TOKEN")
                return []
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {}).get("annotations", [])
    except Exception as exc:
        print(f"[Infra] Cloudflare Radar fetch error: {exc}")
        return []


def _fetch_internet_quality(iso2: str | None = None) -> list[dict]:
    """Fetch traffic anomalies (leading indicators of outages)."""
    try:
        params: dict = {"limit": 20, "format": "json"}
        if iso2:
            params["location"] = iso2
        with httpx.Client(headers=_auth_headers(), timeout=20) as client:
            resp = client.get(
                f"{CF_RADAR_BASE}/annotations/outages",
                params=params,
            )
            resp.raise_for_status()
            return resp.json().get("result", {}).get("annotations", [])
    except Exception as exc:
        print(f"[Infra] Traffic anomaly fetch error: {exc}")
        return []


def _parse_outage_type(annotation: dict) -> tuple[str, str, str]:
    """
    Extract outage_type, scope, cause from a Cloudflare annotation.
    Returns (outage_type, scope, cause) strings.
    """
    event_type = annotation.get("eventType", "outage")
    outage_type = "regional" if "region" in event_type.lower() else "nationwide"
    if "isp" in event_type.lower() or "asn" in event_type.lower():
        outage_type = "isp"

    locations = annotation.get("locations", [])
    scope = ", ".join(loc.get("label", "") for loc in locations) if locations else "Unknown"
    cause = annotation.get("description", "Unknown cause")[:300]

    return outage_type, scope, cause


def _extract_iso2(annotation: dict) -> str | None:
    """Try to extract an ISO2 country code from the annotation."""
    locations = annotation.get("locations", [])
    for loc in locations:
        code = loc.get("code", "")
        if len(code) == 2:
            return code.upper()
    return None


def _extract_asn(annotation: dict) -> str | None:
    """Extract ASN if present in the annotation."""
    networks = annotation.get("networks", [])
    if networks:
        return str(networks[0].get("asn") or networks[0].get("name", ""))
    return None


def fetch_infrastructure_events(db_conn: Any) -> int:
    """
    Pull latest internet outages from Cloudflare Radar.
    Stores new outages in infra_events table.
    Returns count of new rows inserted.
    """
    if not CLOUDFLARE_API_TOKEN:
        print("[Infra] CLOUDFLARE_API_TOKEN not set — skipping.")
        return 0

    annotations = _fetch_outages()
    if not annotations:
        print("[Infra] No outage annotations returned from Cloudflare Radar.")
        return 0

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for ann in annotations:
        ann_id    = ann.get("id") or ann.get("datasetId") or str(uuid.uuid4())
        start_raw = ann.get("startDate") or ann.get("startTime") or now
        end_raw   = ann.get("endDate") or ann.get("endTime")

        # Normalise timestamps
        try:
            started_at = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).isoformat()
        except Exception:
            started_at = now
        try:
            ended_at = datetime.fromisoformat(end_raw.replace("Z", "+00:00")).isoformat() if end_raw else None
        except Exception:
            ended_at = None

        # Deduplicate by Cloudflare annotation ID
        dup_id = f"cf-{ann_id}"
        exists = db_conn.execute(
            "SELECT 1 FROM infra_events WHERE id=?", (dup_id,)
        ).fetchone()
        if exists:
            continue

        outage_type, scope, cause = _parse_outage_type(ann)
        iso2 = _extract_iso2(ann)
        asn  = _extract_asn(ann)

        db_conn.execute(
            """INSERT INTO infra_events
               (id, outage_type, scope, cause, iso2, asn, started_at, ended_at, ingested_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                dup_id,
                outage_type,
                scope[:200],
                cause,
                iso2,
                asn,
                started_at,
                ended_at,
                now,
            ),
        )
        inserted += 1

        # Also mirror significant nationwide outages into geo_events for the feed
        if outage_type in ("nationwide", "regional") and iso2:
            geo_url = f"https://radar.cloudflare.com/outage-center#{ann_id}"
            geo_exists = db_conn.execute(
                "SELECT 1 FROM geo_events WHERE url=?", (geo_url,)
            ).fetchone()
            if not geo_exists:
                db_conn.execute(
                    """INSERT INTO geo_events
                       (id, iso2, headline, url, source, occurred_at, tone, themes, ingested_at)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        str(uuid.uuid4()),
                        iso2,
                        f"[Internet Outage] {outage_type.capitalize()} outage in {scope}: {cause[:120]}",
                        geo_url,
                        "Cloudflare Radar",
                        started_at,
                        -30.0,  # internet outages are moderately negative signals
                        '["internet","outage","infrastructure","cyber"]',
                        now,
                    ),
                )

    if inserted:
        db_conn.commit()
        print(f"[Infra] ✓ {inserted} new outage events stored")
    else:
        print("[Infra] No new outage events")

    return inserted
