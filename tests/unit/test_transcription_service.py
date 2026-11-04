from pathlib import Path

from app.domain.models import (
    AudioMetadata,
    ProviderTranscription,
    TranscriptSegment,
)
from app.services.transcription import AudioTranscriptionService


class FakeValidator:
    def validate(self, _path: Path) -> AudioMetadata:
        return AudioMetadata("wav", "pcm_s16le", 5.0)


class FakeProvider:
    def __init__(self, segments: tuple[TranscriptSegment, ...]) -> None:
        self._segments = segments

    def transcribe(self, _path: Path) -> ProviderTranscription:
        return ProviderTranscription("en", 0.99, self._segments)


def test_segments_are_combined_into_complete_transcript() -> None:
    segments = (
        TranscriptSegment(0.0, 1.0, "Hello"),
        TranscriptSegment(1.0, 2.0, "world."),
    )
    service = AudioTranscriptionService(FakeValidator(), FakeProvider(segments))  # type: ignore[arg-type]

    result = service.transcribe_file(Path("audio.wav"))

    assert result.text == "Hello world."
    assert result.duration_seconds == 5.0
    assert result.segments == segments


def test_silent_audio_returns_empty_transcript() -> None:
    service = AudioTranscriptionService(FakeValidator(), FakeProvider(()))  # type: ignore[arg-type]

    result = service.transcribe_file(Path("silent.wav"))

    assert result.text == ""
    assert result.segments == ()
