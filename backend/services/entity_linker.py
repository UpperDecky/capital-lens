"""Match company names and tickers in text to entity_ids."""
from difflib import SequenceMatcher
from backend.database import get_connection


class EntityLinker:
    """Cache entity names for fast fuzzy matching against headlines."""

    MATCH_THRESHOLD = 0.72

    def __init__(self) -> None:
        self._load()

    def _load(self) -> None:
        conn = get_connection()
        try:
            rows = conn.execute(
                "SELECT id, name, ticker, description FROM entities WHERE type='company'"
            ).fetchall()
        finally:
            conn.close()

        self._entities = [dict(r) for r in rows]
        # Map lowercase name -> id for exact/substring lookups
        self._name_map: dict[str, str] = {
            r['name'].lower(): r['id'] for r in self._entities
        }
        # Map uppercase ticker -> id
        self._ticker_map: dict[str, str] = {}
        for r in self._entities:
            if r.get('ticker'):
                self._ticker_map[r['ticker'].upper()] = r['id']
            # Also parse ticker from description field ("Ticker: AAPL")
            desc = r.get('description') or ''
            if 'Ticker:' in desc:
                parts = desc.split('Ticker:')
                if len(parts) > 1:
                    t = parts[1].strip().split()[0].upper()
                    if t:
                        self._ticker_map[t] = r['id']

    def find_entity(self, text: str, ticker: str = None) -> str | None:
        """Return entity_id best matching the given text/ticker, or None."""
        # 1. Exact ticker match (most reliable)
        if ticker:
            eid = self._ticker_map.get(ticker.upper().strip())
            if eid:
                return eid

        # 2. Exact or substring name match in text
        text_lower = text.lower()
        for name_lower, eid in self._name_map.items():
            if name_lower in text_lower:
                return eid

        # 3. Fuzzy name match (slower, last resort)
        best_id = None
        best_ratio = self.MATCH_THRESHOLD
        for name_lower, eid in self._name_map.items():
            ratio = SequenceMatcher(None, name_lower, text_lower[:200]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_id = eid

        return best_id

    def refresh(self) -> None:
        """Reload entity cache after new entities are added."""
        self._load()


# Global singleton -- lazy-loaded to avoid DB access at import time
_linker: EntityLinker | None = None


def get_entity_linker() -> EntityLinker:
    global _linker
    if _linker is None:
        _linker = EntityLinker()
    return _linker
