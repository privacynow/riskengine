import os
import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import OTHER_TENANT, SAMPLE_TENANT, TEST_ADMIN_TOKEN, TEST_SAMPLE_TOKEN
from tests.seed_reset import SEED_CHECKPOINT_CURRENT

SEED_ONBOARDING_CHECKPOINT = SEED_CHECKPOINT_CURRENT[SAMPLE_TENANT]["Onboarding"]
SEED_FUNDS_DISBURSEMENT_CHECKPOINT = SEED_CHECKPOINT_CURRENT[SAMPLE_TENANT]["Funds Disbursement"]
FUNDS_DISBURSEMENT_DSL = (
    "disbursement_limit_check and (previous_delinquency == 0) and credit_pass"
)


@pytest.fixture
def client():
    from engine.main import app

    return TestClient(app)


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.skipif(
    os.environ.get("DB_HOST", "localhost") == "localhost"
    and not os.environ.get("RUN_INTEGRATION_TESTS"),
    reason="Integration tests require Postgres (set DB_HOST or RUN_INTEGRATION_TESTS=1)",
)
class TestAdminHygiene:
    def test_make_current_missing_checkpoint_returns_404_not_500(self, client):
        resp = client.post(
            "/ui/checkpoints/00000000-0000-0000-0000-000000000000/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Regression test promotion"},
        )
        assert resp.status_code == 404

    def test_make_current_requires_promotion_reason(self, client):
        target = client.get(
            f"/ui/checkpoints/{SEED_ONBOARDING_CHECKPOINT}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert target["name"] == "Onboarding"

        missing = client.post(
            f"/ui/checkpoints/{target['id']}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert missing.status_code == 422

        empty = client.post(
            f"/ui/checkpoints/{target['id']}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "  "},
        )
        assert empty.status_code == 422

        short = client.post(
            f"/ui/checkpoints/{target['id']}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "no"},
        )
        assert short.status_code == 422

    def test_make_current_persists_promotion_audit(self, client):
        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "promotion-audit-test",
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        assert created.status_code == 200
        checkpoint_id = created.json()["id"]
        reason = "Promote for audit persistence test"

        promoted = client.post(
            f"/ui/checkpoints/{checkpoint_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": reason},
        )
        assert promoted.status_code == 200

        from engine.db import db_cursor

        with db_cursor() as (_, cur):
            cur.execute(
                """
                SELECT resource_type, resource_id::text, resource_name, promotion_reason
                  FROM promotion_audit
                 WHERE resource_id = %s
                 ORDER BY created_at DESC
                 LIMIT 1
                """,
                (checkpoint_id,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "checkpoint"
        assert row[1] == checkpoint_id
        assert row[2] == "promotion-audit-test"
        assert row[3] == reason

    def test_signal_make_current_requires_promotion_reason(self, client):
        listed = client.get(
            f"/ui/signals?tenant_id={SAMPLE_TENANT}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        target = next(item for item in listed if item["name"] == "age_check")

        missing = client.post(
            f"/ui/signals/{target['id']}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert missing.status_code == 422

    def test_all_tenants_is_not_limited_by_page_cap(self, client):
        from engine.db import db_cursor

        created_ids = [str(uuid.uuid4()) for _ in range(105)]
        try:
            with db_cursor() as (conn, cur):
                for index, tenant_id in enumerate(created_ids):
                    cur.execute(
                        """
                        INSERT INTO tenants (id, name)
                        VALUES (%s, %s)
                        """,
                        (tenant_id, f"zz-all-tenants-regression-{index:03d}"),
                    )
                conn.commit()

            resp = client.get("/ui/all_tenants", headers=auth_header(TEST_ADMIN_TOKEN))
            assert resp.status_code == 200
            returned_ids = {item["id"] for item in resp.json()}
            assert set(created_ids).issubset(returned_ids)
        finally:
            with db_cursor() as (conn, cur):
                for tenant_id in created_ids:
                    cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))
                conn.commit()

    def test_create_checkpoint_with_associated_signals(self, client):
        age_check_id = "33333333-3333-3333-3333-333333333301"
        blocklist_id = "33333333-3333-3333-3333-333333333302"

        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "assoc-create-test",
                "type": "onboarding",
                "dsl_expression": "age_check and not blocklist_check",
                "signals": [age_check_id, blocklist_id],
            },
        )
        assert created.status_code == 200
        checkpoint_id = created.json()["id"]
        assert created.json().get("association_count") == 2

        linked = client.get(
            f"/ui/signals?checkpoint_id={checkpoint_id}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        linked_names = {item["name"] for item in linked}
        assert linked_names == {"age_check", "blocklist_check"}

    def test_create_checkpoint_rejects_cross_tenant_signal(self, client):
        foreign = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": OTHER_TENANT,
                "name": "foreign-only-signal",
                "type": "expression",
                "expression_body": "True",
            },
        )
        assert foreign.status_code == 200
        foreign_id = foreign.json()["id"]

        resp = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "cross-tenant-assoc-test",
                "type": "onboarding",
                "dsl_expression": "True",
                "signals": [foreign_id],
            },
        )
        assert resp.status_code == 422

        missing = client.get(
            f"/ui/search_checkpoints?q=cross-tenant-assoc-test&tenant_id={SAMPLE_TENANT}&page=1&size=5",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        assert not any(item["name"] == "cross-tenant-assoc-test" for item in missing)

    def test_create_signal_version_copies_variable_values_only(self, client):
        source = client.get(
            f"/ui/signals?tenant_id={SAMPLE_TENANT}&q=age_check&page=1&size=1",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"][0]
        source_id = source["id"]

        created = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": source["name"],
                "description": "forked version",
                "type": source["type"],
                "method_of_call": source.get("method_of_call"),
                "expression_body": source.get("expression_body") or "True",
                "copyFromSignalId": source_id,
            },
        )
        assert created.status_code == 200
        new_id = created.json()["id"]
        assert new_id != source_id

        assoc = client.get(
            f"/ui/checkpoint_signals?signal_id={new_id}&tenant_id={SAMPLE_TENANT}&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        assert assoc == []

    def test_create_checkpoint_signal_rejects_duplicate_logical_name(self, client):
        age_check = client.get(
            f"/ui/signals?tenant_id={SAMPLE_TENANT}&q=age_check&page=1&size=1",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"][0]
        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": f"dup-assoc-guard-{uuid.uuid4().hex[:8]}",
                "type": "onboarding",
                "dsl_expression": "True",
                "signals": [age_check["id"]],
            },
        )
        assert created.status_code == 200
        checkpoint_id = created.json()["id"]

        resp = client.post(
            "/ui/checkpoint_signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "checkpoint_id": checkpoint_id,
                "signal_id": age_check["id"],
            },
        )
        assert resp.status_code == 409

    def test_create_checkpoint_rejects_duplicate_logical_signal_names(self, client):
        age_check = client.get(
            f"/ui/signals?tenant_id={SAMPLE_TENANT}&q=age_check&page=1&size=1",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"][0]
        fork = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": age_check["name"],
                "type": "expression",
                "expression_body": "True",
            },
        )
        assert fork.status_code == 200

        resp = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": f"dup-create-guard-{uuid.uuid4().hex[:8]}",
                "type": "onboarding",
                "dsl_expression": "True",
                "signals": [age_check["id"], fork.json()["id"]],
            },
        )
        assert resp.status_code == 409

    def test_create_checkpoint_signal_rejects_cross_tenant(self, client):
        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": f"cross-tenant-link-{uuid.uuid4().hex[:8]}",
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        assert created.status_code == 200
        foreign = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": OTHER_TENANT,
                "name": "foreign-assoc-signal",
                "type": "expression",
                "expression_body": "True",
            },
        )
        assert foreign.status_code == 200

        resp = client.post(
            "/ui/checkpoint_signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "checkpoint_id": created.json()["id"],
                "signal_id": foreign.json()["id"],
            },
        )
        assert resp.status_code == 422

    def test_create_checkpoint_rejects_invalid_signal_uuid(self, client):
        resp = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "invalid-signal-id",
                "type": "onboarding",
                "dsl_expression": "True",
                "signals": ["not-a-uuid"],
            },
        )
        assert resp.status_code == 422

    def test_create_checkpoint_rejects_invalid_copy_from_uuid(self, client):
        resp = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "invalid-copy-from",
                "type": "onboarding",
                "dsl_expression": "True",
                "copyFromCheckpointId": "not-a-uuid",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "path",
        [
            "/ui/promotion_audit/not-a-uuid",
            "/ui/checkpoints/not-a-uuid",
            "/ui/signals/not-a-uuid",
        ],
    )
    def test_invalid_uuid_path_returns_422(self, client, path):
        resp = client.get(path, headers=auth_header(TEST_ADMIN_TOKEN))
        assert resp.status_code == 422

    def test_create_checkpoint_rejects_unknown_write_fields(self, client):
        resp = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "save-time-promote-blocked",
                "type": "onboarding",
                "dsl_expression": "True",
                "makeCurrentVersion": True,
            },
        )
        assert resp.status_code == 422

    def test_dsl_preflight_rejects_unknown_identifiers(self, client):
        resp = client.post(
            "/ui/dsl_preflight",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "dsl_expression": "age_check and mystery_signal",
                "signal_names": ["age_check"],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert any("mystery_signal" in err for err in body["errors"])

    def test_search_promotion_audit_filters_by_tenant(self, client):
        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "promotion-search-test",
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        checkpoint_id = created.json()["id"]
        client.post(
            f"/ui/checkpoints/{checkpoint_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Search surface integration test"},
        )

        resp = client.get(
            f"/ui/promotion_audit?tenant_id={SAMPLE_TENANT}&q=promotion-search-test&page=1&size=10",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        assert items[0]["resource_name"] == "promotion-search-test"
        assert items[0]["promotion_reason"] == "Search surface integration test"

    def test_get_promotion_audit_by_id(self, client):
        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "promotion-detail-test",
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        checkpoint_id = created.json()["id"]
        client.post(
            f"/ui/checkpoints/{checkpoint_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Detail fetch integration test"},
        )

        listed = client.get(
            f"/ui/promotion_audit?tenant_id={SAMPLE_TENANT}&q=promotion-detail-test&page=1&size=1",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        promotion_id = listed.json()["items"][0]["id"]

        detail = client.get(
            f"/ui/promotion_audit/{promotion_id}?tenant_id={SAMPLE_TENANT}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert detail.status_code == 200
        body = detail.json()
        assert body["id"] == promotion_id
        assert body["resource_name"] == "promotion-detail-test"
        assert body["promotion_reason"] == "Detail fetch integration test"

        missing = client.get(
            f"/ui/promotion_audit/{promotion_id}?tenant_id={OTHER_TENANT}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert missing.status_code == 404

    def test_runtime_checkpoint_omits_template_fields(self, client):
        resp = client.get(
            "/checkpoints/Onboarding",
            headers=auth_header(TEST_SAMPLE_TOKEN),
        )
        assert resp.status_code == 200
        for signal in resp.json()["signals"]:
            assert "request_headers_template" not in signal
            assert "request_body_template" not in signal
            assert "request_url_params_template" not in signal

    def test_admin_signal_list_redacts_header_templates(self, client):
        resp = client.get("/ui/signals?page=1&size=50", headers=auth_header(TEST_ADMIN_TOKEN))
        assert resp.status_code == 200
        for signal in resp.json()["items"]:
            headers = signal.get("request_headers_template") or ""
            assert "Bearer" not in headers or "[REDACTED]" in headers
            assert "bearer_token" not in signal

    def test_search_checkpoints_filters_by_tenant_id(self, client):
        sample = client.get(
            "/ui/search_checkpoints?q=Onboarding&tenant_id="
            f"{SAMPLE_TENANT}&page=1&size=10",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert sample.status_code == 200
        sample_items = sample.json()["items"]
        assert sample_items
        assert all(item["tenant_id"] == SAMPLE_TENANT for item in sample_items)

        other = client.get(
            f"/ui/search_checkpoints?q=Onboarding&tenant_id={OTHER_TENANT}&page=1&size=10",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert other.status_code == 200
        for item in other.json()["items"]:
            assert item["tenant_id"] == OTHER_TENANT

    def test_spa_fallback_serves_index_for_document_routes(self, client):
        resp = client.get("/admin/checkpoints")
        assert resp.status_code == 200
        assert "Decision Engine Admin" in resp.text

    def test_missing_admin_js_asset_returns_404(self, client):
        resp = client.get("/admin/assets/missing-bundle-deadbeef.js")
        assert resp.status_code == 404
        assert "Decision Engine Admin" not in resp.text

    def test_admin_get_checkpoint_includes_is_current_version(self, client):
        current = client.get(
            f"/ui/checkpoints/{SEED_ONBOARDING_CHECKPOINT}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert current["name"] == "Onboarding"
        assert current["is_current_version"] is True
        assert current["name_has_current_version"] is True
        detail = client.get(
            f"/ui/checkpoints/{current['id']}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert detail["is_current_version"] is True
        assert detail["name_has_current_version"] is True

    def test_admin_get_signal_includes_is_current_version(self, client):
        listed = client.get(
            f"/ui/signals?tenant_id={SAMPLE_TENANT}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        current = next(item for item in listed if item.get("is_current_version"))
        detail = client.get(
            f"/ui/signals/{current['id']}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert detail["is_current_version"] is True

    def test_admin_test_decision_checkpoint_id_runs_selected_version(self, client):
        fork_name = "admin-version-fork-test"
        stale = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": fork_name,
                "type": "onboarding",
                "dsl_expression": "False",
            },
        )
        assert stale.status_code == 200
        stale_id = stale.json()["id"]

        by_name = client.post(
            "/ui/test_decisions",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "checkpoint_name": "Onboarding",
                "correlation_id": "admin-test-by-name",
            },
        )
        assert by_name.status_code == 200
        assert by_name.json()["final_decision_value"] == "True"

        by_id = client.post(
            "/ui/test_decisions",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "checkpoint_name": fork_name,
                "checkpoint_id": stale_id,
                "correlation_id": "admin-test-by-id",
            },
        )
        assert by_id.status_code == 200
        assert by_id.json()["final_decision_value"] == "False"

    def test_search_decisions_includes_checkpoint_name_and_tenant_filter(self, client):
        resp = client.get(
            f"/ui/search_decisions?tenant_id={SAMPLE_TENANT}&q=Onboarding&page=1&size=10",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items
        assert all(item["tenant_id"] == SAMPLE_TENANT for item in items)
        assert any(item.get("checkpoint_name") == "Onboarding" for item in items)

        other = client.get(
            f"/ui/search_decisions?tenant_id={OTHER_TENANT}&q=Onboarding&page=1&size=10",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert other.status_code == 200
        for item in other.json()["items"]:
            assert item["tenant_id"] == OTHER_TENANT

    def test_search_signal_logs_failures_only_and_signal_name(self, client):
        resp = client.get(
            f"/ui/search_signal_logs?tenant_id={SAMPLE_TENANT}&failures_only=true&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["success"] is False
            if item.get("signal_name"):
                assert isinstance(item["signal_name"], str)

    def test_search_signal_logs_paginates_distinct_logs_before_params(self, client):
        from engine.db import db_cursor

        marker = f"log-page-{uuid.uuid4().hex[:8]}"
        decision_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        signal_log_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    """
                    SELECT signal_id
                      FROM signal_current_version
                     WHERE tenant_id = %s AND name = 'age_check'
                    """,
                    (SAMPLE_TENANT,),
                )
                signal_id = str(cur.fetchone()[0])
                for idx, decision_id in enumerate(decision_ids):
                    cur.execute(
                        """
                        INSERT INTO decision_log (
                            id, checkpoint_id, tenant_id, applicant_id,
                            final_decision_value, cost_incurred, correlation_id,
                            decision_timestamp
                        )
                        VALUES (%s, %s, %s, %s, 'True', 0, %s, NOW() - (%s * INTERVAL '1 minute'))
                        """,
                        (
                            decision_id,
                            SEED_ONBOARDING_CHECKPOINT,
                            SAMPLE_TENANT,
                            f"{marker}-app-{idx}",
                            f"{marker}-corr-{idx}",
                            idx,
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO signal_log (
                            id, decision_log_id, signal_id, applicant_id,
                            signal_value, started_at, completed_at,
                            cost_incurred, success
                        )
                        VALUES (%s, %s, %s, %s, 'True',
                                NOW() - (%s * INTERVAL '1 minute'),
                                NOW() - (%s * INTERVAL '1 minute'),
                                0, TRUE)
                        """,
                        (
                            signal_log_ids[idx],
                            decision_id,
                            signal_id,
                            f"{marker}-app-{idx}",
                            idx,
                            idx,
                        ),
                    )
                for param_name in ["first", "second"]:
                    cur.execute(
                        """
                        INSERT INTO signal_log_values (
                            id, signal_log_id, param_name, param_value
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            signal_log_ids[0],
                            param_name,
                            f"{marker}-{param_name}",
                        ),
                    )
                conn.commit()

            resp = client.get(
                f"/ui/search_signal_logs?tenant_id={SAMPLE_TENANT}&q={marker}&page=1&size=2",
                headers=auth_header(TEST_ADMIN_TOKEN),
            )
            assert resp.status_code == 200
            items = resp.json()["items"]
            assert len(items) == 2
            assert {item["id"] for item in items} == set(signal_log_ids)
            first = next(item for item in items if item["id"] == signal_log_ids[0])
            assert {param["param_name"] for param in first["param_values"]} == {
                "first",
                "second",
            }
        finally:
            with db_cursor() as (conn, cur):
                cur.execute(
                    "DELETE FROM signal_log_values WHERE signal_log_id = ANY(%s::uuid[])",
                    (signal_log_ids,),
                )
                cur.execute(
                    "DELETE FROM signal_log WHERE id = ANY(%s::uuid[])",
                    (signal_log_ids,),
                )
                cur.execute(
                    "DELETE FROM decision_log WHERE id = ANY(%s::uuid[])",
                    (decision_ids,),
                )
                conn.commit()

    def test_dsl_preflight_endpoint(self, client):
        ok = client.post(
            "/ui/dsl_preflight",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "dsl_expression": "age_check and kyc_score > 80",
                "signal_names": ["age_check", "kyc_score"],
            },
        )
        assert ok.status_code == 200
        assert ok.json()["ok"] is True

        bad = client.post(
            "/ui/dsl_preflight",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"dsl_expression": "age_check and (", "signal_names": ["age_check"]},
        )
        assert bad.status_code == 200
        assert bad.json()["ok"] is False

    def test_dsl_preflight_resolves_linked_signals_from_checkpoint_id(self, client):
        resp = client.post(
            "/ui/dsl_preflight",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "dsl_expression": FUNDS_DISBURSEMENT_DSL,
                "checkpoint_id": SEED_FUNDS_DISBURSEMENT_CHECKPOINT,
                "signal_names": [],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_dsl_preflight_empty_names_without_checkpoint_id_fails(self, client):
        resp = client.post(
            "/ui/dsl_preflight",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "dsl_expression": FUNDS_DISBURSEMENT_DSL,
                "signal_names": [],
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert any("credit_pass" in err for err in body["errors"])

    def test_dsl_preflight_new_checkpoint_draft_requires_client_signal_names(self, client):
        resp = client.post(
            "/ui/dsl_preflight",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "dsl_expression": "age_check and kyc_score > 80",
                "signal_names": [],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is False

    def test_admin_mutation_response_envelope(self, client):
        resp = client.post(
            "/ui/checkpoints/00000000-0000-0000-0000-000000000000/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Envelope test promotion"},
        )
        assert resp.status_code == 404

        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "mutation-envelope-test",
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        assert created.status_code == 200
        body = created.json()
        assert body["ok"] is True
        assert body["action"] == "created"
        assert body["id"]

        promoted = client.post(
            f"/ui/checkpoints/{body['id']}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Mutation envelope promotion"},
        )
        assert promoted.status_code == 200
        promoted_body = promoted.json()
        assert promoted_body == {"ok": True, "action": "promoted", "id": body["id"]}

    def test_copy_tenant_clears_bearer_tokens_and_preserves_links(self, client):
        create = client.post(
            "/ui/tenants",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"name": "COPY TEST TENANT", "copyFromTenantId": SAMPLE_TENANT},
        )
        assert create.status_code == 200
        new_tenant_id = create.json()["id"]

        source_cp = client.get(
            f"/ui/checkpoints?tenant_id={SAMPLE_TENANT}&active_only=true&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        source_onboarding = next(item for item in source_cp if item["name"] == "Onboarding")
        source_links = client.get(
            f"/ui/signals?checkpoint_id={source_onboarding['id']}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]

        copied_cp = client.get(
            f"/ui/checkpoints?tenant_id={new_tenant_id}&active_only=true&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        copied_onboarding = next(item for item in copied_cp if item["name"] == "Onboarding")

        copied_links = client.get(
            f"/ui/signals?checkpoint_id={copied_onboarding['id']}&page=1&size=50",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]

        source_names = {s["name"] for s in source_links if s.get("is_current_version")}
        copied_names = {s["name"] for s in copied_links}

        assert copied_names == source_names
        assert len(copied_names) >= 3
        assert all(signal["has_bearer_token"] is False for signal in copied_links)

    def test_copy_tenant_preserves_stale_signal_associations(self, client):
        from engine.db import db_cursor

        old_signal_id = None
        new_signal_id = None
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    """
                    SELECT signal_id
                      FROM signal_current_version
                     WHERE tenant_id = %s AND name = 'age_check'
                    """,
                    (SAMPLE_TENANT,),
                )
                row = cur.fetchone()
                assert row is not None
                old_signal_id = str(row[0])

                cur.execute(
                    """
                    INSERT INTO signals (
                        tenant_id, name, description, type, method_of_call,
                        expression_body, cost, cache_expiration_seconds, timeout_seconds,
                        can_run_in_parallel, order_of_evaluation, http_method,
                        request_url_params_template, request_body_template,
                        request_headers_template, bearer_token, allow_caching,
                        global_reuse, function_params_template
                    )
                    SELECT tenant_id, name, description, type, method_of_call,
                           expression_body, cost, cache_expiration_seconds, timeout_seconds,
                           can_run_in_parallel, order_of_evaluation, http_method,
                           request_url_params_template, request_body_template,
                           request_headers_template, NULL, allow_caching,
                           global_reuse, function_params_template
                      FROM signals
                     WHERE id = %s
                    RETURNING id
                    """,
                    (old_signal_id,),
                )
                new_signal_id = str(cur.fetchone()[0])

                cur.execute(
                    """
                    UPDATE signal_current_version
                       SET signal_id = %s, updated_at = NOW()
                     WHERE tenant_id = %s AND name = 'age_check'
                    """,
                    (new_signal_id, SAMPLE_TENANT),
                )
                conn.commit()

            create = client.post(
                "/ui/tenants",
                headers=auth_header(TEST_ADMIN_TOKEN),
                json={"name": "STALE LINK COPY TEST", "copyFromTenantId": SAMPLE_TENANT},
            )
            assert create.status_code == 200
            new_tenant_id = create.json()["id"]

            copied_cp = client.get(
                f"/ui/checkpoints?tenant_id={new_tenant_id}&active_only=true&page=1&size=50",
                headers=auth_header(TEST_ADMIN_TOKEN),
            ).json()["items"]
            copied_onboarding = next(item for item in copied_cp if item["name"] == "Onboarding")
            copied_links = client.get(
                f"/ui/signals?checkpoint_id={copied_onboarding['id']}&page=1&size=50",
                headers=auth_header(TEST_ADMIN_TOKEN),
            ).json()["items"]
            copied_names = {signal["name"] for signal in copied_links}

            assert "age_check" in copied_names
        finally:
            if old_signal_id and new_signal_id:
                with db_cursor() as (conn, cur):
                    cur.execute(
                        """
                        UPDATE signal_current_version
                           SET signal_id = %s, updated_at = NOW()
                         WHERE tenant_id = %s AND name = 'age_check'
                        """,
                        (old_signal_id, SAMPLE_TENANT),
                    )
                    cur.execute("DELETE FROM signals WHERE id = %s", (new_signal_id,))
                    conn.commit()

    def test_historical_decision_redacts_param_values(self, client):
        from engine.db import db_cursor

        decision_id = "55555555-5555-5555-5555-555555555555"
        signal_log_id = "66666666-6666-6666-6666-666666666666"
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    """
                    INSERT INTO decision_log (
                        id, checkpoint_id, tenant_id, applicant_id,
                        final_decision_value, cost_incurred, correlation_id
                    ) VALUES (
                        %s,
                        '22222222-2222-2222-2222-222222222201',
                        %s,
                        'param-redaction-test',
                        'PENDING',
                        0,
                        'param-redaction-correlation'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (decision_id, SAMPLE_TENANT),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log (
                        id, decision_log_id, signal_id, applicant_id,
                        signal_value, cost_incurred, success
                    ) VALUES (
                        %s, %s, '33333333-3333-3333-3333-333333333301',
                        'param-redaction-test', 'True', 0, TRUE
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (signal_log_id, decision_id),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log_values (signal_log_id, param_name, param_value)
                    VALUES (%s, 'Authorization', 'Bearer leaked-historical-token')
                    """,
                    (signal_log_id,),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log_values (signal_log_id, param_name, param_value)
                    VALUES (%s, 'user_id', '12345')
                    """,
                    (signal_log_id,),
                )
                conn.commit()

            resp = client.get(
                f"/decisions/{decision_id}",
                headers=auth_header(TEST_SAMPLE_TOKEN),
            )
            assert resp.status_code == 200
            params = resp.json()["signals"][0]["param_values"]
            assert params["Authorization"] == "[REDACTED]"
            assert params["user_id"] == "12345"
            assert "leaked-historical-token" not in str(resp.json())
        finally:
            with db_cursor() as (conn, cur):
                cur.execute(
                    "DELETE FROM signal_log_values WHERE signal_log_id = %s",
                    (signal_log_id,),
                )
                cur.execute("DELETE FROM signal_log WHERE id = %s", (signal_log_id,))
                cur.execute("DELETE FROM decision_log WHERE id = %s", (decision_id,))
                conn.commit()

    def test_signal_create_rejects_embedded_authorization_header(self, client):
        resp = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "bad-secret-signal",
                "type": "internal_endpoint",
                "method_of_call": "http://127.0.0.1:8000/mock/onboarding",
                "request_headers_template": "Authorization: Bearer secret-in-template",
            },
        )
        assert resp.status_code == 422

    def test_signal_create_rejects_sensitive_placeholder_in_template(self, client):
        resp = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": "bad-placeholder-signal",
                "type": "internal_endpoint",
                "method_of_call": "http://127.0.0.1:8000/mock/onboarding",
                "request_headers_template": "X-Custom: %api_key%",
            },
        )
        assert resp.status_code == 422

    def test_search_signal_logs_redacts_param_values(self, client):
        from engine.db import db_cursor

        decision_id = "77777777-7777-7777-7777-777777777777"
        signal_log_id = "88888888-8888-8888-8888-888888888888"
        try:
            with db_cursor() as (conn, cur):
                cur.execute(
                    """
                    INSERT INTO decision_log (
                        id, checkpoint_id, tenant_id, applicant_id,
                        final_decision_value, cost_incurred, correlation_id
                    ) VALUES (
                        %s,
                        '22222222-2222-2222-2222-222222222201',
                        %s,
                        'admin-log-redaction-test',
                        'PENDING',
                        0,
                        'admin-log-redaction-correlation'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (decision_id, SAMPLE_TENANT),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log (
                        id, decision_log_id, signal_id, applicant_id,
                        signal_value, cost_incurred, success
                    ) VALUES (
                        %s, %s, '33333333-3333-3333-3333-333333333301',
                        'admin-log-redaction-test', 'True', 0, TRUE
                    )
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (signal_log_id, decision_id),
                )
                cur.execute(
                    """
                    INSERT INTO signal_log_values (signal_log_id, param_name, param_value)
                    VALUES (%s, 'Authorization', 'Bearer admin-log-secret')
                    """,
                    (signal_log_id,),
                )
                conn.commit()

            resp = client.get(
                "/ui/search_signal_logs?q=admin-log-redaction-test&page=1&size=10",
                headers=auth_header(TEST_ADMIN_TOKEN),
            )
            assert resp.status_code == 200
            items = resp.json()["items"]
            assert items
            params = items[0]["param_values"]
            assert params[0]["param_value"] == "[REDACTED]"
            assert "admin-log-secret" not in str(resp.json())
        finally:
            with db_cursor() as (conn, cur):
                cur.execute(
                    "DELETE FROM signal_log_values WHERE signal_log_id = %s",
                    (signal_log_id,),
                )
                cur.execute("DELETE FROM signal_log WHERE id = %s", (signal_log_id,))
                cur.execute("DELETE FROM decision_log WHERE id = %s", (decision_id,))
                conn.commit()

    def test_create_signal_rejects_invalid_type(self, client):
        resp = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": f"invalid-type-{uuid.uuid4().hex[:8]}",
                "type": "not_a_real_type",
                "expression_body": "True",
            },
        )
        assert resp.status_code == 422

    def test_delete_current_checkpoint_returns_409(self, client):
        resp = client.delete(
            f"/ui/checkpoints/{SEED_ONBOARDING_CHECKPOINT}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert resp.status_code == 409

    def test_checkpoint_deactivate_and_reactivate_lifecycle(self, client):
        created = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": f"authoring_e2e_cp_{uuid.uuid4().hex[:8]}",
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        assert created.status_code == 200
        checkpoint_id = created.json()["id"]

        promoted = client.post(
            f"/ui/checkpoints/{checkpoint_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Authoring e2e promotion"},
        )
        assert promoted.status_code == 200

        deactivated = client.post(
            f"/ui/checkpoints/{checkpoint_id}/deactivate",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Authoring e2e deactivate"},
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["action"] == "deactivated"

        detail = client.get(
            f"/ui/checkpoints/{checkpoint_id}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert detail["is_current_version"] is False
        assert detail["name_has_current_version"] is False

        runtime = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={"checkpoint_name": detail["name"]},
        )
        assert runtime.status_code == 404

        reactivated = client.post(
            f"/ui/checkpoints/{checkpoint_id}/reactivate",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Authoring e2e reactivate"},
        )
        assert reactivated.status_code == 200
        assert reactivated.json()["action"] == "reactivated"
        after_reactivate = client.get(
            f"/ui/checkpoints/{checkpoint_id}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert after_reactivate["name_has_current_version"] is True

        audit = client.get(
            f"/ui/promotion_audit?tenant_id={SAMPLE_TENANT}&q={detail['name']}&page=1&size=10",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()["items"]
        actions = {row["action"] for row in audit}
        assert {"promote", "deactivate", "reactivate"}.issubset(actions)

    def test_checkpoint_reactivate_rejects_when_another_version_is_current(self, client):
        checkpoint_name = f"reactivate-current-guard-{uuid.uuid4().hex[:8]}"
        first = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": checkpoint_name,
                "type": "onboarding",
                "dsl_expression": "True",
            },
        )
        assert first.status_code == 200
        first_id = first.json()["id"]
        assert client.post(
            f"/ui/checkpoints/{first_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Promote first version"},
        ).status_code == 200

        second = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": checkpoint_name,
                "type": "onboarding",
                "dsl_expression": "False",
            },
        )
        assert second.status_code == 200
        second_id = second.json()["id"]
        assert client.post(
            f"/ui/checkpoints/{second_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Promote second version"},
        ).status_code == 200

        stale_detail = client.get(
            f"/ui/checkpoints/{first_id}",
            headers=auth_header(TEST_ADMIN_TOKEN),
        ).json()
        assert stale_detail["is_current_version"] is False
        assert stale_detail["name_has_current_version"] is True

        reactivate = client.post(
            f"/ui/checkpoints/{first_id}/reactivate",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Should require promote"},
        )
        assert reactivate.status_code == 409

    def test_authoring_expression_signal_checkpoint_and_test_lab(self, client):
        signal_name = f"authoring_e2e_signal_{uuid.uuid4().hex[:8]}"
        signal = client.post(
            "/ui/signals",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": signal_name,
                "type": "expression",
                "expression_body": "request_score > 10",
                "cost": 0,
            },
        )
        assert signal.status_code == 200
        signal_id = signal.json()["id"]

        promoted_signal = client.post(
            f"/ui/signals/{signal_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Authoring e2e signal promotion"},
        )
        assert promoted_signal.status_code == 200

        checkpoint_name = f"authoring_e2e_cp_{uuid.uuid4().hex[:8]}"
        checkpoint = client.post(
            "/ui/checkpoints",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "name": checkpoint_name,
                "type": "onboarding",
                "dsl_expression": signal_name,
                "signals": [signal_id],
            },
        )
        assert checkpoint.status_code == 200
        checkpoint_id = checkpoint.json()["id"]

        promoted_cp = client.post(
            f"/ui/checkpoints/{checkpoint_id}/make_current",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={"promotionReason": "Authoring e2e checkpoint promotion"},
        )
        assert promoted_cp.status_code == 200

        lab = client.post(
            "/ui/test_decisions",
            headers=auth_header(TEST_ADMIN_TOKEN),
            json={
                "tenant_id": SAMPLE_TENANT,
                "checkpoint_name": checkpoint_name,
                "checkpoint_id": checkpoint_id,
                "applicant_id": "authoring-e2e-applicant",
                "parameters": {"request_score": 12},
            },
        )
        assert lab.status_code == 200
        assert lab.json()["signal_results"][signal_name] is True

        runtime = client.post(
            "/decisions",
            headers=auth_header(TEST_SAMPLE_TOKEN),
            json={
                "checkpoint_name": checkpoint_name,
                "applicant_id": "authoring-e2e-runtime",
                "parameters": {"request_score": 12},
            },
        )
        assert runtime.status_code == 200
        assert runtime.json()["signal_results"][signal_name] is True

    def test_pagination_size_is_bounded(self, client):
        resp = client.get(
            f"/ui/checkpoints?tenant_id={SAMPLE_TENANT}&page=1&size=500",
            headers=auth_header(TEST_ADMIN_TOKEN),
        )
        assert resp.status_code == 200
        assert resp.json()["size"] == 100
