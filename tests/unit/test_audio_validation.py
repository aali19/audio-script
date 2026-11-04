import json
import subprocess
from pathlib import Path

import pytest

from app.core.config import Settings
from app.domain.errors import (
    AudioDurationExceededError,
    InvalidAudioError,
    UnsupportedAudioFormatError,
)
from app.services.audio_validation import FFprobeAudioValidator


def completed(payload: dict, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["ffprobe"], returncode=returncode, stdout=json.dumps(payload), stderr=""
    )


def test_valid_wav_metadata_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "format": {"format_name": "wav", "duration": "3.25"},
        "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}],
    }
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed(payload))

    metadata = FFprobeAudioValidator(Settings()).validate(Path("sample.bin"))

    assert metadata.format_name == "wav"
    assert metadata.duration_seconds == 3.25


def test_non_audio_format_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "format": {"format_name": "matroska,webm", "duration": "3"},
        "streams": [{"codec_type": "audio", "codec_name": "opus"}],
    }
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed(payload))

    with pytest.raises(UnsupportedAudioFormatError):
        FFprobeAudioValidator(Settings()).validate(Path("sample.bin"))


def test_corrupt_audio_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed({}, returncode=1),
    )

    with pytest.raises(InvalidAudioError):
        FFprobeAudioValidator(Settings()).validate(Path("sample.bin"))


def test_duration_limit_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "format": {"format_name": "mp3", "duration": "11"},
        "streams": [{"codec_type": "audio", "codec_name": "mp3"}],
    }
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: completed(payload))

    with pytest.raises(AudioDurationExceededError):
        FFprobeAudioValidator(Settings(max_duration_seconds=10)).validate(
            Path("sample.bin")
        )
