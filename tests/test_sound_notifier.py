from pathlib import Path

from pko_rate_watcher.config import LocalSoundConfig
from pko_rate_watcher.sound_notifier import play_local_sound


class FakeWinsound:
    MB_ICONEXCLAMATION = 48
    SND_FILENAME = 131072

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def MessageBeep(self, value: int) -> None:
        self.calls.append(("MessageBeep", (value,)))

    def Beep(self, frequency: int, duration_ms: int) -> None:
        self.calls.append(("Beep", (frequency, duration_ms)))

    def PlaySound(self, wav_file: str, flags: int) -> None:
        self.calls.append(("PlaySound", (wav_file, flags)))


def test_play_local_sound_returns_disabled_message() -> None:
    result = play_local_sound(LocalSoundConfig(enabled=False), winsound_module=FakeWinsound())

    assert result.success is False
    assert result.message == "Local sound is disabled in config.toml."


def test_play_local_sound_message_beep_uses_windows_message_beep() -> None:
    fake = FakeWinsound()

    result = play_local_sound(
        LocalSoundConfig(enabled=True, mode="message_beep"),
        winsound_module=fake,
    )

    assert result.success is True
    assert fake.calls == [("MessageBeep", (fake.MB_ICONEXCLAMATION,))]


def test_play_local_sound_beep_uses_configured_frequency_and_duration() -> None:
    fake = FakeWinsound()

    result = play_local_sound(
        LocalSoundConfig(enabled=True, mode="beep", frequency=1200, duration_ms=400),
        winsound_module=fake,
    )

    assert result.success is True
    assert fake.calls == [("Beep", (1200, 400))]


def test_play_local_sound_alert_sequence_uses_longer_beep_pattern() -> None:
    fake = FakeWinsound()
    sleeps: list[float] = []

    result = play_local_sound(
        LocalSoundConfig(enabled=True, mode="alert_sequence"),
        winsound_module=fake,
        sleep_func=sleeps.append,
    )

    assert result.success is True
    assert result.message == "Local sound played: alert_sequence."
    assert fake.calls == [
        ("Beep", (880, 220)),
        ("Beep", (1175, 260)),
        ("Beep", (988, 220)),
        ("Beep", (1319, 520)),
        ("Beep", (1047, 700)),
    ]
    assert sleeps == [0.09, 0.09, 0.12, 0.12]


def test_play_local_sound_aurora_uses_soft_longer_beep_pattern() -> None:
    fake = FakeWinsound()
    sleeps: list[float] = []

    result = play_local_sound(
        LocalSoundConfig(enabled=True, mode="aurora"),
        winsound_module=fake,
        sleep_func=sleeps.append,
    )

    assert result.success is True
    assert result.message == "Local sound played: aurora."
    assert fake.calls == [
        ("Beep", (659, 360)),
        ("Beep", (784, 420)),
        ("Beep", (988, 480)),
        ("Beep", (784, 420)),
        ("Beep", (1047, 760)),
    ]
    assert sleeps == [0.08, 0.08, 0.1, 0.12]


def test_play_local_sound_wav_requires_existing_file(tmp_path: Path) -> None:
    result = play_local_sound(
        LocalSoundConfig(enabled=True, mode="wav", wav_file=str(tmp_path / "missing.wav")),
        winsound_module=FakeWinsound(),
    )

    assert result.success is False
    assert "WAV file does not exist" in result.message


def test_play_local_sound_unknown_mode_is_readable_error() -> None:
    result = play_local_sound(
        LocalSoundConfig(enabled=True, mode="unknown"),
        winsound_module=FakeWinsound(),
    )

    assert result.success is False
    assert result.message == "Unknown local sound mode: unknown"
