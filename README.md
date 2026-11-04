# Audio Transcription API

A minimal FastAPI service that validates WAV/MP3 uploads with FFprobe and
transcribes them with Faster-Whisper. It streams uploads to local temporary
storage, limits expensive work per process, and removes temporary files on every
success and failure path.

## Implemented baseline

- `POST /api/v1/transcriptions` synchronous multipart upload and transcription
- Actual container inspection for WAV and MP3; filename/content type are not
  trusted
- Configurable upload-size and duration limits
- Faster-Whisper `small` model on CPU with `int8` by default
- Complete text plus timestamped segments and detected language metadata
- Silent-audio, corrupt-media, capacity, and unexpected-error handling
- Structured JSON errors, health endpoint, tests, and Docker configuration

S3, PostgreSQL, SQS, Redis, background jobs, and a frontend are **not
implemented**. [The production design](docs/system-design.md) documents those as
future extensions.

## Requirements

- Python 3.12
- FFmpeg/FFprobe available on `PATH`
- Enough disk for the configured upload limit and enough memory for the Whisper
  model (the first real request downloads and loads it)

## Local setup

```bash
python -m venv .venv
```

Activate the environment, then install and start the service:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

OpenAPI documentation is available at `http://localhost:8000/docs`.

## API usage

```bash
curl -X POST http://localhost:8000/api/v1/transcriptions \
  -F "file=@recording.wav"
```

Example response:

```json
{
  "language": "en",
  "language_probability": 0.98,
  "duration_seconds": 12.4,
  "text": "Example transcription text.",
  "segments": [
    {
      "start_seconds": 0.0,
      "end_seconds": 3.2,
      "text": "Example transcription text."
    }
  ]
}
```

Errors use a stable envelope:

```json
{
  "error": {
    "code": "unsupported_audio_format",
    "message": "Only valid WAV and MP3 audio files are supported."
  }
}
```

`GET /health` is process liveness only; it does not download or load the model.

## Configuration

Copy the safe template for local development:

```bash
cp .env.example .env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
```

The application reads `.env` from its working directory. All settings use the
`AUDIO_` prefix, and process environment variables take precedence over values
from `.env`. The real `.env` file is excluded from Git and Docker build contexts;
only `.env.example` is committed and it must never contain secrets.

| Variable | Default | Purpose |
| --- | ---: | --- |
| `AUDIO_MAX_UPLOAD_BYTES` | `524288000` | Maximum streamed upload size |
| `AUDIO_MAX_DURATION_SECONDS` | `14400` | Maximum inspected duration |
| `AUDIO_UPLOAD_CHUNK_SIZE` | `1048576` | Copy chunk size |
| `AUDIO_TEMP_DIRECTORY` | OS default | Temporary-file directory |
| `AUDIO_FFPROBE_PATH` | `ffprobe` | FFprobe executable |
| `AUDIO_FFPROBE_TIMEOUT_SECONDS` | `30` | Inspection timeout |
| `AUDIO_WHISPER_MODEL` | `small` | Faster-Whisper model |
| `AUDIO_WHISPER_DEVICE` | `cpu` | Inference device |
| `AUDIO_WHISPER_COMPUTE_TYPE` | `int8` | CTranslate2 compute type |
| `AUDIO_WHISPER_DOWNLOAD_ROOT` | unset | Optional model cache directory |
| `AUDIO_WHISPER_BEAM_SIZE` | `5` | Decoder beam size |
| `AUDIO_TRANSCRIPTION_CONCURRENCY` | `1` | Concurrent inference calls/worker |
| `AUDIO_TRANSCRIPTION_ACQUIRE_TIMEOUT_SECONDS` | `1` | Capacity wait before 503 |

## Tests and quality checks

```bash
pytest
ruff check .
ruff format --check .
```

Unit tests mock subprocess and inference boundaries. API tests use the real
FastAPI routing, multipart parsing, temporary storage, exception mapping, and
response validation while replacing FFprobe/model work with fakes.

## Docker

```bash
docker build -t audio-transcription-api .
docker run --rm -p 8000:8000 audio-transcription-api
```

The image installs FFmpeg and runs as a non-root user. It uses one Uvicorn worker
so one model is loaded in that process. Scale containers for additional capacity;
multiple workers each load their own model.

## Architecture and engineering decisions

- The API layer handles HTTP only. `AudioTranscriptionService` coordinates a
  provider-neutral validator and transcription provider.
- `TemporaryUploadStorage` copies in bounded chunks and owns cleanup. Starlette's
  multipart parser spools larger parts to disk before the endpoint runs; the
  service never calls `read()` without a chunk bound.
- FFprobe validates the actual container and audio stream. Supported containers
  are WAV and MP3; codecs valid inside those containers are accepted.
- Faster-Whisper is imported only in its adapter, instantiated lazily, and reused
  once per worker process. A semaphore prevents unbounded inference concurrency.
- The synchronous contract is intentionally small. It bounds memory, disk, file
  size, duration, inspection time, and inference concurrency, but HTTP connection
  time still grows with recording duration.
- Production long-running work should use direct object-store upload and an
  asynchronous job API backed by a queue. See `docs/system-design.md`.

## Limitations

- The first transcription needs network access to download the model unless it
  is already cached or mounted through `AUDIO_WHISPER_DOWNLOAD_ROOT`.
- Results and source audio are not persisted.
- There is no authentication or rate limiting in the assessment baseline.
- A process crash can leave an OS temporary file; periodic temp-directory
  scavenging is a production concern.
- The API returns 503 when per-process inference capacity is not acquired within
  the configured timeout; clients may retry with backoff.

## Assessment video

Add the submitted English walkthrough video URL here before final delivery.
