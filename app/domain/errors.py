class ApplicationError(Exception):
    code = "application_error"
    message = "The request could not be completed."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class EmptyUploadError(ApplicationError):
    code = "empty_upload"
    message = "The uploaded audio file is empty."


class UploadTooLargeError(ApplicationError):
    code = "upload_too_large"

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"The audio file exceeds the {max_bytes}-byte upload limit.")


class UnsupportedAudioFormatError(ApplicationError):
    code = "unsupported_audio_format"
    message = "Only valid WAV and MP3 audio files are supported."


class InvalidAudioError(ApplicationError):
    code = "invalid_audio"
    message = "The audio file is corrupt or unreadable."


class AudioDurationExceededError(ApplicationError):
    code = "audio_duration_exceeded"

    def __init__(self, max_seconds: float) -> None:
        super().__init__(
            f"The audio duration exceeds the {max_seconds:g}-second limit."
        )


class MediaInspectionUnavailableError(ApplicationError):
    code = "media_inspection_unavailable"
    message = "Audio validation is temporarily unavailable."


class TranscriptionUnavailableError(ApplicationError):
    code = "transcription_unavailable"
    message = "Audio transcription is temporarily unavailable."
