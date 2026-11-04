from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routes.transcriptions import router as transcriptions_router
from app.core.config import get_settings
from app.schemas.transcriptions import HealthResponse


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Synchronous WAV/MP3 transcription using Faster-Whisper.",
    )
    register_exception_handlers(app)
    app.include_router(transcriptions_router)

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
