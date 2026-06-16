from fastapi import APIRouter, Depends, HTTPException

from ...auth import AuthContext, require_permission
from ...db import get_db_connection
from ...models import PromotionRequest
from ...services.admin_responses import admin_mutation
from ...services.dsl import validate_expression
from ...services.promotion_audit import (
    normalize_promotion_reason,
    record_promotion_audit,
)
from ...services.resource_lifecycle import (
    deactivate_checkpoint,
    deactivate_signal,
    normalize_lifecycle_reason,
    reactivate_checkpoint,
    reactivate_signal,
)
from ...types import UuidStr
from ._shared import raise_admin_error

router = APIRouter()

@router.post("/ui/checkpoints/{checkpoint_id}/make_current")
def make_checkpoint_current(
    checkpoint_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:promote")),
):
    """Make a checkpoint the current version for its tenant and name."""
    promotion_reason = normalize_promotion_reason(payload.promotion_reason)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # First get the checkpoint details
        cur.execute("""
            SELECT tenant_id, name, dsl_expression
            FROM checkpoints
            WHERE id = %s
        """, (checkpoint_id,))
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

        # Update or insert into checkpoint_current_version
        cur.execute("""
            INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name) 
            DO UPDATE SET 
                checkpoint_id = EXCLUDED.checkpoint_id,
                updated_at = NOW()
        """, (tenant_id, checkpoint_name, checkpoint_id))

        record_promotion_audit(
            cur,
            tenant_id=str(tenant_id),
            resource_type="checkpoint",
            resource_id=checkpoint_id,
            resource_name=checkpoint_name,
            actor_id=auth.actor_id,
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


@router.post("/ui/signals/{signal_id}/make_current")
def make_signal_current(
    signal_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:promote")),
):
    """Set a signal as the current version for its tenant and name."""
    promotion_reason = normalize_promotion_reason(payload.promotion_reason)
    conn = get_db_connection()
    try:
        # Get the tenant_id and name for this signal
        cur = conn.cursor()
        cur.execute(
            "SELECT tenant_id, name FROM signals WHERE id = %s",
            (signal_id,)
        )
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        tenant_id, signal_name = result

        # Update or insert into signal_current_version
        cur.execute("""
            INSERT INTO signal_current_version (tenant_id, name, signal_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, name)
            DO UPDATE SET signal_id = EXCLUDED.signal_id,
                updated_at = NOW()
        """, (tenant_id, signal_name, signal_id))

        record_promotion_audit(
            cur,
            tenant_id=str(tenant_id),
            resource_type="signal",
            resource_id=signal_id,
            resource_name=signal_name,
            actor_id=auth.actor_id,
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


@router.post("/ui/checkpoints/{checkpoint_id}/deactivate")
def deactivate_checkpoint_version(
    checkpoint_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:deactivate")),
):
    reason = normalize_lifecycle_reason(payload.promotion_reason)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        deactivate_checkpoint(
            cur,
            checkpoint_id=checkpoint_id,
            actor_id=auth.actor_id,
            promotion_reason=reason,
        )
        conn.commit()
        return admin_mutation("deactivated", checkpoint_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="deactivate_checkpoint failed")
    finally:
        cur.close()
        conn.close()


@router.post("/ui/checkpoints/{checkpoint_id}/reactivate")
def reactivate_checkpoint_version(
    checkpoint_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:deactivate")),
):
    reason = normalize_lifecycle_reason(payload.promotion_reason)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        reactivate_checkpoint(
            cur,
            checkpoint_id=checkpoint_id,
            actor_id=auth.actor_id,
            promotion_reason=reason,
        )
        conn.commit()
        return admin_mutation("reactivated", checkpoint_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="reactivate_checkpoint failed")
    finally:
        cur.close()
        conn.close()


@router.post("/ui/signals/{signal_id}/deactivate")
def deactivate_signal_version(
    signal_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:deactivate")),
):
    reason = normalize_lifecycle_reason(payload.promotion_reason)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        deactivate_signal(
            cur,
            signal_id=signal_id,
            actor_id=auth.actor_id,
            promotion_reason=reason,
        )
        conn.commit()
        return admin_mutation("deactivated", signal_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="deactivate_signal failed")
    finally:
        cur.close()
        conn.close()


@router.post("/ui/signals/{signal_id}/reactivate")
def reactivate_signal_version(
    signal_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:deactivate")),
):
    reason = normalize_lifecycle_reason(payload.promotion_reason)
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        reactivate_signal(
            cur,
            signal_id=signal_id,
            actor_id=auth.actor_id,
            promotion_reason=reason,
        )
        conn.commit()
        return admin_mutation("reactivated", signal_id)
    except Exception as e:
        conn.rollback()
        raise_admin_error(e, context="reactivate_signal failed")
    finally:
        cur.close()
        conn.close()
