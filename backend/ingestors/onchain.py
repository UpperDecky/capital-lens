"""
On-chain whale transaction ingestor -- Bitcoin + Ethereum.

Uses Blockchair API (free tier: 1440 req/day, no key required).
Polls for transactions > $1M USD every 5 minutes via scheduler.

Geographic attribution uses a static registry of known exchange
wallet addresses mapped to their operating country.

Blockchair docs: https://blockchair.com/api/docs
"""
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.config import BLOCKCHAIR_API_KEY

# ---- Country centroids (lat, lon) -------------------------------------------

COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "US": (37.09,  -95.71),
    "GB": (55.38,   -3.44),
    "DE": (51.17,   10.45),
    "FR": (46.23,    2.21),
    "JP": (36.20,  138.25),
    "CN": (35.86,  104.20),
    "RU": (61.52,  105.32),
    "IN": (20.59,   78.96),
    "SG": ( 1.35,  103.82),
    "HK": (22.40,  114.11),
    "AE": (23.42,   53.85),
    "MT": (35.94,   14.38),
    "SC": (-4.68,   55.49),
    "KY": (19.51,  -80.57),
    "CH": (46.82,    8.23),
    "LU": (49.82,    6.13),
    "XX": ( 0.00,    0.00),
}

# ---- Known exchange registry ------------------------------------------------
# Maps ETH/BTC wallet address prefix -> (label, iso2)
# These are publicly documented hot wallet addresses for major exchanges.

KNOWN_ETH_EXCHANGES: dict[str, tuple[str, str]] = {
    "0x28c6c06298d514db089934071355e5743bf21d60": ("Binance",   "MT"),
    "0xdfd5293d8e347dfe59e90efd55b2956a1343963d": ("Binance",   "MT"),
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": ("Binance",   "MT"),
    "0xa9d1e08c7793af67e9d92fe308d5697fb81d3e43": ("Coinbase",  "US"),
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": ("Coinbase",  "US"),
    "0x503828976d22510aad0201ac7ec88293211d23da": ("Coinbase",  "US"),
    "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2": ("FTX",       "XX"),
    "0xc098b2a3aa256d2140208c3de6543aaef5cd3a94": ("Kraken",    "US"),
    "0xe853c56864a2ebe4576a807d26fdc4a0ada51919": ("Kraken",    "US"),
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": ("Huobi",     "SC"),
    "0x1062a747393198f70f71ec65a582423dba7e5ab3": ("OKX",       "SC"),
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": ("OKX",       "SC"),
    "0x750e4c4984a9e0f12978ea6742bc1c5d248f40ed": ("Bybit",     "AE"),
    "0xf89d7b9c864f589bbf53a82105107622b35eaa40": ("Bybit",     "AE"),
}

KNOWN_BTC_EXCHANGES: dict[str, tuple[str, str]] = {
    "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo":  ("Binance",   "MT"),
    "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ":  ("Binance",   "MT"),
    "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6":  ("Coinbase",  "US"),
    "1FzWLkAahHooV3kzTgyx6qsswXJ6sCXkSR":  ("Coinbase",  "US"),
    "3Nxwenay9Z8Lc9JBiywExpnEFiLp6Afp8v":  ("Kraken",    "US"),
    "3AfGRmpuRE7nNvhauACHvnE5Ckxq4PJKxU":  ("Kraken",    "US"),
    "1Kr6QSydW9bFQG1mXiPNNu6WpJGmUa9i1g":  ("Bitfinex",  "HK"),
    "3D2oetdNuZUqQHPJmcMDDHYoqkyNVsFk9r":  ("OKX",       "SC"),
    "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": ("Bybit", "AE"),
}

_HEADERS = {
    "User-Agent": "CapitalLens/1.0 research@capitallens.dev",
    "Accept":     "application/json",
}

_BLOCKCHAIR_BASE = "https://api.blockchair.com"

_THRESHOLD_USD = 1_000_000  # only store flows >= $1M


def _blockchair_params(extra: dict | None = None) -> dict:
    p: dict = {}
    if BLOCKCHAIR_API_KEY:
        p["key"] = BLOCKCHAIR_API_KEY
    if extra:
        p.update(extra)
    return p


def _lookup_eth_address(addr: str) -> tuple[str, str] | None:
    """Return (label, iso2) if addr is a known ETH exchange address."""
    if not addr:
        return None
    return KNOWN_ETH_EXCHANGES.get(addr.lower())


def _lookup_btc_address(addr: str) -> tuple[str, str] | None:
    """Return (label, iso2) if addr is a known BTC exchange address."""
    if not addr:
        return None
    return KNOWN_BTC_EXCHANGES.get(addr)


def _coords(iso2: str) -> tuple[float, float]:
    return COUNTRY_COORDS.get(iso2, COUNTRY_COORDS["XX"])


# ---- Bitcoin whale transactions ---------------------------------------------

def _fetch_btc_whales(db_conn: Any) -> int:
    """Fetch large BTC transactions from Blockchair. Returns inserted count."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    try:
        resp = httpx.get(
            f"{_BLOCKCHAIR_BASE}/bitcoin/transactions",
            params=_blockchair_params({
                "q":     f"output_total_usd({_THRESHOLD_USD}..)",
                "s":     "time(desc)",
                "limit": 10,
            }),
            headers=_HEADERS,
            timeout=20,
        )
        if resp.status_code == 430:
            print("[CashFlow/BTC] Blockchair rate limited")
            return 0
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[CashFlow/BTC] Fetch error: {exc}")
        return 0

    for tx in data.get("data", []):
        tx_hash      = tx.get("hash")
        amount_usd   = float(tx.get("output_total_usd") or 0)
        occurred_str = tx.get("time", now)

        if not tx_hash or amount_usd < _THRESHOLD_USD:
            continue

        try:
            occurred_at = datetime.strptime(
                occurred_str, "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            occurred_at = now

        # BTC doesn't expose addresses in the aggregate endpoint --
        # attribute to generic chain-level source/dest
        src_label, src_iso = "BTC Network", "XX"
        dst_label, dst_iso = "BTC Network", "XX"

        src_lat, src_lon = _coords(src_iso)
        dst_lat, dst_lon = _coords(dst_iso)

        headline = (
            f"BTC whale transfer: ${amount_usd/1e6:.2f}M on-chain"
        )

        flow_id = str(uuid.uuid4())
        try:
            db_conn.execute(
                """INSERT OR IGNORE INTO cash_flows
                   (id, flow_type, asset, amount_usd,
                    source_label, dest_label,
                    source_country, dest_country,
                    source_lat, source_lon, dest_lat, dest_lon,
                    tx_hash, headline, source_name, occurred_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (flow_id, "crypto_whale", "BTC", amount_usd,
                 src_label, dst_label,
                 src_iso, dst_iso,
                 src_lat, src_lon, dst_lat, dst_lon,
                 tx_hash, headline, "Blockchair", occurred_at, now),
            )
            inserted += db_conn.execute("SELECT changes()").fetchone()[0]
        except Exception as exc:
            print(f"[CashFlow/BTC] DB error: {exc}")

    if inserted:
        db_conn.commit()
    return inserted


# ---- Ethereum whale transactions --------------------------------------------

def _fetch_eth_whales(db_conn: Any) -> int:
    """Fetch large ETH transactions from Blockchair. Returns inserted count."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    try:
        resp = httpx.get(
            f"{_BLOCKCHAIR_BASE}/ethereum/transactions",
            params=_blockchair_params({
                "q":     f"value_usd({_THRESHOLD_USD}..),type(call)",
                "s":     "time(desc)",
                "limit": 10,
            }),
            headers=_HEADERS,
            timeout=20,
        )
        if resp.status_code == 430:
            print("[CashFlow/ETH] Blockchair rate limited")
            return 0
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[CashFlow/ETH] Fetch error: {exc}")
        return 0

    for tx in data.get("data", []):
        tx_hash      = tx.get("hash")
        amount_usd   = float(tx.get("value_usd") or 0)
        sender       = (tx.get("sender") or "").lower()
        recipient    = (tx.get("recipient") or "").lower()
        occurred_str = tx.get("time", "")

        if not tx_hash or amount_usd < _THRESHOLD_USD:
            continue

        try:
            occurred_at = datetime.strptime(
                occurred_str, "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            occurred_at = now

        src_info = _lookup_eth_address(sender)
        dst_info = _lookup_eth_address(recipient)

        src_label = src_info[0] if src_info else "Unknown Wallet"
        src_iso   = src_info[1] if src_info else "XX"
        dst_label = dst_info[0] if dst_info else "Unknown Wallet"
        dst_iso   = dst_info[1] if dst_info else "XX"

        src_lat, src_lon = _coords(src_iso)
        dst_lat, dst_lon = _coords(dst_iso)

        headline = (
            f"ETH whale: ${amount_usd/1e6:.2f}M "
            f"{src_label} -> {dst_label}"
        )

        flow_id = str(uuid.uuid4())
        try:
            db_conn.execute(
                """INSERT OR IGNORE INTO cash_flows
                   (id, flow_type, asset, amount_usd,
                    source_label, dest_label,
                    source_country, dest_country,
                    source_lat, source_lon, dest_lat, dest_lon,
                    tx_hash, headline, source_name, occurred_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (flow_id, "crypto_whale", "ETH", amount_usd,
                 src_label, dst_label,
                 src_iso, dst_iso,
                 src_lat, src_lon, dst_lat, dst_lon,
                 tx_hash, headline, "Blockchair", occurred_at, now),
            )
            inserted += db_conn.execute("SELECT changes()").fetchone()[0]
        except Exception as exc:
            print(f"[CashFlow/ETH] DB error: {exc}")

    if inserted:
        db_conn.commit()
    return inserted


# ---- Solana (via Blockchair) ------------------------------------------------

def _fetch_sol_whales(db_conn: Any) -> int:
    """Fetch large SOL transactions. Returns inserted count."""
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0

    try:
        resp = httpx.get(
            f"{_BLOCKCHAIR_BASE}/solana/transactions",
            params=_blockchair_params({
                "s":     "time(desc)",
                "limit": 10,
            }),
            headers=_HEADERS,
            timeout=20,
        )
        if resp.status_code in (429, 430):
            return 0
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[CashFlow/SOL] Fetch error: {exc}")
        return 0

    for tx in data.get("data", []):
        tx_hash    = tx.get("hash") or tx.get("transaction_hash")
        fee_usd    = float(tx.get("fee_usd") or 0)
        # Solana aggregated tx endpoint doesn't include value_usd --
        # skip unless we have meaningful amounts
        if not tx_hash or fee_usd < 10:
            continue

        occurred_str = tx.get("time", "")
        try:
            occurred_at = datetime.strptime(
                occurred_str, "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            occurred_at = now

        flow_id  = str(uuid.uuid4())
        headline = f"SOL network activity detected (fee: ${fee_usd:.2f})"
        try:
            db_conn.execute(
                """INSERT OR IGNORE INTO cash_flows
                   (id, flow_type, asset, amount_usd,
                    source_label, dest_label,
                    source_country, dest_country,
                    source_lat, source_lon, dest_lat, dest_lon,
                    tx_hash, headline, source_name, occurred_at, ingested_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (flow_id, "crypto_whale", "SOL", fee_usd,
                 "SOL Network", "SOL Network", "XX", "XX",
                 0, 0, 0, 0,
                 tx_hash, headline, "Blockchair", occurred_at, now),
            )
            inserted += db_conn.execute("SELECT changes()").fetchone()[0]
        except Exception:
            pass

    if inserted:
        db_conn.commit()
    return inserted


# ---- Public entry point -----------------------------------------------------

def fetch_onchain_flows(db_conn: Any, entity_map: dict | None = None) -> int:
    """
    Fetch large on-chain transactions for BTC and ETH.
    Returns total inserted count.
    """
    total = 0
    total += _fetch_btc_whales(db_conn)
    total += _fetch_eth_whales(db_conn)
    if total > 0:
        print(f"[CashFlow/OnChain] Stored {total} new whale transactions")
    return total
