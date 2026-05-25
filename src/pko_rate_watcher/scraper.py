from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "PKO-Rate-Watcher/0.1 (+local informational alert script)"
)
RATE_NUMBER_RE = re.compile(r"\d+[,.]\d{2,6}")
CANTOR_API_PATH = "/api/modules/fxrates/cantor"


class ScraperError(RuntimeError):
    """Raised when the public PKO BP rate page cannot be read."""


class RateNotFoundError(ScraperError):
    """Raised when a requested currency rate is not present in page text."""


@dataclass(frozen=True)
class CurrencyRate:
    currency: str
    buy: Decimal
    sell: Decimal
    source_date: datetime | None = None


def fetch_html(url: str, timeout_seconds: int = 20) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ScraperError(f"Nie udalo sie pobrac strony PKO BP: {exc}") from exc

    return response.text


def extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def fetch_currency_rate(url: str, currency: str) -> CurrencyRate:
    return fetch_cantor_currency_rate(url, currency)


def fetch_cantor_currency_rate(page_url: str, currency: str) -> CurrencyRate:
    api_url = urljoin(page_url, CANTOR_API_PATH)
    try:
        response = requests.get(
            api_url,
            headers={
                "User-Agent": USER_AGENT,
                "Referer": page_url,
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            },
            params={"_": int(datetime.now().timestamp())},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise ScraperError(f"Nie udalo sie pobrac publicznych kursow kantoru PKO BP: {exc}") from exc
    except ValueError as exc:
        raise ScraperError("Publiczne kursy kantoru PKO BP nie sa poprawnym JSON.") from exc

    return parse_cantor_rates_payload(payload, currency)


def fetch_currency_rate_from_html(url: str, currency: str) -> CurrencyRate:
    html = fetch_html(url)
    text = extract_visible_text(html)
    return parse_rates_from_text(text, currency)


def parse_cantor_rates_payload(payload: dict[str, Any], currency: str) -> CurrencyRate:
    normalized_currency = currency.strip().upper()
    expected_pair = f"{normalized_currency}PLN"
    rates = payload.get("rates")
    if not isinstance(rates, list):
        raise RateNotFoundError("Publiczne dane kantoru PKO BP nie zawieraja listy kursow.")

    for item in rates:
        if not isinstance(item, dict):
            continue
        if str(item.get("currency_pair", "")).upper() != expected_pair:
            continue

        bid_price = item.get("bid_price")
        ask_price = item.get("ask_price")
        if bid_price is None or ask_price is None:
            raise RateNotFoundError(f"Nie znaleziono pelnego kursu {normalized_currency}/PLN w danych kantoru.")

        return CurrencyRate(
            currency=normalized_currency,
            # The public PKO BP cantor card labels customer actions:
            # "Kupno" is the ask price, "Sprzedaz" is the bid price.
            buy=_to_decimal(str(ask_price)),
            sell=_to_decimal(str(bid_price)),
            source_date=_parse_source_date(payload.get("date")),
        )

    raise RateNotFoundError(f"Nie znaleziono kursu {normalized_currency}/PLN w publicznych danych kantoru.")


def parse_rates_from_text(text: str, currency: str) -> CurrencyRate:
    """Parse buy/sell rates from visible page text.

    If PKO BP changes the public page structure, this parser may need to be
    updated to match the new layout.
    """

    normalized_currency = currency.strip().upper()
    for line in _candidate_lines(text):
        rate = _parse_line_for_currency(line, normalized_currency)
        if rate is not None:
            return rate

    flattened = " ".join(text.split())
    match = re.search(rf"\b{re.escape(normalized_currency)}\b(?:\s*/\s*PLN)?(?P<tail>.{{0,240}})", flattened, re.IGNORECASE)
    if match:
        numbers = RATE_NUMBER_RE.findall(match.group("tail"))
        if len(numbers) >= 2:
            return CurrencyRate(
                currency=normalized_currency,
                buy=_to_decimal(numbers[0]),
                sell=_to_decimal(numbers[1]),
            )

    raise RateNotFoundError(
        f"Nie znaleziono kursu {normalized_currency} w publicznym tekście strony PKO BP."
    )


def _candidate_lines(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    joined_neighbors: list[str] = []
    for index, line in enumerate(lines):
        joined_neighbors.append(line)
        if index + 2 < len(lines):
            joined_neighbors.append(" ".join(lines[index : index + 3]))
        if index + 5 < len(lines):
            joined_neighbors.append(" ".join(lines[index : index + 6]))
    return joined_neighbors


def _parse_line_for_currency(line: str, currency: str) -> CurrencyRate | None:
    match = re.search(rf"\b{re.escape(currency)}\b", line, re.IGNORECASE)
    if not match:
        return None

    numbers = RATE_NUMBER_RE.findall(line[match.end() :])
    if len(numbers) < 2:
        return None

    return CurrencyRate(
        currency=currency,
        buy=_to_decimal(numbers[0]),
        sell=_to_decimal(numbers[1]),
    )


def _to_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise ScraperError(f"Nieprawidlowa wartosc kursu: {value}") from exc


def _parse_source_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
