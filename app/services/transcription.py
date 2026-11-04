from pathlib import Path

from app.domain.models import TranscriptionResult
from app.providers.base import TranscriptionProvider
from app.services.audio_validation import FFprobeAudioValidator


class AudioTranscriptionService:
    def __init__(
        self,
        validator: FFprobeAudioValidator,
        provider: TranscriptionProvider,
    ) -> None:
        self._validator = validator
        self._provider = provider

    def transcribe_file(self, audio_path: Path) -> TranscriptionResult:
        metadata = self._validator.validate(audio_path)
        provider_result = self._provider.transcribe(audio_path)
        full_text = " ".join(
            segment.text for segment in provider_result.segments if segment.text
        )
        return TranscriptionResult(
            language=provider_result.language,
            language_probability=provider_result.language_probability,
            duration_seconds=metadata.duration_seconds,
            text=full_text,
            segments=provider_result.segments,
        )
