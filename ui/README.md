# Decision Engine Admin UI

Vue 3 + TypeScript + Vite + Pinia + Vue Router. Built to `dist/` and served by FastAPI at `/admin/`.

Repo-level overview: [../README.md](../README.md). Architecture: [../docs/UI_REDESIGN.md](../docs/UI_REDESIGN.md). Operator workflows: [../docs/UI_WORKFLOWS.md](../docs/UI_WORKFLOWS.md).

## Commands

```bash
npm ci
npm run dev          # Vite dev server on :5173; proxies /ui and /decisions to :8000
npm run typecheck    # vue-tsc
npm run lint         # eslint src
npm run test:unit    # vitest (src/tests/unit/)
npm run build        # vue-tsc + vite build → dist/
npm run test:e2e     # playwright (src/tests/e2e/); stack + SMOKE_ADMIN_TOKEN required
```

Docker builds the UI in the repo `Dockerfile` (`node:24-slim` stage → copies `ui/dist/` into the Python image). The runtime container has no Node.js.

### E2e prerequisites

Stack must be up (`docker compose up -d --build`). Read the admin token without exporting the whole env file:

```bash
# from repo root
source scripts/lib/read_env_var.sh
ADMIN_TOKEN="$(read_env_var SMOKE_ADMIN_TOKEN .env.local)"

cd ui
env -i PATH="${PATH}" HOME="${HOME:-}" npx playwright install chromium
env -i PATH="${PATH}" HOME="${HOME:-}" \
  BASE_URL="http://127.0.0.1:8000" \
  SMOKE_ADMIN_TOKEN="${ADMIN_TOKEN}" \
  ./node_modules/.bin/playwright test
```

For local iteration you may use `npm run test:e2e` after exporting only `SMOKE_ADMIN_TOKEN`. Do not `source .env.local` before `npm ci` or `playwright install` — install tooling should not inherit app secrets. `scripts/ui_smoke.sh` uses the same scrubbed-env pattern for its Playwright step.

### Dependency audit

```bash
npm --prefix ui run audit:high
npm --prefix scripts audit --audit-level=high --omit=optional
```

CI runs both gates. Dev toolchain was upgraded (Vite 8, Vitest 4, Playwright 1.61+) to clear high-severity advisories; production runtime image does not ship Node.

`SMOKE_ADMIN_TOKEN` in `.env.local` is set by `scripts/create_demo_env.sh`. Playwright `baseURL` is `http://localhost:8000` (override with `BASE_URL`).

`scripts/ui_smoke.sh` runs a separate browser workflow check via `scripts/ui_browser_smoke.mjs`. CI runs scripts audit, UI smoke, then Playwright e2e (scrubbed env; see above).

## Source layout

```text
ui/
  index.html              # loads /src/app/main.ts
  vite.config.ts          # base: /admin/
  playwright.config.ts
  src/
    app/
      main.ts             # createApp, mount
      router.ts           # routes + auth guard
      pinia.ts
      config.ts           # AUTH_STORAGE_KEY, page sizes
      routeLoader.ts      # loadRouteData (router guard + post-login)
      tenantScope.ts      # requireTenantId, activeTenantId
      tenantNav.ts        # routeWithTenant
    api/                  # httpClient, types, *Api.ts
    stores/               # auth, tenant, checkpoint, signal, association, audit, overview, decisionTest, ui
    views/                # one file per route (OverviewView, CheckpointsView, …)
    components/
      layout/             # AppShell, SidebarNav, TenantSwitcher, AuthModal, ConfirmDialog
      primitives/         # ResourceTable, AppPagination, EmptyState, …
      workbench/          # PageHeader, WorkbenchLayout, TraceTimeline, JsonInspector, …
      domain/             # CheckpointForm, SignalForm, audit panels, variable panel
    composables/          # useConfirmDialog
    styles/
    tests/
      unit/
      e2e/
  dist/                   # gitignored; required at runtime
```

## Routing and tenant context

Routes are defined in `src/app/router.ts` (paths like `/checkpoints`, `/signals`, `/associations`). With Vite `base: /admin/`, the browser URL is `/admin/checkpoints`, etc.

The active tenant is stored in Pinia (`tenantStore`) and mirrored in the query string: `?tenant=<uuid>`. `tenantStore.setActiveTenant` updates both. `tenantStore.syncTenantFromRoute` applies `?tenant=` on load and clears `activeTenant` when the query is absent.

`routeWithTenant()` in `src/app/tenantNav.ts` merges `?tenant=` into sidebar links and other in-app navigation (`OverviewView` “Run test”, etc.).

`routeLoader.ts` loads view data via `loadRouteData(to)` in the router guard after auth. Tenant changes call `setActiveTenant()` → `router.replace({ query })`, which re-enters the guard and reloads once.

Tenant-scoped stores call `requireTenantId()` from `tenantScope.ts` before list/search/create. They clear local state when no tenant is selected. API modules pass `tenant_id` as a query parameter; there is no client-side filtering of cross-tenant rows.

## Responsive lists

`ResourceTable` shows the `#cards` slot below 768px when provided; otherwise it falls back to the `#table` slot so mobile views are not blank. Master-detail workbenches (`CheckpointsView`, `SignalsView`, `AuditView`, `DecisionTestView`) and `AssociationsView` define card layouts for narrow viewports.

## Dev vs production chrome

`SHOW_DEV_DEMO_UI` (`import.meta.env.DEV`) controls the development banner and local `.env.local` sign-in hints. Production builds (`npm run build`) omit that copy.

## Auth flow

1. `sessionStorage` key `decisionEngineAdminToken` (see `app/config.ts`).
2. Router guard calls `authStore.initializeFromStorage()` when `sessionValidated` is false.
3. Valid token → `bootstrap()` loads tenant list, sets `isReady`, guard calls `loadRouteData(to)`.
4. Missing/invalid token → `AuthModal`; on submit, `submitToken` then `loadRouteData` for the current route.
5. Deep links (e.g. `/admin/checkpoints?tenant=…`) are preserved; bootstrap does not redirect to overview.

## Forms

`CheckpointForm` and `SignalForm` use `<script setup lang="ts">`, a local draft ref, `v-model` on the parent draft, and `save` / `cancel` emits. Credential fields (`bearer_token`) are write-only in the form; they are not shown on read paths from the API.

## Static serving (FastAPI)

`main.py` class `AdminSPAStaticFiles` serves `ui/dist/`. Missing files with extensions like `.js` or `.css` return `404`. Extensionless document paths return `index.html` for Vue Router.
