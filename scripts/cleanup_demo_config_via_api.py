#!/usr/bin/env python3
"""
Best-effort demo config cleanup using admin HTTP APIs only.

When DECISION_ENGINE_DEV_PURGE=1 is set on the server, this script first calls
POST /ui/dev/purge/tenant to remove audit/log/cache rows that block tenant delete.

For a true fresh bootstrap, still prefer: docker compose down -v && docker compose up -d --build
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env.local"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
CLEANUP_REASON = "Demo config cleanup via API script"
DEV_PURGE_BODY_PHRASE = (
    "I understand this permanently deletes dev audit data for the tenant"
)

SEED_TENANT_IDS = frozenset(
    {
        "11111111-1111-1111-1111-111111111111",  # SAMPLE LENDING
        "99999999-9999-9999-9999-999999999999",  # OTHER BANK
        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",  # VISUAL FIXTURE BANK
    }
)

# Explicit scratch/test name patterns only — avoid broad "demo"/"fixture" substrings
# that could match legitimate tenant names (e.g. "Customer Demo Bank").
SCRATCH_NAME_PATTERNS = (
    re.compile(r"scratch", re.I),
    re.compile(r"copy test", re.I),
    re.compile(r"authoring_e2e", re.I),
    re.compile(r"^e2e[-_]", re.I),
    re.compile(r"^test[-_]", re.I),
    re.compile(r"promotion-search-test", re.I),
    re.compile(r"promotion-detail-test", re.I),
    re.compile(r"cross-tenant-assoc-test", re.I),
    re.compile(r"reactivate-current-guard", re.I),
)


@dataclass
class Blocker:
    tenant_id: str
    tenant_name: str
    resource: str
    detail: str


@dataclass
class CleanupReport:
    tenants_considered: list[str] = field(default_factory=list)
    tenants_purged: int = 0
    associations_deleted: int = 0
    checkpoints_deactivated: int = 0
    signals_deactivated: int = 0
    checkpoints_deleted: int = 0
    signals_deleted: int = 0
    tenants_deleted: int = 0
    blockers: list[Blocker] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def read_env_var(name: str, path: Path = ENV_FILE) -> str | None:
    if not path.is_file():
        return None
    prefix = f"{name}="
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


class AdminClient:
    def __init__(self, base_url: str, token: str, *, dev_purge_confirm: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.dev_purge_confirm = dev_purge_confirm
        self.dev_purge_status: tuple[int, str] | None = None

    def post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        headers = dict(self.headers)
        if extra_headers:
            headers.update(extra_headers)
        return self._request("POST", path, payload, headers=headers)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        url = f"{self.base_url}{path}"
        data = None
        request_headers = dict(headers or self.headers)
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=request_headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                return response.status, body
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return exc.code, body

    def get_json(self, path: str) -> dict[str, Any]:
        status, body = self._request("GET", path)
        if status >= 400:
            raise RuntimeError(f"GET {path} failed: HTTP {status} {body}")
        return json.loads(body)

    def delete(self, path: str) -> tuple[int, str]:
        return self._request("DELETE", path)

    def check_dev_purge_status(self) -> tuple[int, str]:
        if self.dev_purge_status is not None:
            return self.dev_purge_status
        status, body = self._request("GET", "/ui/dev/purge/status")
        self.dev_purge_status = (status, body)
        return status, body

    def dev_purge_available(self) -> bool:
        status, _ = self.check_dev_purge_status()
        return status == 200

    def purge_tenant_operational_data(self, tenant_id: str) -> tuple[int, str]:
        if not self.dev_purge_confirm:
            return 403, "DECISION_ENGINE_DEV_PURGE_CONFIRM not configured locally"
        return self.post_json(
            "/ui/dev/purge/tenant",
            {
                "tenantId": tenant_id,
                "purgeReason": CLEANUP_REASON,
                "confirmPhrase": DEV_PURGE_BODY_PHRASE,
            },
            extra_headers={"X-Dev-Purge-Confirm": self.dev_purge_confirm},
        )

    def paginate(self, path: str) -> list[dict[str, Any]]:
        page = 1
        items: list[dict[str, Any]] = []
        total: int | None = None
        while True:
            separator = "&" if "?" in path else "?"
            payload = self.get_json(f"{path}{separator}page={page}&size=100")
            batch = payload.get("items") or []
            items.extend(batch)
            if total is None:
                total = int(payload.get("total", len(batch)))
            if len(items) >= total or not batch:
                break
            page += 1
        return items

    def all_checkpoints(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.paginate(f"/ui/checkpoints?tenant_id={tenant_id}")

    def all_signals(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.paginate(f"/ui/signals?tenant_id={tenant_id}")

    def all_associations(self, tenant_id: str) -> list[dict[str, Any]]:
        return self.paginate(f"/ui/checkpoint_signals?tenant_id={tenant_id}")


def tenant_matches_allowlist(
    tenant: dict[str, Any],
    *,
    include_seed_tenants: bool,
    extra_tenant_ids: set[str],
) -> bool:
    tenant_id = tenant["id"]
    name = tenant.get("name") or ""
    if tenant_id in extra_tenant_ids:
        return True
    if include_seed_tenants and tenant_id in SEED_TENANT_IDS:
        return True
    return any(pattern.search(name) for pattern in SCRATCH_NAME_PATTERNS)


def record_blocker(
    report: CleanupReport,
    tenant: dict[str, Any],
    resource: str,
    detail: str,
) -> None:
    report.blockers.append(
        Blocker(
            tenant_id=tenant["id"],
            tenant_name=tenant.get("name") or tenant["id"],
            resource=resource,
            detail=detail,
        )
    )


def deactivate_checkpoint(client: AdminClient, checkpoint_id: str) -> tuple[int, str]:
    return client.post_json(
        f"/ui/checkpoints/{checkpoint_id}/deactivate",
        {"promotionReason": CLEANUP_REASON},
    )


def deactivate_signal(client: AdminClient, signal_id: str) -> tuple[int, str]:
    return client.post_json(
        f"/ui/signals/{signal_id}/deactivate",
        {"promotionReason": CLEANUP_REASON},
    )


def cleanup_tenant(client: AdminClient, tenant: dict[str, Any], report: CleanupReport) -> None:
    tenant_id = tenant["id"]
    tenant_name = tenant.get("name") or tenant_id
    report.tenants_considered.append(f"{tenant_name} ({tenant_id})")

    purge_status, purge_body = client.check_dev_purge_status()
    if purge_status == 200:
        status, body = client.purge_tenant_operational_data(tenant_id)
        if status == 200:
            report.tenants_purged += 1
        else:
            record_blocker(
                report,
                tenant,
                "dev-purge",
                f"POST /ui/dev/purge/tenant -> HTTP {status} {body}",
            )
    elif purge_status == 404:
        report.notes.append(
            f"Skipped dev purge for {tenant_name}: DECISION_ENGINE_DEV_PURGE is not enabled on the server."
        )
    elif purge_status == 500:
        record_blocker(
            report,
            tenant,
            "dev-purge",
            (
                "Server dev purge is misconfigured "
                f"(GET /ui/dev/purge/status -> HTTP 500): {purge_body}. "
                "Set DECISION_ENGINE_DEV_PURGE_CONFIRM on the server and in .env.local."
            ),
        )
    else:
        record_blocker(
            report,
            tenant,
            "dev-purge",
            f"Unexpected dev purge status (GET /ui/dev/purge/status -> HTTP {purge_status}): {purge_body}",
        )

    associations = client.all_associations(tenant_id)
    for assoc in associations:
        status, body = client.delete(f"/ui/checkpoint_signals/{assoc['id']}")
        if status == 200:
            report.associations_deleted += 1
        else:
            record_blocker(
                report,
                tenant,
                f"association:{assoc['id']}",
                f"DELETE /ui/checkpoint_signals/{assoc['id']} -> HTTP {status} {body}",
            )

    checkpoints = client.all_checkpoints(tenant_id)
    for checkpoint in checkpoints:
        if checkpoint.get("is_current_version"):
            status, body = deactivate_checkpoint(client, checkpoint["id"])
            if status == 200:
                report.checkpoints_deactivated += 1
            else:
                record_blocker(
                    report,
                    tenant,
                    f"checkpoint:{checkpoint['name']}",
                    f"deactivate -> HTTP {status} {body}",
                )

    signals = client.all_signals(tenant_id)
    for signal in signals:
        if signal.get("is_current_version"):
            status, body = deactivate_signal(client, signal["id"])
            if status == 200:
                report.signals_deactivated += 1
            else:
                record_blocker(
                    report,
                    tenant,
                    f"signal:{signal['name']}",
                    f"deactivate -> HTTP {status} {body}",
                )

    checkpoints = client.all_checkpoints(tenant_id)
    for checkpoint in checkpoints:
        status, body = client.delete(f"/ui/checkpoints/{checkpoint['id']}")
        if status == 200:
            report.checkpoints_deleted += 1
            continue
        detail = body
        if status == 409:
            detail = (
                "Checkpoint delete blocked (likely still current or referenced). "
                f"HTTP {status}: {body}"
            )
        record_blocker(report, tenant, f"checkpoint:{checkpoint['name']}", detail)

    signals = client.all_signals(tenant_id)
    for signal in signals:
        status, body = client.delete(f"/ui/signals/{signal['id']}")
        if status == 200:
            report.signals_deleted += 1
            continue
        detail = body
        if signal.get("type") == "variable":
            detail = (
                "Signal delete failed; delete variable values first via "
                "GET /ui/signals/{id}/variable_values and DELETE /ui/variable_values/{id}, "
                "or enable dev purge. "
                f"HTTP {status}: {body}"
            )
        record_blocker(report, tenant, f"signal:{signal['name']}", detail)

    status, body = client.delete(f"/ui/tenants/{tenant_id}")
    if status == 200:
        report.tenants_deleted += 1
        return

    record_blocker(
        report,
        tenant,
        "tenant",
        (
            "Tenant delete failed; remaining dependencies may include config rows or FK references. "
            "Enable DECISION_ENGINE_DEV_PURGE on the server and retry, or recreate the DB volume. "
            f"HTTP {status}: {body}"
        ),
    )


def print_report(report: CleanupReport) -> None:
    print("Demo config cleanup report")
    print("=" * 72)
    if report.tenants_considered:
        print("Tenants considered:")
        for entry in report.tenants_considered:
            print(f"  - {entry}")
    else:
        print("Tenants considered: none matched allowlist")

    print()
    print(f"Tenants purged (audit):   {report.tenants_purged}")
    print(f"Associations deleted:     {report.associations_deleted}")
    print(f"Checkpoints deactivated:  {report.checkpoints_deactivated}")
    print(f"Signals deactivated:      {report.signals_deactivated}")
    print(f"Checkpoints deleted:      {report.checkpoints_deleted}")
    print(f"Signals deleted:          {report.signals_deleted}")
    print(f"Tenants deleted:          {report.tenants_deleted}")

    for note in report.notes:
        print(f"\nNote: {note}")

    if report.blockers:
        print("\nUnresolved blockers:")
        for blocker in report.blockers:
            print(f"  [{blocker.tenant_name}] {blocker.resource}")
            print(f"    {blocker.detail}")

    print()
    if report.blockers:
        print(
            "Cleanup incomplete for some resources. For a full reset, recreate the DB volume "
            "and apply sql/02_sample_data.sql on bootstrap."
        )
    else:
        print("Cleanup completed for all targeted resources.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=read_env_var("BASE_URL") or DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--token",
        default=read_env_var("SMOKE_ADMIN_TOKEN"),
        help="Admin bearer token (default: SMOKE_ADMIN_TOKEN from .env.local)",
    )
    parser.add_argument(
        "--tenant-id",
        action="append",
        default=[],
        help="Tenant UUID to include (repeatable; primary way to target a specific tenant)",
    )
    parser.add_argument(
        "--include-seed-tenants",
        action="store_true",
        help="Also target seeded demo tenants (SAMPLE LENDING, OTHER BANK, VISUAL FIXTURE BANK)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List tenants that would be cleaned without mutating anything",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required to perform destructive cleanup",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.token:
        print("Missing admin token. Set SMOKE_ADMIN_TOKEN in .env.local or pass --token.", file=sys.stderr)
        return 1

    client = AdminClient(
        args.base_url,
        args.token,
        dev_purge_confirm=read_env_var("DECISION_ENGINE_DEV_PURGE_CONFIRM"),
    )
    try:
        tenants = client.paginate("/ui/tenants")
    except (urllib.error.URLError, RuntimeError) as exc:
        print(f"Failed to reach admin API at {args.base_url}: {exc}", file=sys.stderr)
        return 1

    extra_ids = set(args.tenant_id)
    targets = [
        tenant
        for tenant in tenants
        if tenant_matches_allowlist(
            tenant,
            include_seed_tenants=args.include_seed_tenants,
            extra_tenant_ids=extra_ids,
        )
    ]

    if args.dry_run:
        print(f"Base URL: {args.base_url}")
        print("Tenants that would be cleaned:")
        if not targets:
            print("  (none matched allowlist)")
        for tenant in targets:
            print(f"  - {tenant.get('name')} ({tenant['id']})")
        return 0

    if not args.yes:
        print("Refusing to run without --yes.", file=sys.stderr)
        print("Dry run: python3 scripts/cleanup_demo_config_via_api.py --dry-run", file=sys.stderr)
        return 1

    if not targets:
        print("No tenants matched the cleanup allowlist.")
        return 0

    report = CleanupReport()
    if args.include_seed_tenants:
        report.notes.append(
            "Seed tenants were in scope. Re-bootstrap curated demo data from sql/02_sample_data.sql "
            "or recreate the Postgres volume."
        )

    for tenant in targets:
        cleanup_tenant(client, tenant, report)

    print_report(report)
    return 1 if report.blockers else 0


if __name__ == "__main__":
    raise SystemExit(main())
