from pko_rate_watcher.main import send_test_sound
from pko_rate_watcher.sound_notifier import SoundResult


def test_send_test_sound_uses_local_sound_config_without_fetching_rates(tmp_path, monkeypatch, capsys) -> None:
    config_file = tmp_path / "config.toml"
    log_file = tmp_path / "rate_watcher.log"
    config_file.write_text(
        f"""
[watcher]
url = "https://example.test"
target_rate = 3.60
log_file = "{log_file.as_posix()}"

[alerts]

[local_sound]
enabled = true
mode = "message_beep"
frequency = 1000
duration_ms = 700
wav_file = ""
""",
        encoding="utf-8",
    )

    called = {}

    def fake_play(local_sound_config):
        called["mode"] = local_sound_config.mode
        return SoundResult(True, "Local sound played: message_beep.")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("network or telegram should not be called in --test-sound")

    monkeypatch.setattr("pko_rate_watcher.main.play_local_sound", fake_play)
    monkeypatch.setattr("pko_rate_watcher.main.fetch_currency_rate", fail_if_called)
    monkeypatch.setattr("pko_rate_watcher.main.send_telegram_message", fail_if_called)

    exit_code = send_test_sound(config_file)

    assert exit_code == 0
    assert called == {"mode": "message_beep"}
    assert "Local sound played: message_beep." in capsys.readouterr().out
