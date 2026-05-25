from decimal import Decimal

import pytest

from pko_rate_watcher.scraper import (
    RateNotFoundError,
    fetch_cantor_currency_rate,
    parse_cantor_rates_payload,
    parse_rates_from_text,
)


def test_parse_rates_from_text_finds_usd_with_decimal_commas() -> None:
    text = "Waluta Kupno Sprzedaz\nUSD 3,7500 3,7900\nEUR 4,2500 4,3100"

    rate = parse_rates_from_text(text, "USD")

    assert rate.currency == "USD"
    assert rate.buy == Decimal("3.7500")
    assert rate.sell == Decimal("3.7900")


def test_parse_rates_from_text_finds_usd_with_decimal_dots() -> None:
    text = "USD / PLN kupno 3.7512 sprzedaz 3.8034"

    rate = parse_rates_from_text(text, "usd")

    assert rate.buy == Decimal("3.7512")
    assert rate.sell == Decimal("3.8034")


def test_parse_rates_from_text_does_not_use_previous_currency_values() -> None:
    text = "\n".join(
        [
            "Kursy walut",
            "Kupno",
            "Sprzedaz",
            "CHF",
            "4.5053",
            "4.7839",
            "USD",
            "3.4904",
            "3.8193",
        ]
    )

    rate = parse_rates_from_text(text, "USD")

    assert rate.buy == Decimal("3.4904")
    assert rate.sell == Decimal("3.8193")


def test_parse_cantor_rates_payload_maps_usd_card_labels() -> None:
    payload = {
        "date": "2026-05-22T19:09:58+02:00",
        "rates": [
            {
                "currency_pair": "CHFPLN",
                "bid_price": "4.6300",
                "ask_price": "4.6704",
            },
            {
                "currency_pair": "USDPLN",
                "bid_price": "3.6298",
                "ask_price": "3.6694",
            },
        ],
    }

    rate = parse_cantor_rates_payload(payload, "USD")

    assert rate.currency == "USD"
    assert rate.buy == Decimal("3.6694")
    assert rate.sell == Decimal("3.6298")
    assert rate.source_date is not None
    assert rate.source_date.isoformat() == "2026-05-22T19:09:58+02:00"


def test_fetch_cantor_currency_rate_requests_uncached_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "date": "2026-05-22T20:04:59+02:00",
                "rates": [
                    {
                        "currency_pair": "USDPLN",
                        "bid_price": "3.6298",
                        "ask_price": "3.6694",
                    }
                ],
            }

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return FakeResponse()

    monkeypatch.setattr("pko_rate_watcher.scraper.requests.get", fake_get)

    rate = fetch_cantor_currency_rate("https://www.pkobp.pl/some-page", "USD")

    kwargs = captured["kwargs"]
    assert rate.sell == Decimal("3.6298")
    assert kwargs["headers"]["Cache-Control"] == "no-cache"
    assert kwargs["headers"]["Pragma"] == "no-cache"
    assert "_" in kwargs["params"]


def test_parse_rates_from_text_raises_clear_error_when_currency_missing() -> None:
    with pytest.raises(RateNotFoundError, match="Nie znaleziono kursu USD"):
        parse_rates_from_text("EUR 4,2500 4,3100", "USD")
