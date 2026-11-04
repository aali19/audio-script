from pathlib import Path

import pytest

from app.core.config import Settings


def test_settings_load_values_from_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUDIO_MAX_UPLOAD_BYTES", raising=False)
    monkeypatch.delenv("AUDIO_WHISPER_MODEL", raising=False)
    (tmp_path / ".env").write_text(
        "AUDIO_MAX_UPLOAD_BYTES=12345\nAUDIO_WHISPER_MODEL=tiny\n",
        encoding="utf-8",
    )

    settings = Settings()

    assert settings.max_upload_bytes == 12345
    assert settings.whisper_model == "tiny"


def test_process_environment_overrides_dotenv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "AUDIO_TRANSCRIPTION_CONCURRENCY=2\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AUDIO_TRANSCRIPTION_CONCURRENCY", "3")

    settings = Settings()

    assert settings.transcription_concurrency == 3
