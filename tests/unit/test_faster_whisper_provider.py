from pathlib import Path
from types import SimpleNamespace

from app.core.config import Settings
from app.providers.faster_whisper import FasterWhisperProvider


class FakeModel:
    def transcribe(self, _path: str, **_kwargs: object):
        segments = iter([SimpleNamespace(start=0.0, end=1.5, text=" hello ")])
        info = SimpleNamespace(language="en", language_probability=0.9)
        return segments, info


class StubProvider(FasterWhisperProvider):
    creations = 0

    def _create_model(self) -> FakeModel:
        self.creations += 1
        return FakeModel()


def test_model_is_loaded_once_and_segments_are_normalized() -> None:
    provider = StubProvider(Settings())

    first = provider.transcribe(Path("one.wav"))
    second = provider.transcribe(Path("two.wav"))

    assert provider.creations == 1
    assert first.segments[0].text == "hello"
    assert second.language == "en"
