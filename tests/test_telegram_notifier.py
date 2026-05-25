import pytest

from pko_rate_watcher.telegram_notifier import TelegramError, send_telegram_message


def test_telegram_error_does_not_include_bot_token(monkeypatch) -> None:
    token = "123456789:secret-token"

    class FakeResponse:
        status_code = 500
        text = f"server error for https://api.telegram.org/bot{token}/sendMessage"

        def json(self) -> dict[str, object]:
            return {"ok": False, "description": "Internal Server Error"}

    def fake_post(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("pko_rate_watcher.telegram_notifier.requests.post", fake_post)

    with pytest.raises(TelegramError) as exc_info:
        send_telegram_message(bot_token=token, chat_id="123", message="test")

    assert token not in str(exc_info.value)
