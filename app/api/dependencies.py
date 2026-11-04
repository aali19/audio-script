from functools import lru_cache

from app.core.config import get_settings
from app.providers.faster_whisper import FasterWhisperProvider
from app.services.audio_validation import FFprobeAudioValidator
from app.services.transcription import AudioTranscriptionService
from app.services.uploads import TemporaryUploadStorage


@lru_cache
def get_transcription_provider() -> FasterWhisperProvider:
    return FasterWhisperProvider(get_settings())


@lru_cache
def get_audio_validator() -> FFprobeAudioValidator:
    return FFprobeAudioValidator(get_settings())


@lru_cache
def get_transcription_service() -> AudioTranscriptionService:
    return AudioTranscriptionService(
        validator=get_audio_validator(),
        provider=get_transcription_provider(),
    )


@lru_cache
def get_upload_storage() -> TemporaryUploadStorage:
    return TemporaryUploadStorage(get_settings())
