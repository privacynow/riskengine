# API documentation

OpenAPI is generated from the running FastAPI app:

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

## Authentication

All runtime and admin routes require `Authorization: Bearer <token>`.

Tokens are **not** stored in source code. Configure one of:

- `DECISION_ENGINE_AUTH_TOKENS` — JSON object inline
- `DECISION_ENGINE_AUTH_TOKENS_FILE` — path to JSON file

Generate local demo credentials:

```sh
bash scripts/create_demo_env.sh
```

### Token map shape

```json
{
  "RANDOM_RUNTIME_TOKEN": {
    "tenant_id": "11111111-1111-1111-1111-111111111111",
    "actor_id": "sample-lending-client",
    "roles": ["runtime"]
  },
  "RANDOM_ADMIN_TOKEN": {
    "tenant_id": null,
    "actor_id": "admin-local",
    "roles": ["admin"]
  }
}
```

- **runtime** tokens must include `tenant_id`.
- **admin** tokens may omit `tenant_id` (cross-tenant admin UI access).
- Runtime clients must not supply `tenant_id` / `tenant_name` on `/decisions`, `/checkpoints`, or `/signals`.
- Admin test decisions use `POST /ui/test_decisions` so runtime tokens never reach the browser.

### Admin tenant scoping

Admin list and search endpoints accept optional `tenant_id` to restrict results (used by the admin UI). Examples:

- `GET /ui/checkpoints?tenant_id=<uuid>`
- `GET /ui/search_checkpoints?q=…&tenant_id=<uuid>`
- `GET /ui/signals?tenant_id=<uuid>&checkpoint_id=<uuid>`

Omitting `tenant_id` on admin routes can return rows across tenants; the admin UI always passes `tenant_id` for tenant-bound screens.

### ID validation

Admin path parameters and UUID fields in write models (`tenant_id`, `signals`, `copyFromCheckpointId`, `copyFromSignalId`) must be valid UUIDs. Malformed IDs return **422** before database access.

### Checkpoint create with associations

`POST /ui/checkpoints` accepts optional `signals` (array of signal UUIDs) and `copyFromCheckpointId`. Associations are created in the same transaction as the new checkpoint row.

### DSL preflight

`POST /ui/dsl_preflight` accepts:

- `dsl_expression`
- `signal_names` for new checkpoint drafts
- optional `checkpoint_id` / `checkpointId` for existing checkpoints
- optional `known_names`
- `expression_kind` (`checkpoint` | `signal_expression`)
- optional `binding_mode`

When `checkpoint_id` is supplied, the server checks tenant access and resolves linked signal names from `checkpoint_signals` before strict validation. This is the preferred path for Test Lab and existing checkpoint edits because it avoids client-side races while associations load.

New checkpoint drafts do not have an ID yet, so clients must pass selected signal names explicitly. A checkpoint DSL that references names not present in either `checkpoint_id` links or `signal_names` returns `ok: false` with unknown-identifier errors.

Uses the same policy as runtime evaluation — see [DSL_GUIDE.md](DSL_GUIDE.md).

### Promotion audit

`GET /ui/promotion_audit` (search) and `GET /ui/promotion_audit/{id}` (detail) expose governed version lifecycle events (`action`: `promote`, `deactivate`, `reactivate`).

Lifecycle endpoints (all require `promotionReason`):

- `POST /ui/checkpoints/{id}/make_current` — promote checkpoint version
- `POST /ui/checkpoints/{id}/deactivate` — remove current pointer (runtime 404 by name)
- `POST /ui/checkpoints/{id}/reactivate` — restore current pointer with DSL validation
- `POST /ui/signals/{id}/make_current` — promote signal version
- `POST /ui/signals/{id}/deactivate` — remove current pointer (linked signals skip at runtime)
- `POST /ui/signals/{id}/reactivate` — restore current pointer

Hand-maintained OpenAPI YAML was removed to avoid drift; use `/docs` on a running instance as the source of truth.
