## System Overview

The Risk Decision Engine is a multi-tenant system that allows users (e.g., underwriters, compliance officers, or developers) to define checkpoints—decision points that incorporate signals (data checks, calls to internal or external services, local functions, or variable lookups). The system:

1. Receives requests to evaluate a checkpoint (e.g., “Onboarding,” “Underwriting”).
2. Loads configuration (e.g., a DSL expression, signals).
3. Invokes each signal in **evaluation order** (`order_of_evaluation`). Signals that share an order run concurrently today; the `can_run_in_parallel` flag is stored but not yet enforced (see [ROADMAP.md](ROADMAP.md)).
4. Evaluates a final DSL expression referencing the signals.
5. Logs everything for auditing.
6. Caches signals (in-memory and DB) when `allow_caching` is enabled.

**Cost limits:** The engine skips signals when cumulative cost would exceed `max_cost` (unless `override_cost_flag` is set).

**Not yet implemented:** Per-signal/checkpoint HTTP timeouts (external calls use a fixed 5s client timeout today) and selective parallelism based on `can_run_in_parallel`.

It also includes a UI (a single-page application) and a UI Backend for admin/maintenance tasks like creating new tenants, checkpoints, signals, and variables.

> **Status:** Working prototype / architectural spike. See [ROADMAP.md](ROADMAP.md) for known limitations and planned milestones.

---

## Risk Engine

### Architecture

The Risk Engine is a FastAPI application exposing these endpoints:

- `GET /checkpoints/{checkpoint_name}`: Returns checkpoint details (including associated signals).
- `GET /signals/{signal_name}`: Returns signal details.
- `POST /decisions`: Invokes a decision for a given `checkpoint_name`, plus an optional `applicant_id` and `correlation_id`.
- `GET /decisions/{decision_id}`: Retrieves an audit record of a past decision (with signals invoked).
- `GET /mock/{name}`: Demo stub endpoints used by sample internal/external signals.

Internally, it is composed of:

- **Routing + Controllers**: The FastAPI paths for the endpoints.
- **Logic Layer**: The decision orchestration (`make_decision(...)`), caching checks, DSL evaluation, cost tracking, and concurrency.
- **Audit Logging**: An asynchronous queue that writes to `decision_log` and `signal_log` in the database.

The system is designed so that configuration (signals, checkpoints) is stored in the DB, not in code. Therefore, new signals can be added or modified without redeploying the service.

---

### Execution Flow (Decision)

When the user (or an external system) calls `POST /decisions` with `checkpoint_name` (and optionally `applicant_id`, `correlation_id`), the following occurs:

1. **Lookup Checkpoint**: Queries checkpoints for a row matching the name.
2. **Find Signals**: Joins with `checkpoint_signals → signals`.
3. **Ordered execution:** Signals are grouped by `order_of_evaluation`. All signals in the same order group run concurrently; cost limits may skip expensive signals. Optional DB/in-memory caching applies when configured.
4. **Evaluate DSL:** `simpleeval` evaluates the checkpoint expression using `{ signal_name: signal_value }`.
5. **Asynchronous logging:** Final decision and per-signal invocations are logged.
6. **Response:** Returns `decision_id`, `final_decision_value`, `cost_incurred`, and `signal_results`.

See [ROADMAP.md](ROADMAP.md) for planned runtime improvements (tenant/current-version resolution, configurable timeouts, parallelism flags).

---

## UI and UI Backend

The UI is a Vue 2 single-page app served at **`/admin/`** (static files under `ui/`). JavaScript dependencies are **vendored locally** under `ui/vendor/` (no CDN required). JSON admin APIs live under **`/ui/...`**.

Primary admin capabilities:

- Tenants, checkpoints, signals, variable values, checkpoint-signal associations
- Search endpoints for tenants, checkpoints, signals, decisions, and signal logs
- Test Decision flow in the admin UI

---

## Database

PostgreSQL stores tenants, checkpoints, signals, associations, audit logs, `signal_variable_values`, `signal_cached_values`, and current-version pointer tables (`checkpoint_current_version`, `signal_current_version`).

Schema: [`sql/01_schema.sql`](sql/01_schema.sql)  
Sample data: [`sql/02_sample_data.sql`](sql/02_sample_data.sql) (includes demo tenant **SAMPLE LENDING** and mock-friendly signal URLs)

Sample bearer-token fields use clearly fake values such as `EXAMPLE-KYC-TOKEN-NOT-REAL`.

---

## Quick Start (Docker)

Prerequisites: Docker and Docker Compose.

```sh
git clone <your-repo-url>
cd decision-engine
docker compose up -d --build
```

On first start, Postgres runs `sql/01_schema.sql` then `sql/02_sample_data.sql` from `docker-entrypoint-initdb.d`.

Open the admin UI:

```sh
open http://localhost:8000/admin/
```

Run the smoke test (assumes stack is already up):

```sh
bash scripts/smoke_test.sh
```

For a clean-room verification (destroys the local DB volume first):

```sh
bash scripts/bootstrap_smoke.sh
```

Helper scripts (all use `docker compose`):

| Script | Purpose |
|--------|---------|
| `scripts/run.sh` | Start stack and apply SQL to an existing volume |
| `scripts/destroy.sh` | Stop stack and remove the Postgres volume |
| `scripts/redeploy_engine.sh` | Rebuild/recreate the app container |
| `scripts/redeploy_db.sh` | Reset Postgres volume and re-seed sample data |
| `scripts/redeploy_all.sh` | Destroy, run, and smoke test |

Example decision request:

```sh
curl -s -X POST http://localhost:8000/decisions \
  -H "Content-Type: application/json" \
  -d '{"checkpoint_name":"Onboarding","applicant_id":"demo-1","correlation_id":"demo"}'
```

---

## Local Development (without Docker)

1. Start PostgreSQL and create database `risk_engine_db`.
2. Apply `sql/01_schema.sql`, then `sql/02_sample_data.sql`.
3. `python3 -m venv .venv && source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. Export DB env vars if needed (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, ...).
6. `uvicorn main:app --host 0.0.0.0 --port 8000`
7. Open `http://localhost:8000/admin/`

---

## Security (demo limitations)

- No authentication on `/ui/*` or decision APIs.
- Docker Compose uses default Postgres credentials for local demo only.
- Do not expose an unsecured instance to the public internet.

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for milestone plan and known gaps (tenant-aware runtime, immutable versioning, CI, auth, etc.).

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Docker Compose deployment and optional remote-host sync patterns.

---

## License

MIT — see [LICENSE](LICENSE).
