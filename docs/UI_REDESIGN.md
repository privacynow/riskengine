# Admin UI architecture

The admin console is a compiled Vue 3 SPA. FastAPI serves `ui/dist/` at `/admin/`; there is no server-side rendering and no runtime SFC loader.

## Stack

| Layer | Choice |
|-------|--------|
| UI | Vue 3, Composition API, `<script setup lang="ts">` |
| Build | Vite 8, `base: /admin/` |
| State | Pinia stores per domain |
| Routing | Vue Router 4, history mode |
| HTTP | Typed modules under `ui/src/api/` |
| Unit tests | Vitest (`ui/src/tests/unit/`) |
| Browser tests | Playwright (`ui/src/tests/e2e/`) plus `scripts/ui_browser_smoke.mjs` |

Node.js is build-time only. The Python Docker image contains `ui/dist/` and no `node_modules`.

## Directory layout

```text
engine/                   # Python application package
  main.py                 # FastAPI app (uvicorn engine.main:app)
  auth.py, db.py, config.py, models.py, audit.py, cache.py
  routes/                 # runtime + admin routers
  services/               # decision, tenancy, security, …
  demo/                   # /mock/* stubs
ui/
  package.json
  package-lock.json
  vite.config.ts
  playwright.config.ts
  index.html
  public/assets/
  src/
    app/
      main.ts             # entry (referenced from index.html)
      router.ts
      pinia.ts
      config.ts
      routeLoader.ts
      tenantScope.ts
      tenantNav.ts        # routeWithTenant — preserve ?tenant= on navigation
    App.vue
    api/
    stores/
    views/
    components/
      layout/
      primitives/
      workbench/          # PageHeader, WorkbenchLayout, TraceTimeline, …
      domain/             # forms + audit detail panels
    composables/
    styles/
    tests/
      unit/
      e2e/
  dist/                     # gitignored
```

## Navigation and data loading

**Router** owns all screen changes. Paths are deep-linkable (`/admin/signals`, `/admin/checkpoints?tenant=<uuid>`).

**`routeLoader.ts`** maps route names to store actions (`loadAll`, `fetchPage`, `reset`, etc.). It runs:

- In `router.beforeEach` when the session is valid (including after `setActiveTenant()` updates the query).
- After `authStore.submitToken` completes.

**`tenantScope.ts`** exposes `requireTenantId()` and `activeTenantId()`. Tenant-scoped stores refuse to fetch without an active tenant and pass `tenant_id` on every list/search call to `/ui/*`.

## Tenant boundary

| Concern | Implementation |
|---------|----------------|
| URL state | `?tenant=<uuid>` on admin routes |
| Store selection | `tenantStore.activeTenant` synced from URL; cleared when query absent |
| Navigation | `routeWithTenant()` on sidebar and in-app links keeps `?tenant=` |
| API calls | `tenant_id` query param on list/search endpoints |
| Tenant switch | `setActiveTenant()` → `router.replace({ query })` → guard → `loadRouteData(to)` |
| Associations | Loaded on row expand, not on list fetch (avoids N+1) |

Admin list endpoints that accept `tenant_id` include `/ui/checkpoints`, `/ui/search_checkpoints`, `/ui/signals`, and filtered association queries. Runtime `/decisions` still derives tenant from the bearer token only.

## Forms

Domain forms keep an explicit draft object. Parent views bind with `v-model`; submit handlers read the emitted draft. Props are not mutated in place. Outbound bearer tokens are collected in create/edit forms but omitted from API read payloads (`has_bearer_token` on the server).

## SPA static file serving

`engine/main.py` mounts `AdminSPAStaticFiles` at `/admin/`:

- Extensionless paths (e.g. `/admin/checkpoints`) → `index.html` when no static file exists.
- Paths ending in `.js`, `.css`, `.map`, images, fonts, `.json` → `404` if missing (no SPA fallback).

This prevents a missing bundle from returning HTML with a `200` status.

## Build and CI

Local production build:

```bash
cd ui && npm ci && npm run build
```

Docker: `Dockerfile` runs the same in a `node:24-slim` stage and copies `dist/` into the Python image.

CI (`.github/workflows/ci.yml`):

1. `npm ci`, `npm audit --audit-level=high`, `typecheck`, `lint`, `test:unit`, `build`
2. `docker compose up --build`
3. `pytest`, `smoke_test.sh`
4. `scripts/` toolchain `npm ci` + `npm audit` (before UI smoke)
5. `ui_smoke.sh` (browser workflow via `scripts/ui_browser_smoke.mjs`)
6. Playwright e2e under scrubbed env: install Chromium with `env -i PATH HOME` only; run `./node_modules/.bin/playwright test` with `PATH`, `HOME`, `BASE_URL`, and `SMOKE_ADMIN_TOKEN` (read via `scripts/lib/read_env_var.sh` — do not `source .env.local` into npm)

Operator workflows (screens, deep links, acceptance bar): [`UI_WORKFLOWS.md`](UI_WORKFLOWS.md).

## Prior UI

The earlier Vue 2 + `httpVueLoader` shell and the transitional `$root` / mixin layout were removed. Domain logic now lives in Pinia stores and routed views under `ui/src/`.
