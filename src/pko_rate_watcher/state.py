from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WatcherState:
    last_rate: Decimal | None = None
    last_checked_at: datetime | None = None
    last_alert_at: datetime | None = None
    condition_was_met: bool = False
    alert_sent_for_current_condition: bool = False


def load_state(path: str | Path) -> WatcherState:
    state_path = Path(path)
    if not state_path.exists():
        return WatcherState()

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    return WatcherState(
        last_rate=_decimal_or_none(raw.get("last_rate")),
        last_checked_at=_datetime_or_none(raw.get("last_checked_at")),
        last_alert_at=_datetime_or_none(raw.get("last_alert_at")),
        condition_was_met=bool(raw.get("condition_was_met", False)),
        alert_sent_for_current_condition=bool(raw.get("alert_sent_for_current_condition", False)),
    )


def save_state(path: str | Path, state: WatcherState) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "last_rate": str(state.last_rate) if state.last_rate is not None else None,
        "last_checked_at": state.last_checked_at.isoformat() if state.last_checked_at else None,
        "last_alert_at": state.last_alert_at.isoformat() if state.last_alert_at else None,
        "condition_was_met": state.condition_was_met,
        "alert_sent_for_current_condition": state.alert_sent_for_current_condition,
    }
    state_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _datetime_or_none(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    return datetime.fromisoformat(str(value))
