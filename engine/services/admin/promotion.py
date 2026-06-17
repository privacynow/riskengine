"""Checkpoint and signal promotion (make current) service logic."""

from fastapi import HTTPException

from ...db import get_db_connection
from ...services.admin_responses import admin_mutation
from ...services.dsl import validate_expression
from ...services.promotion_audit import normalize_promotion_reason, record_promotion_audit
from ...services.admin.common import raise_admin_error
from ...types import UuidStr


def make_checkpoint_current(
    checkpoint_id: UuidStr,
    *,
    promotion_reason: str,
    actor_id: str,
) -> dict:
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT tenant_id, name, dsl_expression
              FROM checkpoints
             WHERE id = %s
            """,
            (checkpoint_id,),
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Checkpoint not found")

        tenant_id, checkpoint_name, dsl_expression = result

        cur.execute(
            """
            SELECT s.name
              FROM checkpoint_signals cs
              JOIN signals s ON s.id = cs.signal_id
             WHERE cs.checkpoint_id = %s
            """,
            (checkpoint_id,),
        )
        signal_names = [row[0] for row in cur.fetchall()]
        dsl_result = validate_expression(dsl_expression, signal_names, "strict")
        if not dsl_result.ok:
            raise HTTPException(status_code=422, detail="; ".join(dsl_result.errors))

        cur.execute(
            """
            INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET
                checkpoint_id = EXCLUDED.checkpoint_id,
                updated_at = NOW()
            """,
            (tenant_id, checkpoint_name, checkpoint_id),
        )

        record_promotion_audit(
            cur,
            tenant_id=str(tenant_id),
            resource_type="checkpoint",
            resource_id=checkpoint_id,
            resource_name=checkpoint_name,
            actor_id=actor_id,
            promotion_reason=promotion_reason,
            action="promote",
        )

        conn.commit()
        return admin_mutation("promoted", checkpoint_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="make_checkpoint_current failed")
    finally:
        cur.close()
        conn.close()


def make_signal_current(
    signal_id: UuidStr,
    *,
    promotion_reason: str,
    actor_id: str,
) -> dict:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, name FROM signals WHERE id = %s",
            (signal_id,),
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Signal not found")

        tenant_id, signal_name = result

        cur.execute(
            """
            INSERT INTO signal_current_version (tenant_id, name, signal_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET signal_id = EXCLUDED.signal_id,
                updated_at = NOW()
            """,
            (tenant_id, signal_name, signal_id),
        )

        record_promotion_audit(
            cur,
            tenant_id=str(tenant_id),
            resource_type="signal",
            resource_id=signal_id,
            resource_name=signal_name,
            actor_id=actor_id,
            promotion_reason=promotion_reason,
            action="promote",
        )

        conn.commit()
        return admin_mutation("promoted", signal_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="make_signal_current failed")
    finally:
        cur.close()
        conn.close()
