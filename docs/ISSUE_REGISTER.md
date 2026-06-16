# Issue Register

Baseline: `800cd54` + showcase hygiene work in progress. Severity: P0 publish blocker, P1 serious, P2 engineering quality, P3 polish.

| ID | Severity | Area | Finding | Status | Verified at |
|----|----------|------|---------|--------|-------------|
| P0-REMOTE | P0 | Git | Pushed `main` must include security hygiene commits | Open | — |
| P0-SECRETS | P0 | Git | No committed tokens, `.env.local`, or auth files | Closed | `800cd54` |
| P1-UNCOMMITTED | P1 | Git | Security refactor only in working tree | Closed | committed `800cd54` |
| P1-STALE-API | P1 | Docs | Stale `api/*.yml` contradict runtime | Closed | `7fcdd2d` |
| P2-TEMPLATE-LEAK | P2 | Security | Template/header secrets in API responses | Closed | `800cd54` |
| P2-TEMPLATE-WRITE | P2 | Security | Embedded credentials in template writes | Closed | `800cd54` + placeholder names |
| P2-TENANT-COPY-TOKEN | P2 | Security | Tenant copy clones bearer tokens | Closed | `800cd54` |
| P2-TENANT-COPY-LINK | P2 | Correctness | Copy dropped stale signal associations | Closed | `800cd54` |
| P2-PARAM-READ | P2 | Security | Historical decision param_values leak | Closed | `800cd54` |
| P2-ADMIN-LOG-READ | P2 | Security | Admin search_signal_logs raw param_values | Closed | this branch |
| P2-AUTH-TOKEN-CTX | P2 | Security | Raw bearer in AuthContext | Closed | `800cd54` |
| P2-HTTP-500 | P2 | Correctness | HTTPException wrapped as 500 | Closed | `800cd54` |
| P2-ERROR-CTX | P2 | Ops | Wrong raise_admin_error log contexts | Closed | `800cd54` |
| P2-LOOPBACK | P2 | Security | App bound to all interfaces | Closed | `7fcdd2d` |
| P2-SSRF-CLAIMS | P2 | Docs | Outbound URL policy oversold | Closed | README `800cd54` |
| P2-UI-HTTP-TYPE | P2 | UI | UI uses `http` type; backend uses endpoint types | Closed | this branch |
| P2-UI-DUP-MODAL | P2 | UI | Duplicate checkpoint confirmation modal | Closed | this branch |
| P2-UI-MONOLITH | P2 | UI | Monolithic app.js / index.html | Open | deferred split |
| P2-UI-ALERTS | P2 | UI | Scattered alert() error handling | Closed | this branch |
| P2-ADMIN-CONTRACT | P2 | API | Mixed admin mutation response shapes | Open | deferred |
| P3-ROADMAP-VOICE | P3 | Docs | Milestone/chat wording in ROADMAP | Closed | this branch |
| P3-DESIGN-NOTES | P3 | Docs | No explicit tradeoff documentation | Closed | this branch |
| P3-SAMPLE-SQL | P3 | Data | Large casual seed file | Open | deferred |
| P3-CI | P3 | Ops | No GitHub Actions | Closed | this branch |
| P3-2F-IMMUTABLE | P3 | Feature | Immutable checkpoint/signal writes | Open | deferred |

## Done criteria (showcase)

- `git status --short` clean except ignored local files
- `pytest` and `smoke_test.sh` pass from committed tree
- No raw connector secrets on read paths (runtime, historical decisions, admin log search)
- UI signal types align with backend
- ROADMAP and DESIGN_NOTES read as engineering artifacts, not chat history
