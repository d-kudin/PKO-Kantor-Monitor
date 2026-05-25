from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pko_rate_watcher.config import AlertsConfig, WatcherConfig
from pko_rate_watcher.main import should_send_alert
from pko_rate_watcher.state import WatcherState


def make_watcher(
    *,
    condition: str = "below_or_equal",
    target_rate: str = "3.8000",
) -> WatcherConfig:
    return WatcherConfig(
        url="https://example.test/rates",
        currency="USD",
        rate_type="sell",
        condition=condition,
        target_rate=Decimal(target_rate),
        state_file="state/state.json",
        log_file="logs/rate_watcher.log",
        dry_run=False,
    )


def test_should_send_alert_when_condition_first_becomes_true() -> None:
    decision = should_send_alert(
        current_rate=Decimal("3.7900"),
        watcher=make_watcher(),
        alerts=AlertsConfig(min_minutes_between_alerts=360),
        state=WatcherState(),
        checked_at=datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc),
    )

    assert decision.condition_met is True
    assert decision.send_alert is True
    assert decision.reason == "condition_met_first_time"


def test_should_not_send_duplicate_alert_while_condition_stays_true() -> None:
    checked_at = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    state = WatcherState(
        condition_was_met=True,
        alert_sent_for_current_condition=True,
        last_alert_at=checked_at - timedelta(minutes=30),
    )

    decision = should_send_alert(
        current_rate=Decimal("3.7900"),
        watcher=make_watcher(),
        alerts=AlertsConfig(min_minutes_between_alerts=360),
        state=state,
        checked_at=checked_at,
    )

    assert decision.condition_met is True
    assert decision.send_alert is False
    assert decision.reason == "already_alerted_for_current_condition"


def test_should_send_alert_again_after_min_interval_when_enabled() -> None:
    checked_at = datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc)
    state = WatcherState(
        condition_was_met=True,
        alert_sent_for_current_condition=True,
        last_alert_at=checked_at - timedelta(minutes=361),
    )

    decision = should_send_alert(
        current_rate=Decimal("3.7900"),
        watcher=make_watcher(),
        alerts=AlertsConfig(
            min_minutes_between_alerts=360,
            send_alert_when_condition_recovers=True,
        ),
        state=state,
        checked_at=checked_at,
    )

    assert decision.condition_met is True
    assert decision.send_alert is True
    assert decision.reason == "min_interval_elapsed"


def test_should_reset_alert_state_when_condition_is_false() -> None:
    decision = should_send_alert(
        current_rate=Decimal("3.8100"),
        watcher=make_watcher(),
        alerts=AlertsConfig(min_minutes_between_alerts=360),
        state=WatcherState(condition_was_met=True, alert_sent_for_current_condition=True),
        checked_at=datetime(2026, 5, 22, 12, 0, tzinfo=timezone.utc),
    )

    assert decision.condition_met is False
    assert decision.send_alert is False
    assert decision.reason == "condition_not_met"
