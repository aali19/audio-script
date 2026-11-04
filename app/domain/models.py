from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    format_name: str
    codec_name: str
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True, slots=True)
class ProviderTranscription:
    language: str | None
    language_probability: float | None
    segments: tuple[TranscriptSegment, ...]


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    language: str | None
    language_probability: float | None
    duration_seconds: float
    text: str
    segments: tuple[TranscriptSegment, ...]
