# Known issues

Open gaps in this prototype. Closed items and audit history are not tracked here.

| Area | Issue | Notes |
|------|-------|-------|
| API | Admin mutation responses use mixed shapes | Some endpoints return full resources, others return status-only payloads. Deferred until immutable writes land. |
| Data | Sample SQL fixtures are large and informal | Seed data works for demos but is not curated for public review. |
| Feature | Checkpoint/signal writes are mutable | Config changes update rows in place instead of version-on-write. Planned backend milestone; see [ROADMAP.md](../ROADMAP.md). |
| Docker | Runtime image includes `tests/` | Supports `docker compose exec risk-engine pytest` in CI and local smoke. Not a minimal production image. |
