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
- Runtime clients must not supply `tenant_id` / `tenant_name` on public APIs.
- Admin test decisions use `POST /ui/test_decisions` so runtime tokens never reach the browser.

Hand-maintained YAML under this directory was removed to avoid drift; use `/docs` as the source of truth.
