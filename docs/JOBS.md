# Durable analysis jobs

Starting analysis commits the run and its outbox event together. The API returns `202`; it does not execute analysis inside an HTTP background task. Run status is authoritative in the database. A broker message contains only a run ID.

## Supported execution modes

- **Native local development:** SQLite plus `python -m app.jobs.worker` from `backend`. `run_backend.ps1` starts and stops this hidden worker with the API. A manual Uvicorn launch requires a separate worker terminal. The local worker polls the durable database and uses the same leases/checkpoints as Celery.
- **Shared/container development:** `docker compose up --build` starts PostgreSQL 16, Redis, one-shot migrations, API, Celery worker, dispatcher, and frontend. Celery runs in Linux containers, including on Windows hosts.

The Compose stack now uses a separate PostgreSQL volume. It does not import or remove an existing local SQLite database. Continue native SQLite mode to work with existing local data. A transfer to PostgreSQL needs a separately rehearsed data migration; changing a connection string is not a transfer. Compose credentials are local-development defaults and the stack is not a production deployment template. Production hardening remains M8.

## Ownership and recovery

Workers claim queued runs atomically with a unique attempt ID. A heartbeat renews the lease. Each checkpoint and final publication checks that the attempt still owns an unexpired lease. Publication locks the project and checks the run again, so an older worker cannot overwrite a recovered attempt's report.

Extraction checkpoints include their output hash and are unique per run/stage. A recovered attempt reuses valid extracted input, while validating the source file against the sealed manifest again. Findings and the score publish in one transaction. Duplicate delivery after a terminal state is a no-op.

The dispatcher reconciles expired leases and republishes undelivered or still-queued work. A broker outage leaves the outbox intact, with bounded delivery backoff. Worker execution is limited to three attempts by default. Repeated worker loss reaches `failed` with `worker_attempts_exhausted`; it never silently loops forever. Input/parser failures fail the attempt rather than repeatedly retrying corrupt data. Requested AI failures preserve deterministic results as a partial report.

Celery uses late acknowledgements, worker-loss redelivery, prefetch one, JSON-only task messages, no result backend, and a hard task time limit. Redis visibility timeout exceeds the job limit. Recovery does not depend solely on broker visibility: the database reconciler handles expired ownership. [Celery Redis delivery documentation](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html).

| Setting | Default | Purpose |
|---|---|---|
| `JOB_LEASE_SECONDS` | 90 | Ownership lease, renewed approximately every third of this interval |
| `JOB_MAX_ATTEMPTS` | 3 | Limit on claims after worker loss |
| `JOB_TIMEOUT_SECONDS` | 900 | Worker job time budget |
| `JOB_REDISPATCH_SECONDS` | 30 | Retry interval for queued work whose broker delivery did not lead to a claim |
| `JOB_POLL_SECONDS` | 1 | Local worker polling interval |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery transport |

Keep leases longer than ordinary database delays. Never run two independently configured deployments against the same job tables with conflicting time budgets. Stop old workers and API writes before applying the jobs migration. It imports unfinished old runs into the durable queue; this is a one-time cutover, not blanket invalidation at application startup.

## Cancellation and diagnosis

`POST /v1/runs/{id}/cancel` is owner-checked and idempotent. Queued work cancels immediately. Running work checks cancellation between stages and before provider calls/retries; it does not promise to undo an already-sent provider request. Cancelled or failed attempts cannot replace the last complete report. The report UI exposes stage, attempt count, and cancellation state without inventing progress percentages.

If a run remains queued, check worker and dispatcher processes, database connectivity and Redis. If it remains running after worker loss, allow its lease to expire and ensure a reconciler is running. Native mode reconciles before polling; container mode uses the dispatcher. Readiness checks database/schema availability, not worker throughput. `/v1/runs/{id}` reports heartbeat time and safe error codes; provider credentials are not stored in queue errors.

```sh
docker compose logs worker dispatcher backend
docker compose restart worker dispatcher
```

Restarting workers can cause redelivery; the lease/fencing protocol makes that safe. Do not manually clear run status or delete output rows to retry a job. Start a new run through the API after a terminal failure.

## Verification

- Unit tests cover atomic enqueue, duplicate claim, checkpoint identity, broker retry, bounded recovery, live-lease preservation, and cancellation.
- A real-process test kills a worker during parsing, restarts the API, then starts a replacement worker. The original run completes on attempt two with one score and one set of findings; API reads remain responsive.
- The Chromium workflow runs against the separate local worker.
- CI Compose testing stops the worker, creates queued work, restarts API/Redis/dispatcher, resumes the worker, and verifies the same run completes. An additional duplicate Celery delivery must leave its report unchanged.

AI output contracts, per-call usage budgets, scoped caches, privacy validation, and provider retry classification remain M5. This phase does not claim those checks are complete.
