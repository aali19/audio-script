import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.domain.errors import EmptyUploadError, UploadTooLargeError


class AsyncReadable(Protocol):
    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True, slots=True)
class StoredUpload:
    path: Path
    size_bytes: int


class TemporaryUploadStorage:
    def __init__(self, settings: Settings) -> None:
        self._max_bytes = settings.max_upload_bytes
        self._chunk_size = settings.upload_chunk_size
        self._directory = settings.temp_directory

    @asynccontextmanager
    async def store(self, source: AsyncReadable) -> AsyncIterator[StoredUpload]:
        if self._directory is not None:
            self._directory.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(suffix=".audio", dir=self._directory)
        path = Path(raw_path)
        size = 0
        try:
            with os.fdopen(descriptor, "wb") as destination:
                while chunk := await source.read(self._chunk_size):
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise UploadTooLargeError(self._max_bytes)
                    destination.write(chunk)
            if size == 0:
                raise EmptyUploadError()
            yield StoredUpload(path=path, size_bytes=size)
        finally:
            path.unlink(missing_ok=True)
