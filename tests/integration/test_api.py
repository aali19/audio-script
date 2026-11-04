from pathlib import Path

from fastapi.testclient import TestClient

from app.api.dependencies import get_transcription_service, get_upload_storage
from app.core.config import Settings
from app.domain.errors import InvalidAudioError
from app.domain.models import TranscriptionResult, TranscriptSegment
from app.main import create_app
from app.services.uploads import TemporaryUploadStorage


class SuccessfulService:
    def __init__(self) -> None:
        self.path_seen: Path | None = None

    def transcribe_file(self, audio_path: Path) -> TranscriptionResult:
        assert audio_path.exists()
        self.path_seen = audio_path
        segment = TranscriptSegment(0.0, 1.25, "Hello world.")
        return TranscriptionResult(
            language="en",
            language_probability=0.98,
            duration_seconds=1.25,
            text="Hello world.",
            segments=(segment,),
        )


class InvalidService:
    def transcribe_file(self, _audio_path: Path) -> TranscriptionResult:
        raise InvalidAudioError()


class FailingService:
    def __init__(self) -> None:
        self.path_seen: Path | None = None

    def transcribe_file(self, audio_path: Path) -> TranscriptionResult:
        self.path_seen = audio_path
        raise RuntimeError("provider details that must not leak")


def build_client(tmp_path: Path, service: object, max_bytes: int = 1024) -> TestClient:
    app = create_app()
    storage = TemporaryUploadStorage(
        Settings(
            temp_directory=tmp_path,
            max_upload_bytes=max_bytes,
            upload_chunk_size=2,
        )
    )
    app.dependency_overrides[get_upload_storage] = lambda: storage
    app.dependency_overrides[get_transcription_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_health_endpoint(tmp_path: Path) -> None:
    response = build_client(tmp_path, SuccessfulService()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_transcription_contract_and_cleanup(tmp_path: Path) -> None:
    service = SuccessfulService()
    client = build_client(tmp_path, service)

    response = client.post(
        "/api/v1/transcriptions",
        files={"file": ("recording.wav", b"fake audio", "audio/wav")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "language": "en",
        "language_probability": 0.98,
        "duration_seconds": 1.25,
        "text": "Hello world.",
        "segments": [
            {
                "start_seconds": 0.0,
                "end_seconds": 1.25,
                "text": "Hello world.",
            }
        ],
    }
    assert service.path_seen is not None
    assert not service.path_seen.exists()


def test_missing_file_has_structured_error(tmp_path: Path) -> None:
    response = build_client(tmp_path, SuccessfulService()).post(
        "/api/v1/transcriptions"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_request"


def test_oversized_upload_has_structured_error_and_is_removed(tmp_path: Path) -> None:
    response = build_client(tmp_path, SuccessfulService(), max_bytes=4).post(
        "/api/v1/transcriptions",
        files={"file": ("large.mp3", b"12345", "audio/mpeg")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "upload_too_large"
    assert list(tmp_path.iterdir()) == []


def test_invalid_audio_error_is_mapped(tmp_path: Path) -> None:
    response = build_client(tmp_path, InvalidService()).post(
        "/api/v1/transcriptions",
        files={"file": ("broken.wav", b"broken", "audio/wav")},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "invalid_audio",
            "message": "The audio file is corrupt or unreadable.",
        }
    }


def test_unexpected_failure_is_hidden_and_temp_file_is_removed(tmp_path: Path) -> None:
    service = FailingService()
    response = build_client(tmp_path, service).post(
        "/api/v1/transcriptions",
        files={"file": ("recording.wav", b"audio", "audio/wav")},
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "provider details" not in response.text
    assert service.path_seen is not None
    assert not service.path_seen.exists()
