# PKO USD Rate Watcher

Mały lokalny program dla Windows, który odczytuje publiczne kursy kantoru PKO BP widoczne na stronie, odczytuje kurs USD/PLN i wysyła alert przez Telegram Bot API, gdy kurs spełni skonfigurowany warunek.

Program:

- nie loguje się do banku,
- nie używa oficjalnego API banku ani logowania do banku,
- nie wykonuje żadnych transakcji,
- działa jako jedno sprawdzenie na jedno uruchomienie,
- nadaje się do uruchamiania cyklicznie przez Harmonogram zadań Windows.

Źródło kursu: publiczna strona PKO BP:
`https://www.pkobp.pl/klient-indywidualny/aplikacja-iko-ipko/kantor-internetowy-mobilny-24h`

W praktyce karta „Przykładowe kursy wymiany walut w kantorze internetowym” jest doładowywana przez publiczny moduł strony PKO BP. Program pobiera ten sam publiczny moduł, bez tokenów, logowania i dostępu do konta bankowego.

Kurs ma charakter poglądowy.

## 1. Instalacja Pythona na Windows

1. Wejdź na `https://www.python.org/downloads/windows/`.
2. Pobierz Python 3.12 lub nowszy.
3. Uruchom instalator.
4. Zaznacz opcję `Add python.exe to PATH`.
5. Kliknij `Install Now`.
6. Po instalacji otwórz PowerShell i sprawdź:

```powershell
python --version
```

Powinieneś zobaczyć wersję `Python 3.12.x` albo nowszą.

## 2. Utworzenie środowiska wirtualnego

W PowerShell przejdź do katalogu projektu i uruchom:

```powershell
python -m venv .venv
```

## 3. Aktywacja środowiska

```powershell
.\.venv\Scripts\Activate.ps1
```

Jeśli PowerShell blokuje aktywację skryptów, uruchom jednorazowo:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Potem ponownie aktywuj środowisko.

## 4. Instalacja zależności

```powershell
pip install -r requirements.txt
```

Ten krok instaluje biblioteki oraz lokalny pakiet, dzięki czemu działa polecenie:

```powershell
python -m pko_rate_watcher.main
```

Skopiuj przykładową konfigurację do lokalnego pliku:

```powershell
Copy-Item config.example.toml config.toml
```

Plik `config.toml` jest lokalny i wpisany w `.gitignore`, bo może zawierać Twoje progi alertów oraz lokalne preferencje.

## 5. Utworzenie bota Telegram

1. Otwórz Telegram.
2. Znajdź oficjalnego bota `@BotFather`.
3. Wyślij komendę:

```text
/newbot
```

4. Podaj nazwę bota.
5. Podaj username bota, który kończy się na `bot`, np. `moj_kantor_alert_bot`.
6. BotFather zwróci token. Skopiuj go. Nie publikuj go i nie commituj do repozytorium.

## 6. Uzyskanie TELEGRAM_CHAT_ID

1. Otwórz czat ze swoim nowym botem.
2. Wyślij do niego dowolną wiadomość, np. `test`.
3. W przeglądarce wejdź pod adres:

```text
https://api.telegram.org/bot<TOKEN>/getUpdates
```

Zamień `<TOKEN>` na token otrzymany od BotFather.

4. W odpowiedzi znajdź pole `chat.id`.
5. Skopiuj wartość `chat.id`.

## 7. Utworzenie pliku .env

Skopiuj plik `.env.example` do pliku `.env`:

```powershell
Copy-Item .env.example .env
```

Otwórz `.env` w edytorze tekstu i wpisz swoje dane:

```text
TELEGRAM_BOT_TOKEN=123456789:twoj_token
TELEGRAM_CHAT_ID=123456789
```

Plik `.env` jest wpisany w `.gitignore`, więc nie powinien trafić do repozytorium.

## 8. Test Telegrama

Po aktywacji środowiska uruchom:

```powershell
python -m pko_rate_watcher.main --test-telegram
```

Jeśli konfiguracja jest poprawna, bot wyśle wiadomość testową.

Test lokalnego dźwięku:

```powershell
python -m pko_rate_watcher.main --test-sound
```

To polecenie ładuje `config.toml`, czyta sekcję `[local_sound]`, próbuje odtworzyć dźwięk i kończy działanie bez pobierania strony PKO oraz bez wysyłania Telegrama.

## 9. Ręczne sprawdzenie kursu

```powershell
python -m pko_rate_watcher.main
```

Tryb dry-run, czyli sprawdzenie bez wysyłania alertu:

```powershell
python -m pko_rate_watcher.main --dry-run
```

Możesz też użyć innego pliku konfiguracyjnego:

```powershell
python -m pko_rate_watcher.main --config config.toml
```

## 10. Konfiguracja progu kursu

Edytuj `config.toml`:

```toml
[watcher]
currency = "USD"
rate_type = "sell"
condition = "below_or_equal"
target_rate = 3.80
dry_run = false

[alerts]
min_minutes_between_alerts = 0
send_alert_when_condition_recovers = true

[local_sound]
enabled = true
mode = "aurora"
frequency = 1000
duration_ms = 700
wav_file = ""
```

Znaczenie pól:

- `currency`: waluta, domyślnie `USD`,
- `rate_type`: `buy` dla wartości z karty `Kupno` albo `sell` dla wartości z karty `Sprzedaż`,
- `condition`: `below_or_equal` albo `above_or_equal`,
- `target_rate`: próg alertu,
- `min_minutes_between_alerts`: minimalny odstęp między kolejnymi alertami,
- `send_alert_when_condition_recovers`: gdy `true`, program ponawia alert po upływie minimalnego odstępu, nawet jeśli warunek cały czas jest spełniony.

Sekcja `[local_sound]`:

- `enabled`: `true` włącza lokalny dźwięk przy realnym alercie; `false` wyłącza dźwięk,
- `mode`: `aurora`, `alert_sequence`, `message_beep`, `beep` albo `wav`,
- `frequency`: częstotliwość dla `mode = "beep"`,
- `duration_ms`: czas trwania dla `mode = "beep"`,
- `wav_file`: ścieżka do pliku `.wav` dla `mode = "wav"`.

Tryb `aurora` jest domyślnie rekomendowany do alertów: odtwarza łagodniejszą, dłuższą sekwencję tonów i trwa około 2,5 sekundy. Tryb `alert_sequence` jest krótszy i bardziej alarmowy. Tryb `message_beep` jest krótkim systemowym dźwiękiem Windows.

Lokalny dźwięk jest odtwarzany tylko przy realnym alercie. Nie jest odtwarzany przy `--dry-run`, przy niespełnionym warunku ani wtedy, gdy alert blokuje logika antyspamowa.

Typowe ustawienia:

```toml
# Alert, gdy kurs Sprzedaż jest równy lub wyższy niż próg.
rate_type = "sell"
condition = "above_or_equal"
target_rate = 3.60
```

```toml
# Alert, gdy kurs Kupno jest równy lub niższy niż próg.
rate_type = "buy"
condition = "below_or_equal"
target_rate = 3.60
```

Jeśli chcesz alert przy każdym cyklicznym sprawdzeniu, ustaw brak dodatkowego odstępu między alertami:

```toml
[alerts]
min_minutes_between_alerts = 0
send_alert_when_condition_recovers = true
```

Wtedy przy zadaniu uruchamianym co 5 minut program wyśle alert przy każdym sprawdzeniu, o ile warunek nadal jest spełniony. Ręczne uruchomienie programu też może wtedy wysłać alert, jeśli warunek jest spełniony.

Jeśli chcesz tylko jeden alert na jeden okres spełnienia warunku, ustaw:

```toml
[alerts]
min_minutes_between_alerts = 360
send_alert_when_condition_recovers = false
```

## 11. Harmonogram zadań Windows

1. Otwórz Start.
2. Wyszukaj `Harmonogram zadań`.
3. Kliknij `Utwórz zadanie`.
4. Na karcie `Ogólne` wpisz nazwę, np. `PKO USD Rate Watcher`.
5. Na karcie `Wyzwalacze` kliknij `Nowy`.
6. Ustaw rozpoczęcie zadania, np. dzisiaj.
7. Zaznacz `Powtarzaj zadanie co:` i wybierz `5 minut`.
8. Ustaw czas trwania na `Bez końca`.
9. Na karcie `Akcje` kliknij `Nowa`.
10. W polu `Program/skrypt` wpisz pełną ścieżkę do Pythona z `.venv`, np.:

```text
C:\Users\TwojUser\projekty\pko-usd-rate-watcher\.venv\Scripts\python.exe
```

11. W polu `Dodaj argumenty` wpisz:

```text
-m pko_rate_watcher.main
```

12. W polu `Rozpocznij w` wpisz pełną ścieżkę do katalogu projektu, np.:

```text
C:\Users\TwojUser\projekty\pko-usd-rate-watcher
```

13. Zapisz zadanie.

## 12. Logi i stan

Logi są zapisywane w:

```text
logs/rate_watcher.log
```

Stan alertów jest zapisywany w:

```text
state/state.json
```

W stanie znajdują się między innymi:

- ostatni odczytany kurs,
- czas ostatniego sprawdzenia,
- czas ostatniego alertu,
- informacja, czy alert dla obecnego spełnienia warunku został już wysłany.

## 13. Zatrzymanie monitorowania

Program nie działa w tle jako pętla. Monitorowanie zatrzymasz przez wyłączenie zadania w Harmonogramie zadań Windows:

1. Otwórz `Harmonogram zadań`.
2. Znajdź zadanie `PKO USD Rate Watcher`.
3. Kliknij prawym przyciskiem.
4. Wybierz `Wyłącz`.

## Bezpieczeństwo

- Nie zapisuj tokena Telegrama w kodzie.
- Nie commituj pliku `.env`.
- Program nie loguje tokena Telegrama.
- Program nie loguje pełnego URL-a Telegram API z tokenem.
- Program nie prosi o login ani hasło do banku.
- Program nie wykonuje żadnych transakcji.
- Program służy wyłącznie do alertów informacyjnych.

## Testy

Po instalacji zależności możesz uruchomić testy:

```powershell
pytest -q
```
