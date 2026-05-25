from __future__ import annotations

import requests


class TelegramError(RuntimeError):
    """Raised when Telegram Bot API rejects or fails a sendMessage call."""


def send_telegram_message(
    *,
    bot_token: str,
    chat_id: str,
    message: str,
    timeout_seconds: int = 15,
) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, data=payload, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise TelegramError(
            f"Telegram API nie przyjelo wiadomosci: {exc.__class__.__name__}"
        ) from None

    try:
        body = response.json()
    except ValueError as exc:
        if response.status_code >= 400:
            raise TelegramError(
                f"Telegram API zwrocilo status HTTP {response.status_code}."
            ) from None
        raise TelegramError("Telegram API zwrocilo nieprawidlowa odpowiedz JSON.") from None

    if response.status_code >= 400:
        description = body.get("description", "brak opisu bledu")
        raise TelegramError(
            f"Telegram API zwrocilo status HTTP {response.status_code}: {description}"
        )
    if body.get("ok") is not True:
        description = body.get("description", "brak opisu bledu")
        raise TelegramError(f"Telegram API zwrocilo blad: {description}")
