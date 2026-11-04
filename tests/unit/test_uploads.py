from pathlib import Path

import pytest

from app.core.config import Settings
from app.domain.errors import EmptyUploadError, UploadTooLargeError
from app.services.uploads import TemporaryUploadStorage


class ByteStream:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        if self._offset >= len(self._content):
            return b""
        end = len(self._content) if size < 0 else self._offset + size
        chunk = self._content[self._offset : end]
        self._offset += len(chunk)
        return chunk


@pytest.mark.asyncio
async def test_upload_is_chunked_and_removed(tmp_path: Path) -> None:
    storage = TemporaryUploadStorage(
        Settings(temp_directory=tmp_path, max_upload_bytes=10, upload_chunk_size=2)
    )

    async with storage.store(ByteStream(b"audio")) as upload:
        saved_path = upload.path
        assert saved_path.read_bytes() == b"audio"
        assert upload.size_bytes == 5

    assert not saved_path.exists()


@pytest.mark.asyncio
async def test_oversized_upload_is_rejected_and_removed(tmp_path: Path) -> None:
    storage = TemporaryUploadStorage(
        Settings(temp_directory=tmp_path, max_upload_bytes=4, upload_chunk_size=2)
    )

    with pytest.raises(UploadTooLargeError):
        async with storage.store(ByteStream(b"audio")):
            pass

    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_empty_upload_is_rejected_and_removed(tmp_path: Path) -> None:
    storage = TemporaryUploadStorage(Settings(temp_directory=tmp_path))

    with pytest.raises(EmptyUploadError):
        async with storage.store(ByteStream(b"")):
            pass

    assert list(tmp_path.iterdir()) == []
