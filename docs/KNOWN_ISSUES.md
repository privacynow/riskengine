# Known issues

Open gaps in this prototype. Closed items and audit history are not tracked here.

| Area | Issue | Notes |
|------|-------|-------|
| Data | Sample SQL fixtures are large | Curated with stable IDs documented in `sql/README.md`; still one file for Docker init simplicity. |
| Feature | Checkpoint/signal writes are mutable | Config changes update rows in place instead of version-on-write. Planned backend milestone; see [ROADMAP.md](ROADMAP.md). |
| UI | No version history or compare in admin | Saves follow backend in-place update semantics; no diff across signal/checkpoint versions. |
| Docker | Runtime image includes `tests/` | Supports `docker compose exec risk-engine pytest` in CI and local smoke. Not a minimal production image. |
