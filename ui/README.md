# Decision Engine Admin UI

Vue 3 + Vite admin console. Built output goes to `dist/` and is served by FastAPI at `/admin/`.

```bash
npm ci
npm run dev      # Vite dev server
npm run build    # production bundle → dist/
```

Before starting the API locally without Docker:

```bash
npm ci && npm run build
cd .. && uvicorn main:app --reload
```

Docker builds the UI automatically in the multi-stage `Dockerfile` (`node:24-slim` → `python:3.10-slim`).
