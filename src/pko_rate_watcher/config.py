from __future__ import annotations

import os
import tomllib
from decimal import Decimal
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator


RateType = Literal["buy", "sell"]
Condition = Literal["below_or_equal", "above_or_equal"]


class ConfigError(RuntimeError):
    """Raised when local app configuration is missing or invalid."""


class WatcherConfig(BaseModel):
    url: str
    currency: str = "USD"
    rate_type: RateType = "sell"
    condition: Condition = "below_or_equal"
    target_rate: Decimal = Field(gt=Decimal("0"))
    state_file: Path = Path("state/state.json")
    log_file: Path = Path("logs/rate_watcher.log")
    dry_run: bool = False

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("currency must be a 3-letter ISO code, for example USD")
        return normalized


class AlertsConfig(BaseModel):
    min_minutes_between_alerts: int = Field(default=360, ge=0)
    send_alert_when_condition_recovers: bool = False


class LocalSoundConfig(BaseModel):
    enabled: bool = False
    mode: str = "message_beep"
    frequency: int = Field(default=1000, ge=37, le=32767)
    duration_ms: int = Field(default=700, ge=1)
    wav_file: str = ""


class AppConfig(BaseModel):
    watcher: WatcherConfig
    alerts: AlertsConfig
    local_sound: LocalSoundConfig = Field(default_factory=LocalSoundConfig)


class TelegramConfig(BaseModel):
    bot_token: str
    chat_id: str


def load_app_config(path: str | Path = "config.toml") -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Brak pliku konfiguracji: {config_path}")

    try:
        raw_config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        return AppConfig.model_validate(raw_config)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Nieprawidlowy format TOML w {config_path}: {exc}") from exc
    except ValidationError as exc:
        raise ConfigError(f"Nieprawidlowa konfiguracja w {config_path}: {exc}") from exc


def load_telegram_config(dotenv_path: str | Path = ".env") -> TelegramConfig:
    dotenv_file = Path(dotenv_path)
    load_dotenv(dotenv_path=dotenv_file, override=False)

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": bot_token,
            "TELEGRAM_CHAT_ID": chat_id,
        }.items()
        if not value
    ]
    if missing:
        hint = f" Utworz plik {dotenv_file} na podstawie .env.example." if not dotenv_file.exists() else ""
        raise ConfigError(f"Brak konfiguracji Telegram: {', '.join(missing)}.{hint}")

    return TelegramConfig(bot_token=bot_token, chat_id=chat_id)
