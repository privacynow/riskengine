# Admin UI (Vue 3 + Vite)

The Decision Engine admin console is a **Vue 3 + Vite** single-page app, compiled to static assets and served by FastAPI at `/admin/`.

## Why compiled frontend

- No runtime SFC loading or browser HTML parsing bugs
- Standard Vue 3 SFC compilation and tooling
- Plain static JS/CSS/HTML at runtime — easy to cache and serve
- Browser smoke tests verify rendered workflows

## Layout

```text
ui/
  package.json
  package-lock.json
  vite.config.js
  index.html              # Vite entry (dev)
  public/assets/          # static files copied to dist (favicon)
  src/
    main.js
    App.vue
    api/                  # fetch client, auth, formatters
    stores/               # notices (transitional)
    mixins/               # domain logic on App.vue root ($root in views)
    components/           # layout, common, feature views
    styles/
  dist/                   # Vite build output (gitignored; built in Docker/CI)
```

## Build toolchain

Node is used **only at build time**, not in the Python runtime container:

- **Docker:** multi-stage `Dockerfile` runs `npm ci` + `npm run build` in `node:24-slim`, copies `ui/dist/` into the Python image
- **Local:** `cd ui && npm ci && npm run build` before `uvicorn` if not using Docker

Lockfiles (`ui/package-lock.json`, `scripts/package-lock.json`) are committed for reproducible installs.

## Development

```bash
cd ui
npm ci
npm run dev          # Vite dev server (proxy API separately or use full stack)
npm run build        # outputs ui/dist/
```

Full stack locally:

```bash
cd ui && npm ci && npm run build
cd .. && uvicorn main:app --reload
```

Open http://localhost:8000/admin/

## Transitional implementation notes

Domain state and methods live in `src/mixins/` mounted on the root `App.vue` instance. Child views use `$root` for shared state. A follow-up can migrate to Pinia stores and Composition API per domain without changing the backend.

## Verification

```bash
cd ui && npm ci && npm run build
docker compose build risk-engine && docker compose up -d
bash scripts/ui_smoke.sh      # static + Playwright DOM/workflow checks
bash scripts/smoke_test.sh
docker compose exec -T -e RUN_INTEGRATION_TESTS=1 risk-engine pytest -q
```

`ui_smoke.sh` requires Node.js, `SMOKE_ADMIN_TOKEN`, and Playwright Chromium (installed via `scripts/package-lock.json`).

## Migration history

The prior Vue 2 + `httpVueLoader` runtime UI was removed. Component structure and CSS were reused under `ui/src/`.
