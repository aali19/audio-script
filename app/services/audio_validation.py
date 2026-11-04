import json
import math
import subprocess
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.domain.errors import (
    AudioDurationExceededError,
    InvalidAudioError,
    MediaInspectionUnavailableError,
    UnsupportedAudioFormatError,
)
from app.domain.models import AudioMetadata


class FFprobeAudioValidator:
    _SUPPORTED_FORMATS = {"wav", "mp3"}

    def __init__(self, settings: Settings) -> None:
        self._ffprobe_path = settings.ffprobe_path
        self._timeout = settings.ffprobe_timeout_seconds
        self._max_duration = settings.max_duration_seconds

    def validate(self, audio_path: Path) -> AudioMetadata:
        command = [
            self._ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration:stream=codec_name,codec_type",
            "-of",
            "json",
            str(audio_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise MediaInspectionUnavailableError() from exc

        if completed.returncode != 0:
            raise InvalidAudioError()

        try:
            payload: dict[str, Any] = json.loads(completed.stdout)
            format_data = payload["format"]
            formats = {
                value.strip().lower()
                for value in str(format_data["format_name"]).split(",")
            }
            duration = float(format_data["duration"])
            audio_streams = [
                stream
                for stream in payload.get("streams", [])
                if stream.get("codec_type") == "audio"
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise InvalidAudioError() from exc

        if not formats.intersection(self._SUPPORTED_FORMATS):
            raise UnsupportedAudioFormatError()
        if not audio_streams:
            raise InvalidAudioError("The uploaded file contains no audio stream.")
        if not math.isfinite(duration) or duration <= 0:
            raise InvalidAudioError("The audio duration is invalid.")
        if duration > self._max_duration:
            raise AudioDurationExceededError(self._max_duration)

        return AudioMetadata(
            format_name=next(iter(formats.intersection(self._SUPPORTED_FORMATS))),
            codec_name=str(audio_streams[0].get("codec_name", "unknown")),
            duration_seconds=duration,
        )
