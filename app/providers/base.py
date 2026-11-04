from pathlib import Path
from typing import Protocol

from app.domain.models import ProviderTranscription


class TranscriptionProvider(Protocol):
    def transcribe(self, audio_path: Path) -> ProviderTranscription: ...
