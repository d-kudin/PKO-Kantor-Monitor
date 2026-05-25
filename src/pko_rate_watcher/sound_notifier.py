from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any

from pko_rate_watcher.config import LocalSoundConfig


@dataclass(frozen=True)
class SoundResult:
    success: bool
    message: str


def play_local_sound(
    config: LocalSoundConfig,
    *,
    winsound_module: Any | None = None,
    sleep_func: Any = sleep,
) -> SoundResult:
    if not config.enabled:
        return SoundResult(False, "Local sound is disabled in config.toml.")

    winsound = winsound_module if winsound_module is not None else _load_winsound()
    if winsound is None:
        return SoundResult(False, "Local sound is available only on Windows.")

    mode = config.mode.strip().lower()

    try:
        if mode == "message_beep":
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            return SoundResult(True, "Local sound played: message_beep.")

        if mode == "beep":
            winsound.Beep(config.frequency, config.duration_ms)
            return SoundResult(True, "Local sound played: beep.")

        if mode == "alert_sequence":
            pattern = [
                (880, 220, 0.09),
                (1175, 260, 0.09),
                (988, 220, 0.12),
                (1319, 520, 0.12),
                (1047, 700, 0),
            ]
            for frequency, duration_ms, pause_seconds in pattern:
                winsound.Beep(frequency, duration_ms)
                if pause_seconds:
                    sleep_func(pause_seconds)
            return SoundResult(True, "Local sound played: alert_sequence.")

        if mode == "aurora":
            pattern = [
                (659, 360, 0.08),
                (784, 420, 0.08),
                (988, 480, 0.1),
                (784, 420, 0.12),
                (1047, 760, 0),
            ]
            for frequency, duration_ms, pause_seconds in pattern:
                winsound.Beep(frequency, duration_ms)
                if pause_seconds:
                    sleep_func(pause_seconds)
            return SoundResult(True, "Local sound played: aurora.")

        if mode == "wav":
            wav_file = Path(config.wav_file)
            if not wav_file.exists():
                return SoundResult(False, f"WAV file does not exist: {wav_file}")
            winsound.PlaySound(str(wav_file), winsound.SND_FILENAME)
            return SoundResult(True, f"Local sound played: {wav_file}")

        return SoundResult(False, f"Unknown local sound mode: {config.mode}")
    except RuntimeError as exc:
        return SoundResult(False, f"Local sound failed: {exc}")


def _load_winsound() -> Any | None:
    if not sys.platform.startswith("win"):
        return None
    try:
        import winsound
    except ImportError:
        return None
    return winsound
