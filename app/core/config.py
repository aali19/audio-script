from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from .env and AUDIO_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="AUDIO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Audio Transcription API"
    max_upload_bytes: int = Field(default=500 * 1024 * 1024, gt=0)
    max_duration_seconds: float = Field(default=4 * 60 * 60, gt=0)
    upload_chunk_size: int = Field(default=1024 * 1024, gt=0)
    temp_directory: Path | None = None
    ffprobe_path: str = "ffprobe"
    ffprobe_timeout_seconds: float = Field(default=30.0, gt=0)
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_download_root: Path | None = None
    whisper_beam_size: int = Field(default=5, gt=0)
    transcription_concurrency: int = Field(default=1, gt=0)
    transcription_acquire_timeout_seconds: float = Field(default=1.0, ge=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
