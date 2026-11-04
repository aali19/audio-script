# Proposed Production System Design

This document describes a production extension. None of the AWS or database
components below are part of the implemented synchronous baseline.

## Request and processing flow

1. A stateless API authenticates the caller, creates an idempotent transcription
   job in PostgreSQL, and issues a short-lived S3 multipart-upload URL.
2. The client uploads directly to S3, avoiding API memory, disk, and bandwidth
   bottlenecks. The API verifies completion and publishes the job identifier to
   SQS.
3. Autoscaled workers claim messages, atomically move jobs from `queued` to
   `processing`, download or stream the object to bounded local scratch space,
   validate it, and run Faster-Whisper.
4. Workers persist ordered transcript segments and job status in PostgreSQL.
   Clients poll `GET /api/v1/transcriptions/{job_id}` or receive an optional
   webhook/event notification.

## Concurrency and scaling

- API instances remain stateless behind a load balancer and use database-backed
  idempotency keys for safe request retries.
- Direct multipart S3 uploads are size-limited by policy. Per-tenant quotas and
  rate limits protect API and worker capacity.
- Worker groups scale from SQS queue depth and oldest-message age. Each worker
  has a small concurrency limit chosen for its CPU/GPU and model footprint.
- PostgreSQL connections use a bounded pool; transcripts use normalized job and
  segment tables with pagination for large results.

## Retries, DLQ, and recovery

- SQS visibility timeout exceeds the expected processing interval and is renewed
  while a worker remains healthy.
- Jobs and object keys are immutable; worker writes are idempotent and guarded by
  job version/state so redelivery cannot duplicate transcript segments.
- Transient failures use exponential backoff with jitter and a bounded receive
  count. Invalid media is a terminal failure and is not retried.
- Exhausted messages move to a DLQ. Alarms cover DLQ depth and message age.
  Operators inspect the recorded error, correct systemic issues, and re-drive
  only retryable jobs.
- A reconciliation task finds stuck `processing` jobs whose leases expired and
  safely requeues them. S3 lifecycle rules remove abandoned uploads and expired
  source audio according to retention policy.

## REST resources

- `POST /api/v1/transcriptions` creates a job or begins an upload workflow.
- `GET /api/v1/transcriptions/{job_id}` returns status and result metadata.
- `GET /api/v1/transcriptions/{job_id}/segments` pages large transcripts.
- `DELETE /api/v1/transcriptions/{job_id}` requests cancellation and retention
  cleanup where policy permits.

Job states are explicit: `awaiting_upload`, `queued`, `processing`, `completed`,
`failed`, and `cancelled`. Public errors remain stable while internal diagnostic
details live in restricted logs and job-attempt records.

## Operations and security

- Encrypt S3, SQS, and PostgreSQL in transit and at rest; use narrow IAM roles,
  private networking, secret rotation, malware/content controls, and audit logs.
- Never log audio or transcript text by default. Apply tenant authorization to
  every job and object operation and document deletion/retention guarantees.
- Track request latency, upload failures, queue age, transcription duration,
  real-time factor, worker saturation, retries, terminal failures, and DLQ depth.
- Trace a correlation/job ID across API, SQS, worker, storage, and database.
- Deploy backward-compatible schema/API changes and drain workers gracefully.
