import math
import threading
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.domain.errors import TranscriptionUnavailableError
from app.domain.models import ProviderTranscription, TranscriptSegment


class FasterWhisperProvider:
    """Lazy, process-local Faster-Whisper adapter with bounded concurrency."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._model: Any | None = None
        self._model_lock = threading.Lock()
        self._capacity = threading.BoundedSemaphore(settings.transcription_concurrency)

    def _create_model(self) -> Any:
        from faster_whisper import WhisperModel

        kwargs: dict[str, Any] = {
            "device": self._settings.whisper_device,
            "compute_type": self._settings.whisper_compute_type,
        }
        if self._settings.whisper_download_root is not None:
            kwargs["download_root"] = str(self._settings.whisper_download_root)
        return WhisperModel(self._settings.whisper_model, **kwargs)

    def _get_model(self) -> Any:
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._model = self._create_model()
        return self._model

    def transcribe(self, audio_path: Path) -> ProviderTranscription:
        acquired = self._capacity.acquire(
            timeout=self._settings.transcription_acquire_timeout_seconds
        )
        if not acquired:
            raise TranscriptionUnavailableError(
                "Transcription capacity is currently busy; retry later."
            )

        try:
            model = self._get_model()
            raw_segments, info = model.transcribe(
                str(audio_path),
                beam_size=self._settings.whisper_beam_size,
                vad_filter=True,
            )
            segments: list[TranscriptSegment] = []
            for segment in raw_segments:
                start = float(segment.start)
                end = float(segment.end)
                if not math.isfinite(start) or not math.isfinite(end):
                    continue
                segments.append(
                    TranscriptSegment(
                        start_seconds=max(0.0, start),
                        end_seconds=max(max(0.0, start), end),
                        text=str(segment.text).strip(),
                    )
                )

            probability = getattr(info, "language_probability", None)
            return ProviderTranscription(
                language=getattr(info, "language", None),
                language_probability=(
                    float(probability) if probability is not None else None
                ),
                segments=tuple(segments),
            )
        except TranscriptionUnavailableError:
            raise
        except Exception as exc:
            raise TranscriptionUnavailableError() from exc
        finally:
            self._capacity.release()
