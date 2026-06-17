"""Restore integration-test seed pointers after mutating tests."""

from __future__ import annotations

from engine.db import db_cursor

SAMPLE_TENANT = "11111111-1111-1111-1111-111111111111"
OTHER_TENANT = "99999999-9999-9999-9999-999999999999"

SEED_CHECKPOINT_CURRENT: dict[str, dict[str, str]] = {
    SAMPLE_TENANT: {
        "Onboarding": "22222222-2222-2222-2222-222222222201",
        "Compliance": "22222222-2222-2222-2222-222222222202",
        "Underwriting": "22222222-2222-2222-2222-222222222203",
        "Funds Disbursement": "22222222-2222-2222-2222-222222222204",
        "Servicing": "22222222-2222-2222-2222-222222222205",
    },
    OTHER_TENANT: {
        "Onboarding": "88888888-8888-8888-8888-888888888801",
    },
}

SEED_SIGNAL_CURRENT: dict[str, dict[str, str]] = {
    SAMPLE_TENANT: {
        "age_check": "33333333-3333-3333-3333-333333333301",
        "blocklist_check": "33333333-3333-3333-3333-333333333302",
        "previous_delinquency": "33333333-3333-3333-3333-333333333303",
        "active_loan": "33333333-3333-3333-3333-333333333304",
        "doc_verification": "33333333-3333-3333-3333-333333333305",
        "sanction_screening": "33333333-3333-3333-3333-333333333306",
        "kyc_score": "33333333-3333-3333-3333-333333333307",
        "credit_score": "33333333-3333-3333-3333-333333333308",
        "income_verification": "33333333-3333-3333-3333-333333333309",
        "loan_amount_check": "33333333-3333-3333-3333-333333333310",
        "disbursement_limit_check": "33333333-3333-3333-3333-333333333311",
        "delinquent_days": "33333333-3333-3333-3333-333333333312",
        "delinquent_severity": "33333333-3333-3333-3333-333333333313",
        "requested_loan_amount": "33333333-3333-3333-3333-333333333314",
        "kyc_pass": "33333333-3333-3333-3333-333333333315",
        "credit_pass": "33333333-3333-3333-3333-333333333316",
    },
}


SEED_VARIABLE_VALUES: dict[str, tuple[str, str]] = {
    "33333333-3333-3333-3333-333333333301": ("age_check", "True"),
    "33333333-3333-3333-3333-333333333302": ("blocklist_check", "False"),
    "33333333-3333-3333-3333-333333333303": ("previous_delinquency", "0"),
    "33333333-3333-3333-3333-333333333304": ("active_loan", "True"),
    "33333333-3333-3333-3333-333333333314": ("requested_loan_amount", "35000"),
}


def _restore_seed_variable_values(cur) -> None:
    for signal_id, (name, value) in SEED_VARIABLE_VALUES.items():
        cur.execute(
            """
            INSERT INTO signal_variable_values (id, signal_id, name, value)
            SELECT uuid_generate_v4(), %s, %s, %s
             WHERE NOT EXISTS (
                    SELECT 1 FROM signal_variable_values
                     WHERE signal_id = %s AND name = %s
               )
            """,
            (signal_id, name, value, signal_id, name),
        )
        cur.execute(
            """
            UPDATE signal_variable_values
               SET value = %s, updated_at = NOW()
             WHERE signal_id = %s AND name = %s
            """,
            (value, signal_id, name),
        )


def _upsert_current_versions(
    cur,
    table: str,
    id_column: str,
    versions: dict[str, dict[str, str]],
) -> None:
    for tenant_id, names in versions.items():
        for name, resource_id in names.items():
            cur.execute(
                f"""
                INSERT INTO {table} (tenant_id, name, {id_column})
                VALUES (%s, %s, %s)
                ON CONFLICT (tenant_id, name) DO UPDATE
                   SET {id_column} = EXCLUDED.{id_column},
                       updated_at = NOW()
                """,
                (tenant_id, name, resource_id),
            )


def reset_integration_seed_state() -> None:
    """Reset current-version pointers used by auth, tenancy, and admin integration tests."""
    with db_cursor() as (conn, cur):
        _upsert_current_versions(
            cur, "checkpoint_current_version", "checkpoint_id", SEED_CHECKPOINT_CURRENT
        )
        _upsert_current_versions(
            cur, "signal_current_version", "signal_id", SEED_SIGNAL_CURRENT
        )
        _restore_seed_variable_values(cur)
        cur.execute(
            """
            DELETE FROM signal_current_version
             WHERE tenant_id = %s
               AND name = 'inactive_demo'
            """,
            (SAMPLE_TENANT,),
        )
        _cleanup_test_artifacts(cur, SAMPLE_TENANT)
        _cleanup_test_artifacts(cur, OTHER_TENANT)
        conn.commit()


_TEST_CHECKPOINT_NAME_PATTERNS = (
    "dup-assoc-guard-%",
    "cross-tenant-link-%",
    "promotion-%",
    "permission-boundary-%",
    "mutation-envelope-test",
    "cross-tenant-assoc-test",
    "invalid-%",
    "authoring_e2e_%",
    "reactivate-current-guard-%",
    "admin-version-fork-test",
    "assoc-create-test",
)

_TEST_SIGNAL_NAME_PATTERNS = (
    "foreign_%",
    "authoring_e2e_%",
)


_TEST_TENANT_NAME_PATTERNS = (
    "tenant-admin-created",
    "COPY TEST TENANT",
    "STALE LINK COPY TEST",
)


def _delete_checkpoints_by_name_pattern(cur, tenant_id: str, pattern: str) -> None:
    cur.execute(
        """
        DELETE FROM checkpoint_current_version
         WHERE tenant_id = %s
           AND name IN (
                SELECT name FROM checkpoints
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signal_cached_values
         WHERE checkpoint_id IN (
                SELECT id FROM checkpoints
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM promotion_audit
         WHERE resource_id IN (
                SELECT id FROM checkpoints
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM checkpoint_signals
         WHERE checkpoint_id IN (
                SELECT id FROM checkpoints
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signal_log_values
         WHERE signal_log_id IN (
                SELECT sl.id
                  FROM signal_log sl
                  JOIN decision_log dl ON dl.id = sl.decision_log_id
                  JOIN checkpoints c ON c.id = dl.checkpoint_id
                 WHERE c.tenant_id = %s AND c.name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signal_log
         WHERE decision_log_id IN (
                SELECT dl.id
                  FROM decision_log dl
                  JOIN checkpoints c ON c.id = dl.checkpoint_id
                 WHERE c.tenant_id = %s AND c.name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM decision_log
         WHERE checkpoint_id IN (
                SELECT id FROM checkpoints
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM checkpoints
         WHERE tenant_id = %s AND name LIKE %s
        """,
        (tenant_id, pattern),
    )


def _delete_signals_by_name_pattern(cur, tenant_id: str, pattern: str) -> None:
    cur.execute(
        """
        DELETE FROM signal_current_version
         WHERE tenant_id = %s
           AND name IN (
                SELECT name FROM signals
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM checkpoint_signals
         WHERE signal_id IN (
                SELECT id FROM signals
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signal_log_values
         WHERE signal_log_id IN (
                SELECT sl.id
                  FROM signal_log sl
                  JOIN signals s ON s.id = sl.signal_id
                 WHERE s.tenant_id = %s AND s.name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signal_log
         WHERE signal_id IN (
                SELECT id FROM signals
                 WHERE tenant_id = %s AND name LIKE %s
           )
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signal_variable_values
         WHERE signal_id IN (SELECT id FROM signals WHERE tenant_id = %s AND name LIKE %s)
        """,
        (tenant_id, pattern),
    )
    cur.execute(
        """
        DELETE FROM signals
         WHERE tenant_id = %s AND name LIKE %s
        """,
        (tenant_id, pattern),
    )


def _delete_test_tenant_by_name(cur, name: str) -> None:
    cur.execute("SELECT id FROM tenants WHERE name = %s", (name,))
    row = cur.fetchone()
    if not row:
        return
    tenant_id = str(row[0])
    if tenant_id in (SAMPLE_TENANT, OTHER_TENANT):
        return
    cur.execute("DELETE FROM checkpoint_current_version WHERE tenant_id = %s", (tenant_id,))
    cur.execute("DELETE FROM signal_current_version WHERE tenant_id = %s", (tenant_id,))
    cur.execute(
        """
        DELETE FROM signal_cached_values
         WHERE checkpoint_id IN (SELECT id FROM checkpoints WHERE tenant_id = %s)
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM promotion_audit
         WHERE tenant_id = %s
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM checkpoint_signals
         WHERE checkpoint_id IN (SELECT id FROM checkpoints WHERE tenant_id = %s)
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM signal_log_values
         WHERE signal_log_id IN (
                SELECT sl.id
                  FROM signal_log sl
                  JOIN decision_log dl ON dl.id = sl.decision_log_id
                 WHERE dl.checkpoint_id IN (
                        SELECT id FROM checkpoints WHERE tenant_id = %s
                   )
           )
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM signal_log
         WHERE decision_log_id IN (
                SELECT id FROM decision_log
                 WHERE checkpoint_id IN (
                        SELECT id FROM checkpoints WHERE tenant_id = %s
                   )
           )
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM decision_log
         WHERE checkpoint_id IN (SELECT id FROM checkpoints WHERE tenant_id = %s)
        """,
        (tenant_id,),
    )
    cur.execute("DELETE FROM checkpoints WHERE tenant_id = %s", (tenant_id,))
    cur.execute(
        """
        DELETE FROM signal_variable_values
         WHERE signal_id IN (SELECT id FROM signals WHERE tenant_id = %s)
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM signal_log_values
         WHERE signal_log_id IN (
                SELECT sl.id
                  FROM signal_log sl
                  JOIN signals s ON s.id = sl.signal_id
                 WHERE s.tenant_id = %s
           )
        """,
        (tenant_id,),
    )
    cur.execute(
        """
        DELETE FROM signal_log
         WHERE signal_id IN (SELECT id FROM signals WHERE tenant_id = %s)
        """,
        (tenant_id,),
    )
    cur.execute("DELETE FROM signals WHERE tenant_id = %s", (tenant_id,))
    cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))


def _cleanup_test_artifacts(cur, tenant_id: str) -> None:
    for pattern in _TEST_SIGNAL_NAME_PATTERNS:
        _delete_signals_by_name_pattern(cur, tenant_id, pattern)
    for pattern in _TEST_CHECKPOINT_NAME_PATTERNS:
        _delete_checkpoints_by_name_pattern(cur, tenant_id, pattern)
    for name in _TEST_TENANT_NAME_PATTERNS:
        _delete_test_tenant_by_name(cur, name)
