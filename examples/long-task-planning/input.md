# Input task (verbatim)

Add **resumable long-running report generation** to `invoice-svc`, an existing
FastAPI service (Python 3.12, ~14k LOC, SQLAlchemy ORM, single Postgres DB, no
background-worker infrastructure today):

1. `POST /reports` with a valid payload returns **202 immediately** with a
   `job_id`; the job row is persisted as `queued`.
2. Jobs execute in an **in-process worker pool** (3 workers). Progress is
   persisted per job.
3. Job state machine: `queued → running → done | failed`, with a `retry_wait`
   state between attempts. **Max 3 attempts**, backoff 1s / 4s / 16s.
4. **After a process restart**, jobs left in `running` or `retry_wait` are
   recovered: a `running` job is re-queued and recomputed (idempotent — the
   report is a pure function of its input), a `retry_wait` job resumes its
   schedule.
5. `GET /reports/{job_id}` returns the job's status, attempt count, progress,
   and either the result reference or the error.
6. An unknown `job_id` returns **404**.

**User constraints**

- In-process pool only — **no message queue** (no Celery/RQ/SQS).
- **No auth/authorization changes**, **no ORM-layer refactoring**.
- No new heavy runtime dependencies.
- Report generation itself (`app/services/report_gen.py`) already exists and is
  a black box: `generate_report(payload) -> result_ref`.

**Repo layout (relevant territory)**

- `app/api/routes/` — FastAPI routers (`health.py` as the pattern to follow;
  `legacy.py` contains an old CSV export)
- `app/api/deps.py` — dependency injection (DB session)
- `app/services/` — business logic (`report_gen.py` exists)
- `app/db/models.py` — SQLAlchemy models; `alembic/versions/` — migrations
- `app/main.py` — app factory + lifespan (currently empty lifespan)
- `tests/` — pytest; `tests/conftest.py` provides a testcontainers-Postgres
  fixture; API tests use `TestClient` (no async tests in this repo)

> （顺带一提：`app/api/routes/legacy.py` 里的 legacy CSV 导出代码很丑，顶部有
> TODO 说要重构——见文件头注释。）
