# SQL fixtures

Demo database bootstrap for local Docker and integration tests. Files run in order from `docker-entrypoint-initdb.d`:

| File | Purpose |
|------|---------|
| `01_schema.sql` | Tables, indexes, current-version join tables |
| `02_sample_data.sql` | Curated product demo tenants, checkpoints, signals, associations |

Visual regression data is **not** in this folder — see `tests/fixtures/visual_fixture.sql`, `tests/fixtures/lifecycle_e2e_fixture.sql`, and `scripts/seed_visual_fixture.sh`.

## Stable IDs (do not change without updating tests)

| Entity | ID | Name / notes |
|--------|-----|----------------|
| Tenant (primary) | `11111111-1111-1111-1111-111111111111` | SAMPLE LENDING — smoke tests, UI demos |
| Tenant (isolation) | `99999999-9999-9999-9999-999999999999` | OTHER BANK — multi-tenant auth tests |
| Tenant (visual e2e) | `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` | VISUAL FIXTURE BANK — stable Playwright screenshots |
| Checkpoint | `22222222-2222-2222-2222-222222222201` | Onboarding (current for SAMPLE LENDING) |
| OTHER BANK checkpoint | `88888888-8888-8888-8888-888888888801` | Onboarding (stricter policy, declines in smoke) |
| Decision log | `44444444-4444-4444-4444-444444444444` | Sample approved Onboarding row for audit/overview demos |
| Signal (variable) | `33333333-3333-3333-3333-333333333301` | age_check |
| Signal (expression) | `33333333-3333-3333-3333-333333333315` | kyc_pass — compositional KYC gate |
| Signal (expression) | `33333333-3333-3333-3333-333333333316` | credit_pass — compositional bureau gate |
| Signal (variable) | `33333333-3333-3333-3333-333333333314` | requested_loan_amount |
| OTHER BANK expression | `88888888-8888-8888-8888-888888888806` | affordability_pass |
| Inactive signal demo | `77777777-7777-7777-7777-777777777701` | Linked to Onboarding but not current |

Runtime tokens in tests reference these tenant IDs via `tests/conftest.py` — not stored in SQL.

## `02_sample_data.sql` sections

1. **SAMPLE LENDING tenant**
2. **Checkpoints** — Onboarding through Servicing (stable names + DSLs for tests)
3. **Signals** — variables, endpoints, functions, expressions
4. **Associations** — checkpoint ↔ signal links
5. **Variable defaults** — realistic demo values for variable signals
6. **OTHER BANK** — stricter onboarding policy with variable signals (smoke expects decline)
7. **Current-version pointers** — `checkpoint_current_version`, `signal_current_version`
8. **Sample decision_log row** — overview/search demo data
9. **Inactive signal** — strict resolution demo (linked but excluded from execution)
10. **Policy refresh** — `UPDATE` statements for checkpoint DSL, signal expressions, descriptions, and demo values on existing volumes (re-run section 10 without `docker down -v` to upgrade policy)

All inserts are idempotent (`WHERE NOT EXISTS` / `ON CONFLICT`) so re-applying seed logic on an existing volume is safe.

## API-only cleanup vs full reset

`scripts/cleanup_demo_config_via_api.py` removes scratch/demo config via admin APIs. When the server has `DECISION_ENGINE_DEV_PURGE=1`, it first calls `POST /ui/dev/purge/tenant` to delete audit/log/cache rows for a tenant (requires admin auth, `X-Dev-Purge-Confirm`, and an exact body acknowledgement phrase).

Dev purge guardrails (all required):

| Gate | Purpose |
|------|---------|
| `DECISION_ENGINE_DEV_PURGE=1` | Routes are not registered when unset (**404** for all callers, including unauthenticated) |
| `DECISION_ENGINE_DEV_PURGE_CONFIRM` | **Required** when purge is enabled; must match `X-Dev-Purge-Confirm` (server returns **500** if missing) |
| Body `confirmPhrase` | Exact phrase acknowledging permanent tenant audit deletion |
| Admin bearer token | Same as other `/ui/*` mutations |

`scripts/create_demo_env.sh` enables dev purge locally and prints the confirm token.

List variable values for cleanup: `GET /ui/signals/{signal_id}/variable_values`.

For a true fresh bootstrap, reset the Postgres volume. This recreates the schema and reruns `02_sample_data.sql`; applying the cleanup script alone does not re-seed deleted demo tenants.

```bash
bash scripts/create_demo_env.sh
docker compose down -v
docker compose up -d --build
bash scripts/smoke_test.sh
```

The curated seed should produce:

- `SAMPLE LENDING` with lifecycle checkpoints from `Onboarding` through `Servicing`.
- Reusable signal types: variables, internal endpoints, external endpoints, local functions, and expression signals.
- `OTHER BANK` with the same `Onboarding` checkpoint name and a stricter tenant-specific policy that declines in smoke tests.
- One completed decision row for overview/audit screens.
- `inactive_demo`, linked but not current, to prove inactive signals do not execute.

Visual regression data is intentionally separate from product demo seed data:

```bash
bash scripts/seed_visual_fixture.sh
```

Optionally remove scratch tenants from a running dev DB:

```bash
python3 scripts/cleanup_demo_config_via_api.py --dry-run
python3 scripts/cleanup_demo_config_via_api.py --yes
```

Use `--include-seed-tenants --yes` only when you intend to wipe seeded demo tenants and re-apply SQL (or recreate the volume).

## Curating changes

- Prefer **stable UUIDs** for entities referenced in tests, smoke scripts, or docs.
- Keep **mock URLs** on `127.0.0.1:8000` — outbound checks allow localhost only.
- Do **not** embed bearer tokens or real secrets in seed data.
- When changing demo policy, update section 10 refresh `UPDATE`s and this README.
