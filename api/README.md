# OpenAPI specs

Hand-maintained API descriptions for the decision engine.

| File | Scope |
|------|--------|
| [`decision.yml`](decision.yml) | Public runtime API (`/checkpoints`, `/signals`, `/decisions`) |
| [`admin.yml`](admin.yml) | Admin UI backend (`/ui/*`) |

## Accuracy

These files are **not** auto-generated from FastAPI. Prefer the live app schema at `/docs` when in doubt.

Implemented admin convenience endpoints:

- `GET /ui/all_tenants` — unpaginated tenant list
- `GET /ui/all_checkpoints` — unpaginated checkpoint list (optional `tenant_id`, `active_only`)
- `GET /ui/all_signals` — unpaginated signal list (optional `tenant_id`, `checkpoint_id`, `active_only`)

Search and list endpoints return paginated envelopes: `{ "items", "total", "page", "size" }`. Some older paths in `admin.yml` still describe bare arrays for search responses; treat `/docs` as authoritative until those entries are refreshed.

## TODO

- Align search response schemas in `admin.yml` with paginated responses
- Consider generating OpenAPI from FastAPI in CI
