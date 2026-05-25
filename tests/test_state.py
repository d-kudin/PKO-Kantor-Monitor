from datetime import datetime, timezone
from decimal import Decimal

from pko_rate_watcher.state import WatcherState, load_state, save_state


def test_save_and_load_state_json_round_trip(tmp_path) -> None:
    state_file = tmp_path / "state.json"
    checked_at = datetime(2026, 5, 22, 12, 30, tzinfo=timezone.utc)
    state = WatcherState(
        last_rate=Decimal("3.7900"),
        last_checked_at=checked_at,
        last_alert_at=checked_at,
        condition_was_met=True,
        alert_sent_for_current_condition=True,
    )

    save_state(state_file, state)
    loaded = load_state(state_file)

    assert loaded == state


def test_load_state_returns_empty_state_when_file_does_not_exist(tmp_path) -> None:
    loaded = load_state(tmp_path / "missing.json")

    assert loaded == WatcherState()
