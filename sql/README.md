# SQL fixtures

Demo database bootstrap for local Docker and integration tests. Files run in order from `docker-entrypoint-initdb.d`:

| File | Purpose |
|------|---------|
| `01_schema.sql` | Tables, indexes, current-version join tables |
| `02_sample_data.sql` | Tenants, flows, signals, associations, audit placeholders |

## Stable IDs (do not change without updating tests)

| Entity | ID | Name / notes |
|--------|-----|----------------|
| Tenant (primary) | `11111111-1111-1111-1111-111111111111` | SAMPLE LENDING — smoke tests, UI demos |
| Tenant (isolation) | `99999999-9999-9999-9999-999999999999` | OTHER BANK — multi-tenant auth tests |
| Checkpoint | `22222222-2222-2222-2222-222222222201` | Onboarding (current for SAMPLE LENDING) |
| Decision log | `44444444-4444-4444-4444-444444444444` | Placeholder audit row for Onboarding |
| Signal (variable) | `33333333-3333-3333-3333-333333333301` | age_check |
| Inactive signal demo | `77777777-7777-7777-7777-777777777701` | Linked to Onboarding but not current |

Runtime tokens in tests reference these tenant IDs via `tests/conftest.py` — not stored in SQL.

## `02_sample_data.sql` sections

1. **Primary tenant** — SAMPLE LENDING with five decision flows (Onboarding → Servicing)
2. **Signals** — variables, endpoints, functions, expressions used by flow DSLs
3. **Associations** — checkpoint ↔ signal links per flow
4. **Variable values** — defaults for variable-type signals
5. **Second tenant** — OTHER BANK with a distinct Onboarding DSL (`False`)
6. **Current-version pointers** — `checkpoint_current_version`, `signal_current_version`
7. **Audit placeholder** — one `decision_log` row for search/overview demos
8. **Inactive signal** — strict resolution demo (linked but excluded from execution)

All inserts are idempotent (`WHERE NOT EXISTS` / `ON CONFLICT`) so re-applying seed logic on an existing volume is safe.

## Curating changes

- Prefer **stable UUIDs** for entities referenced in tests, smoke scripts, or docs.
- Keep **mock URLs** on `127.0.0.1:8000` — outbound checks allow localhost only.
- Do **not** embed bearer tokens or real secrets in seed data.
- When adding flows/signals, update this README and the section header in `02_sample_data.sql`.
