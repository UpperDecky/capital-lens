"""Generate analytics reports from the JSONL analytics log."""
import json
from collections import Counter
from datetime import datetime, timedelta, timezone


class AnalyticsReporter:
    """Read analytics.jsonl and produce reports."""

    LOG_FILE = 'analytics.jsonl'

    @staticmethod
    def load_events(days: int = 7) -> list:
        """Load events written in the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        events = []
        try:
            with open(AnalyticsReporter.LOG_FILE, 'r', encoding='utf-8') as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        ts_str = entry.get('timestamp', '')
                        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                        if ts >= cutoff:
                            events.append(entry)
                    except (json.JSONDecodeError, ValueError):
                        continue
        except FileNotFoundError:
            pass
        return events

    @staticmethod
    def get_weekly_report() -> dict:
        """Generate the standard weekly analytics report."""
        events = AnalyticsReporter.load_events(days=7)
        event_counts = Counter(e.get('event') for e in events)
        unique_users = {e['user_id'] for e in events if e.get('user_id')}

        signups = event_counts.get('user_signup', 0)
        upgrades = event_counts.get('tier_upgrade', 0)
        alert_creators = len({
            e['user_id'] for e in events
            if e.get('event') == 'alert_created' and e.get('user_id')
        })
        active_users = len({
            e['user_id'] for e in events
            if e.get('event') == 'user_login' and e.get('user_id')
        })

        def pct(num, denom):
            if not denom:
                return '0.0%'
            return f"{100 * num / denom:.1f}%"

        return {
            'week_ending': datetime.now(timezone.utc).isoformat(),
            'summary': {
                'total_events_tracked': len(events),
                'unique_users': len(unique_users),
                'new_signups': signups,
                'active_users': active_users,
                'alerts_created': event_counts.get('alert_created', 0),
                'tier_upgrades': upgrades,
            },
            'funnel': {
                'signups': signups,
                'signup_to_first_alert': f"{alert_creators}/{signups} ({pct(alert_creators, signups)})",
                'signup_to_upgrade': f"{upgrades}/{signups} ({pct(upgrades, signups)})",
            },
            'event_breakdown': dict(event_counts),
            'top_features': {
                'events_viewed': event_counts.get('event_viewed', 0),
                'searches': event_counts.get('search', 0),
                'watchlists_created': event_counts.get('watchlist_created', 0),
                'backtests_run': event_counts.get('backtest_run', 0),
                'alerts_triggered': event_counts.get('alert_triggered', 0),
            },
        }

    @staticmethod
    def get_user_cohort(signup_days_ago: int) -> dict:
        """Retention analysis for the cohort that signed up N days ago."""
        lookback = max(signup_days_ago + 8, 14)
        events = AnalyticsReporter.load_events(days=lookback)

        target_date = (datetime.now(timezone.utc) - timedelta(days=signup_days_ago)).date()

        cohort_users = set()
        for e in events:
            if e.get('event') == 'user_signup':
                try:
                    ts = datetime.fromisoformat(
                        e['timestamp'].replace('Z', '+00:00')
                    ).date()
                    if ts == target_date:
                        cohort_users.add(e.get('user_id') or e.get('properties', {}).get('email'))
                except Exception:
                    continue

        cohort_users.discard(None)

        active_day_1 = {
            e['user_id'] for e in events
            if e.get('event') == 'user_login'
            and e.get('user_id') in cohort_users
        }
        active_day_7 = {
            e['user_id'] for e in events
            if e.get('event') == 'user_login'
            and e.get('user_id') in cohort_users
            and (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
            ).days <= 7
        }

        def fmt(num, denom):
            if not denom:
                return '0/0 (0.0%)'
            return f"{num}/{denom} ({100 * num / denom:.1f}%)"

        n = len(cohort_users)
        return {
            'cohort_date': str(target_date),
            'cohort_size': n,
            'day_1_retention': fmt(len(active_day_1), n),
            'day_7_retention': fmt(len(active_day_7), n),
        }

    @staticmethod
    def get_daily_active_users(days: int = 30) -> list:
        """Return daily active user counts for the last N days."""
        events = AnalyticsReporter.load_events(days=days)
        dau: dict = {}
        for e in events:
            if e.get('event') == 'user_login' and e.get('user_id'):
                try:
                    day = datetime.fromisoformat(
                        e['timestamp'].replace('Z', '+00:00')
                    ).date().isoformat()
                    if day not in dau:
                        dau[day] = set()
                    dau[day].add(e['user_id'])
                except Exception:
                    continue
        return sorted(
            [{'date': d, 'dau': len(users)} for d, users in dau.items()],
            key=lambda x: x['date'],
        )


reporter = AnalyticsReporter()
