"""Lightweight, file-based analytics tracker. No external dependencies."""
import json
import logging
from datetime import datetime, timezone

_analytics_logger = logging.getLogger('capital_lens_analytics')
if not _analytics_logger.handlers:
    _handler = logging.FileHandler('analytics.jsonl', encoding='utf-8')
    _handler.setFormatter(logging.Formatter('%(message)s'))
    _analytics_logger.addHandler(_handler)
    _analytics_logger.setLevel(logging.INFO)
    _analytics_logger.propagate = False


class AnalyticsTracker:
    """Write user events to a JSON Lines file. Non-blocking, <1ms per call."""

    @staticmethod
    def track(event_name: str, user_id: str = None, properties: dict = None) -> None:
        try:
            entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'event': event_name,
                'user_id': user_id,
                'properties': properties or {},
            }
            _analytics_logger.info(json.dumps(entry))
        except Exception:
            pass  # Analytics must never crash the main app

    @staticmethod
    def track_signup(email: str) -> None:
        AnalyticsTracker.track('user_signup', properties={'email': email})

    @staticmethod
    def track_login(user_id: str) -> None:
        AnalyticsTracker.track('user_login', user_id=user_id)

    @staticmethod
    def track_logout(user_id: str) -> None:
        AnalyticsTracker.track('user_logout', user_id=user_id)

    @staticmethod
    def track_tier_upgrade(user_id: str, from_tier: str, to_tier: str) -> None:
        AnalyticsTracker.track(
            'tier_upgrade',
            user_id=user_id,
            properties={'from': from_tier, 'to': to_tier},
        )

    @staticmethod
    def track_alert_created(user_id: str, alert_type: str) -> None:
        AnalyticsTracker.track(
            'alert_created', user_id=user_id, properties={'type': alert_type}
        )

    @staticmethod
    def track_alert_triggered(user_id: str, alert_id: str, event_id: str) -> None:
        AnalyticsTracker.track(
            'alert_triggered',
            user_id=user_id,
            properties={'alert_id': alert_id, 'event_id': event_id},
        )

    @staticmethod
    def track_event_viewed(user_id: str, event_id: str, importance: int) -> None:
        AnalyticsTracker.track(
            'event_viewed',
            user_id=user_id,
            properties={'event_id': event_id, 'importance': importance},
        )

    @staticmethod
    def track_watchlist_created(
        user_id: str, watchlist_name: str, entity_count: int
    ) -> None:
        AnalyticsTracker.track(
            'watchlist_created',
            user_id=user_id,
            properties={'name': watchlist_name, 'entity_count': entity_count},
        )

    @staticmethod
    def track_backtest_run(
        user_id: str, strategy_name: str, return_pct: float
    ) -> None:
        AnalyticsTracker.track(
            'backtest_run',
            user_id=user_id,
            properties={'strategy': strategy_name, 'return': return_pct},
        )

    @staticmethod
    def track_screening_created(user_id: str, rule_complexity: str) -> None:
        AnalyticsTracker.track(
            'screening_created',
            user_id=user_id,
            properties={'complexity': rule_complexity},
        )

    @staticmethod
    def track_feature_used(user_id: str, feature_name: str) -> None:
        AnalyticsTracker.track(
            'feature_used', user_id=user_id, properties={'feature': feature_name}
        )

    @staticmethod
    def track_search(user_id: str, query: str, result_count: int) -> None:
        AnalyticsTracker.track(
            'search',
            user_id=user_id,
            properties={'query': query[:100], 'results': result_count},
        )


tracker = AnalyticsTracker()
