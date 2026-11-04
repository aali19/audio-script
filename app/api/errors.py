import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.errors import (
    ApplicationError,
    AudioDurationExceededError,
    EmptyUploadError,
    InvalidAudioError,
    MediaInspectionUnavailableError,
    TranscriptionUnavailableError,
    UnsupportedAudioFormatError,
    UploadTooLargeError,
)

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: tuple[tuple[type[ApplicationError], int], ...] = (
    (EmptyUploadError, 400),
    (UploadTooLargeError, 413),
    (UnsupportedAudioFormatError, 415),
    (InvalidAudioError, 422),
    (AudioDurationExceededError, 422),
    (MediaInspectionUnavailableError, 503),
    (TranscriptionUnavailableError, 503),
)


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(
        _request: Request, exc: ApplicationError
    ) -> JSONResponse:
        status_code = next(
            (
                status
                for error_type, status in _STATUS_BY_ERROR
                if isinstance(exc, error_type)
            ),
            500,
        )
        return _error_response(status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            400, "invalid_request", "A multipart upload field named 'file' is required."
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unexpected request failure", exc_info=exc)
        return _error_response(
            500, "internal_error", "An unexpected internal error occurred."
        )
