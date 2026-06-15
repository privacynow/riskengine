# Roadmap

This project is a working prototype, not production-ready software.

## Milestone 1 (bootstrap + public repo hygiene) — complete

- Repo hygiene, schema alignment, Docker bootstrap, smoke test, demo mocks, initial commit

## Milestone 2 (runtime correctness)

- Tenant-aware and current-version-aware `POST /decisions`
- Immutable signal/checkpoint updates (POST new version + upstream checkpoint copy)
- Fix UI save wiring and remove duplicate create flows

## Milestone 3 (showcase polish)

- Authentication for `/ui/*`
- Stale OpenAPI refresh or generate from FastAPI
- CI matrix, broader tests, demo screenshots
- Honor `can_run_in_parallel` and configured timeouts

## Known limitations (demo)

- No authentication on admin or decision APIs
- Default Postgres credentials in Docker Compose
- Bearer tokens in sample data are clearly fake example values only
- In-memory cache is per-process only
