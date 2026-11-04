from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from starlette.concurrency import run_in_threadpool

from app.api.dependencies import get_transcription_service, get_upload_storage
from app.schemas.errors import ErrorResponse
from app.schemas.transcriptions import TranscriptionResponse
from app.services.transcription import AudioTranscriptionService
from app.services.uploads import TemporaryUploadStorage

router = APIRouter(prefix="/api/v1", tags=["transcriptions"])


@router.post(
    "/transcriptions",
    response_model=TranscriptionResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def create_transcription(
    file: Annotated[UploadFile, File(description="A WAV or MP3 audio file")],
    service: Annotated[AudioTranscriptionService, Depends(get_transcription_service)],
    storage: Annotated[TemporaryUploadStorage, Depends(get_upload_storage)],
) -> TranscriptionResponse:
    try:
        async with storage.store(file) as upload:
            result = await run_in_threadpool(service.transcribe_file, upload.path)
            return TranscriptionResponse.model_validate(result, from_attributes=True)
    finally:
        await file.close()
