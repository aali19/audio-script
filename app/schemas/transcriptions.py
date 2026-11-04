from pydantic import BaseModel, Field


class TranscriptSegmentResponse(BaseModel):
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(ge=0)
    text: str


class TranscriptionResponse(BaseModel):
    language: str | None
    language_probability: float | None = Field(default=None, ge=0, le=1)
    duration_seconds: float = Field(gt=0)
    text: str
    segments: list[TranscriptSegmentResponse]


class HealthResponse(BaseModel):
    status: str
