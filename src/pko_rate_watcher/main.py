from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from pko_rate_watcher.config import (
    AlertsConfig,
    AppConfig,
    ConfigError,
    WatcherConfig,
    load_app_config,
    load_telegram_config,
)
from pko_rate_watcher.logger import setup_logger
from pko_rate_watcher.scraper import CurrencyRate, ScraperError, fetch_currency_rate
from pko_rate_watcher.sound_notifier import play_local_sound
from pko_rate_watcher.state import WatcherState, load_state, save_state
from pko_rate_watcher.telegram_notifier import TelegramError, send_telegram_message


@dataclass(frozen=True)
class AlertDecision:
    condition_met: bool
    send_alert: bool
    reason: str


def should_send_alert(
    *,
    current_rate: Decimal,
    watcher: WatcherConfig,
    alerts: AlertsConfig,
    state: WatcherState,
    checked_at: datetime,
) -> AlertDecision:
    condition_met = evaluate_condition(current_rate, watcher.condition, watcher.target_rate)
    if not condition_met:
        return AlertDecision(condition_met=False, send_alert=False, reason="condition_not_met")

    if not state.condition_was_met or not state.alert_sent_for_current_condition:
        return AlertDecision(
            condition_met=True,
            send_alert=True,
            reason="condition_met_first_time",
        )

    if alerts.send_alert_when_condition_recovers and _min_interval_elapsed(
        last_alert_at=state.last_alert_at,
        checked_at=checked_at,
        minutes=alerts.min_minutes_between_alerts,
    ):
        return AlertDecision(condition_met=True, send_alert=True, reason="min_interval_elapsed")

    return AlertDecision(
        condition_met=True,
        send_alert=False,
        reason="already_alerted_for_current_condition",
    )


def evaluate_condition(current_rate: Decimal, condition: str, target_rate: Decimal) -> bool:
    if condition == "below_or_equal":
        return current_rate <= target_rate
    if condition == "above_or_equal":
        return current_rate >= target_rate
    raise ValueError(f"Nieznany warunek alertu: {condition}")


def build_alert_message(
    *,
    currency_rate: CurrencyRate,
    watcher: WatcherConfig,
    checked_at: datetime,
) -> str:
    rate_label = "kupna" if watcher.rate_type == "buy" else "sprzedazy"
    operator = "<=" if watcher.condition == "below_or_equal" else ">="
    current_rate = get_observed_rate(currency_rate, watcher.rate_type)
    checked_local = checked_at.astimezone().strftime("%Y-%m-%d %H:%M")
    source_line = ""
    if currency_rate.source_date is not None:
        source_line = f"Czas danych PKO: {currency_rate.source_date.astimezone().strftime('%Y-%m-%d %H:%M')}\n"
    return (
        f"ALERT {currency_rate.currency}/PLN\n"
        f"Kurs {rate_label}: {current_rate:.4f} PLN\n"
        f"Warunek: {operator} {watcher.target_rate:.4f} PLN\n"
        f"Czas sprawdzenia: {checked_local}\n"
        f"{source_line}"
        "Zrodlo: publiczna strona PKO BP, kurs ma charakter pogladowy."
    )


def get_observed_rate(currency_rate: CurrencyRate, rate_type: str) -> Decimal:
    return currency_rate.buy if rate_type == "buy" else currency_rate.sell


def run_once(config: AppConfig, *, force_dry_run: bool = False) -> int:
    logger = setup_logger(config.watcher.log_file)
    checked_at = datetime.now(timezone.utc)
    dry_run = force_dry_run or config.watcher.dry_run

    try:
        state = load_state(config.watcher.state_file)
        currency_rate = fetch_currency_rate(config.watcher.url, config.watcher.currency)
        observed_rate = get_observed_rate(currency_rate, config.watcher.rate_type)
        decision = should_send_alert(
            current_rate=observed_rate,
            watcher=config.watcher,
            alerts=config.alerts,
            state=state,
            checked_at=checked_at,
        )

        print(
            f"Odczytano {currency_rate.currency}/PLN: "
            f"kupno={currency_rate.buy:.4f}, sprzedaz={currency_rate.sell:.4f}. "
            f"Czas danych PKO: {_format_source_date(currency_rate)}. "
            f"Warunek spelniony: {'tak' if decision.condition_met else 'nie'}."
        )
        logger.info(
            "Rate check currency=%s buy=%s sell=%s observed=%s source_date=%s condition_met=%s decision=%s",
            currency_rate.currency,
            currency_rate.buy,
            currency_rate.sell,
            observed_rate,
            currency_rate.source_date.isoformat() if currency_rate.source_date else None,
            decision.condition_met,
            decision.reason,
        )

        alert_sent = False
        if decision.send_alert:
            message = build_alert_message(
                currency_rate=currency_rate,
                watcher=config.watcher,
                checked_at=checked_at,
            )
            if dry_run:
                print("DRY-RUN: alert zostalby wyslany:")
                print(message)
                logger.info("Dry-run alert skipped reason=%s", decision.reason)
            else:
                telegram = load_telegram_config()
                send_telegram_message(
                    bot_token=telegram.bot_token,
                    chat_id=telegram.chat_id,
                    message=message,
                )
                alert_sent = True
                print("Wyslano alert Telegram.")
                logger.info("Telegram alert sent reason=%s", decision.reason)
                sound_result = play_local_sound(config.local_sound)
                print(sound_result.message)
                if sound_result.success:
                    logger.info("Local sound played")
                else:
                    logger.warning("Local sound not played: %s", sound_result.message)
        else:
            print(f"Alert nie zostal wyslany: {decision.reason}.")

        next_state = WatcherState(
            last_rate=observed_rate,
            last_checked_at=checked_at,
            last_alert_at=checked_at if alert_sent else state.last_alert_at,
            condition_was_met=decision.condition_met,
            alert_sent_for_current_condition=(
                False if not decision.condition_met else state.alert_sent_for_current_condition or alert_sent
            ),
        )
        save_state(config.watcher.state_file, next_state)
        return 0
    except (ConfigError, ScraperError, TelegramError, OSError, ValueError) as exc:
        logger.exception("Run failed: %s", exc)
        print(f"BLAD: {exc}")
        return 1


def send_test_telegram(config_path: str | Path) -> int:
    config = load_app_config(config_path)
    logger = setup_logger(config.watcher.log_file)
    try:
        telegram = load_telegram_config()
        send_telegram_message(
            bot_token=telegram.bot_token,
            chat_id=telegram.chat_id,
            message=(
                "Test PKO Rate Watcher\n"
                "Telegram Bot API dziala. To jest wiadomosc testowa."
            ),
        )
        print("Wyslano wiadomosc testowa Telegram.")
        logger.info("Telegram test message sent")
        return 0
    except (ConfigError, TelegramError, OSError) as exc:
        logger.exception("Telegram test failed: %s", exc)
        print(f"BLAD: {exc}")
        return 1


def send_test_sound(config_path: str | Path) -> int:
    config = load_app_config(config_path)
    logger = setup_logger(config.watcher.log_file)
    result = play_local_sound(config.local_sound)
    print(result.message)
    if result.success:
        logger.info("Local sound test succeeded")
        return 0

    logger.warning("Local sound test did not play: %s", result.message)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor publicznego kursu PKO BP i alert Telegram.")
    parser.add_argument("--config", default="config.toml", help="Sciezka do pliku config.toml.")
    parser.add_argument("--dry-run", action="store_true", help="Sprawdz kurs, ale nie wysylaj alertu.")
    parser.add_argument("--test-telegram", action="store_true", help="Wyslij testowa wiadomosc Telegram.")
    parser.add_argument("--test-sound", action="store_true", help="Odtworz testowy lokalny dzwiek z config.toml.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.test_sound:
            return send_test_sound(args.config)
        if args.test_telegram:
            return send_test_telegram(args.config)
        config = load_app_config(args.config)
        return run_once(config, force_dry_run=args.dry_run)
    except ConfigError as exc:
        print(f"BLAD: {exc}")
        return 1


def _min_interval_elapsed(
    *,
    last_alert_at: datetime | None,
    checked_at: datetime,
    minutes: int,
) -> bool:
    if last_alert_at is None:
        return True
    return checked_at - last_alert_at >= timedelta(minutes=minutes)


def _format_source_date(currency_rate: CurrencyRate) -> str:
    if currency_rate.source_date is None:
        return "brak w odpowiedzi PKO"
    return currency_rate.source_date.astimezone().strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    raise SystemExit(main())
