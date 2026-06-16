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
    },
}


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
        cur.execute(
            """
            DELETE FROM signal_current_version
             WHERE tenant_id = %s
               AND name = 'inactive_demo'
            """,
            (SAMPLE_TENANT,),
        )
        conn.commit()
