from pko_rate_watcher.config import load_app_config


def test_load_app_config_reads_local_sound_section(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[watcher]
url = "https://example.test"
target_rate = 3.60

[alerts]
min_minutes_between_alerts = 0
send_alert_when_condition_recovers = true

[local_sound]
enabled = true
mode = "beep"
frequency = 1200
duration_ms = 300
wav_file = ""
""",
        encoding="utf-8",
    )

    config = load_app_config(config_file)

    assert config.local_sound.enabled is True
    assert config.local_sound.mode == "beep"
    assert config.local_sound.frequency == 1200
    assert config.local_sound.duration_ms == 300
