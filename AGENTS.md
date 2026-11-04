# Volga Partners – Principal Software & AI Engineer Assessment

## Project Status

The complete assessment requirements, architecture, and API contracts have been
reviewed and approved. Application implementation is authorized.

Documentation changes made during architecture review are allowed. Do not claim
that a feature is implemented unless working code and tests exist for it.

## Objective

Build a minimal, reliable audio-transcription API that accepts WAV and MP3 files
and returns timestamped text segments. The working baseline must remain small and
fully functional while clearly documenting how it could evolve into a scalable,
asynchronous production system.

## Confirmed Technology Decisions

- Language: Python.
- API framework: FastAPI.
- Request and response validation: Pydantic.
- Transcription engine: Faster-Whisper.
- Media inspection and validation: FFmpeg/FFprobe.
- Baseline storage: local temporary files only.
- Baseline execution model: synchronous request/response transcription.
- Frontend: not required.
- Production-scale components are system-design proposals only.
- Do not implement S3, PostgreSQL, SQS, background workers, or a dead-letter
  queue for the working baseline.

## Part 1 – Working Implementation Requirements

1. Accept WAV and MP3 file uploads through FastAPI.
2. Validate the audio container/codec, configured maximum size, and configured
   maximum duration. Do not trust only the filename or client content type.
3. Use Faster-Whisper for speech-to-text.
4. Return ordered transcription segments with start and end timestamps and text.
5. Handle long recordings with bounded resources:
   - stream uploads to a temporary file in chunks;
   - reject an upload as soon as the byte limit is exceeded;
   - pass file paths, not in-memory audio blobs, to validation/transcription;
   - consume Faster-Whisper segment output incrementally; and
   - limit concurrent transcription work within a process.
6. Return consistent API errors and clean up temporary files on every success and
   failure path.
7. Include automated unit and integration tests. Tests must not require a real
   model download; Faster-Whisper and external processes should be replaceable or
   mockable at boundaries.
8. Provide a Dockerfile and local/Docker setup instructions.

## Part 2 – System Design Documentation Requirements

Document, but do not implement for the baseline, a production architecture that
supports:

1. Concurrent and resumable/controlled uploads.
2. S3 storage for audio and PostgreSQL persistence for jobs and transcripts.
3. SQS-backed background transcription workers.
4. Bounded retries, idempotency, visibility timeouts, dead-letter queues, and
   recovery/re-drive procedures.
5. Horizontally scalable, stateless REST API instances.
6. Capacity controls, observability, security, lifecycle/retention policies, and
   failure handling across the proposed components.

The system-design document must label all of these as proposed production
architecture rather than implemented functionality.

## Assessment Deliverables

- A working Git repository with focused, understandable commits.
- A README containing setup, usage, testing, Docker instructions, limitations,
  and architectural decisions.
- A system-design document for Part 2.
- Automated unit and integration tests.
- Docker configuration.
- A short English-language video explaining the implementation and design.
  The repository should include a link or submission note, not the video binary,
  unless the assessment submission process explicitly requires otherwise.

## Architectural Boundaries

- The API layer owns HTTP parsing, status codes, and response serialization.
- The upload/validation layer streams the file and uses FFprobe to establish its
  actual media properties.
- The application service coordinates validation and transcription without
  depending on FastAPI request objects.
- A transcription protocol/interface defines provider-neutral input and output.
- The Faster-Whisper adapter is the only layer that imports provider-specific
  types.
- Configuration is provided through environment-backed settings.
- Temporary-file creation and cleanup have an explicit lifecycle owned by the
  request/application-service boundary.
- Keep modules independently testable and avoid abstractions without a current
  testing or separation-of-concerns benefit.

## Proposed Folder Structure

```text
.
|-- app/
|   |-- __init__.py
|   |-- main.py
|   |-- api/
|   |   |-- __init__.py
|   |   |-- errors.py
|   |   `-- routes/
|   |       |-- __init__.py
|   |       `-- transcriptions.py
|   |-- core/
|   |   |-- __init__.py
|   |   `-- config.py
|   |-- domain/
|   |   |-- __init__.py
|   |   |-- errors.py
|   |   `-- models.py
|   |-- schemas/
|   |   |-- __init__.py
|   |   |-- errors.py
|   |   `-- transcriptions.py
|   |-- services/
|   |   |-- __init__.py
|   |   |-- audio_validation.py
|   |   |-- transcription.py
|   |   `-- uploads.py
|   `-- providers/
|       |-- __init__.py
|       |-- base.py
|       `-- faster_whisper.py
|-- tests/
|   |-- unit/
|   |-- integration/
|   `-- fixtures/
|-- docs/
|   `-- system-design.md
|-- .dockerignore
|-- .env.example
|-- .gitignore
|-- Dockerfile
|-- pyproject.toml
|-- README.md
`-- AGENTS.md
```

## Proposed Baseline API Contract

### `POST /api/v1/transcriptions`

Request:

- Content type: `multipart/form-data`.
- Required field: `file` containing one WAV or MP3 audio file.
- No URL-based ingestion or multi-file upload in the baseline.
- Language selection and other model-tuning options are omitted from the initial
  public contract; Faster-Whisper performs language detection.

Successful response: `200 OK`, `application/json`.

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

Contract rules:

- Times are finite, non-negative seconds represented as JSON numbers.
- Segments are ordered by `start_seconds` and `end_seconds` is not earlier than
  `start_seconds`.
- `language` and `language_probability` may be `null` if the provider cannot
  determine them reliably.
- `segments` may be empty for valid audio containing no detectable speech.
- `duration_seconds` is derived from media inspection, not client input.

Error response:

```json
{
  "error": {
    "code": "unsupported_audio_format",
    "message": "Only valid WAV and MP3 audio files are supported."
  }
}
```

Error status mapping:

- `400 Bad Request`: missing/empty upload or malformed multipart request.
- `413 Payload Too Large`: configured upload-size limit exceeded.
- `415 Unsupported Media Type`: content is not a supported WAV/MP3 media format.
- `422 Unprocessable Content`: supported media is corrupt, unreadable, or exceeds
  the configured duration limit.
- `503 Service Unavailable`: transcription capacity is temporarily unavailable
  or the transcription provider cannot complete the request.
- `500 Internal Server Error`: unexpected failure, with no internal details or
  filesystem paths exposed to the client.

### `GET /health`

Returns `200 OK` with `{"status": "ok"}` when the API process is running. This
is a liveness endpoint and does not promise that a model has been downloaded or
loaded. A production readiness endpoint is outside the baseline.

## Minimal Working Implementation

The baseline is one FastAPI service with one synchronous transcription endpoint.
It streams a single upload to a uniquely named temporary file, enforces a
configurable byte limit, validates actual media metadata with FFprobe, enforces a
configurable duration limit, and invokes a process-wide Faster-Whisper adapter.
The model is loaded lazily and reused. A bounded concurrency guard prevents one
process from starting unlimited CPU/GPU-heavy transcriptions. Cleanup executes in
a `finally` path.

The baseline does not persist uploads or transcripts, expose job resources, run
background workers, or depend on cloud services or a database.

## Configuration Defaults

The environment-backed defaults are a 500 MiB upload limit, four-hour duration
limit, `small` model, `cpu` device, `int8` compute type, 1 MiB upload chunks, and
one concurrent transcription per worker process.

## Implementation Plan (After Approval)

1. Initialize the Git repository and add repository hygiene/configuration files.
2. Create the package skeleton, settings, domain models, and error taxonomy.
3. Implement chunked temporary-file upload handling with byte limits and cleanup.
4. Implement FFprobe-based media inspection and validation.
5. Define the transcription interface and implement the Faster-Whisper adapter
   with lazy model reuse and bounded concurrency.
6. Add the application orchestration service and FastAPI routes/error handlers.
7. Add unit tests for limits, validation, mapping, cleanup, and orchestration.
8. Add integration tests for the HTTP contract using fakes at heavy/external
   boundaries.
9. Add Docker configuration and verify local and container workflows.
10. Write the README and Part 2 system-design document, explicitly separating
    implemented behavior from proposed production architecture.
11. Run formatting, static checks, tests, and a manual end-to-end smoke test.
12. Prepare the short English walkthrough video and add its submission link/note.

## Implementation Status

Implementation is authorized. Keep this document accurate as the baseline is
built, and continue to distinguish implemented behavior from proposed production
architecture.
