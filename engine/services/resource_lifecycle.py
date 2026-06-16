"""Audited checkpoint/signal lifecycle actions."""

from __future__ import annotations

from fastapi import HTTPException

from .dsl import validate_expression
from .promotion_audit import normalize_promotion_reason, record_promotion_audit


def _checkpoint_row(cur, checkpoint_id: str) -> tuple[str, str, str]:
    cur.execute(
        "SELECT tenant_id, name, dsl_expression FROM checkpoints WHERE id = %s",
        (checkpoint_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Checkpoint not found.")
    return str(row[0]), row[1], row[2]


def _signal_row(cur, signal_id: str) -> tuple[str, str]:
    cur.execute(
        "SELECT tenant_id, name FROM signals WHERE id = %s",
        (signal_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found.")
    return str(row[0]), row[1]


def _current_checkpoint_id(cur, tenant_id: str, name: str) -> str | None:
    cur.execute(
        """
        SELECT checkpoint_id
          FROM checkpoint_current_version
         WHERE tenant_id = %s AND name = %s
        """,
        (tenant_id, name),
    )
    row = cur.fetchone()
    return str(row[0]) if row else None


def _current_signal_id(cur, tenant_id: str, name: str) -> str | None:
    cur.execute(
        """
        SELECT signal_id
          FROM signal_current_version
         WHERE tenant_id = %s AND name = %s
        """,
        (tenant_id, name),
    )
    row = cur.fetchone()
    return str(row[0]) if row else None


def _checkpoint_signal_names(cur, checkpoint_id: str) -> list[str]:
    cur.execute(
        """
        SELECT DISTINCT s.name
          FROM checkpoint_signals cs
          JOIN signals s ON s.id = cs.signal_id
         WHERE cs.checkpoint_id = %s
        """,
        (checkpoint_id,),
    )
    return [row[0] for row in cur.fetchall()]


def deactivate_checkpoint(
    cur,
    *,
    checkpoint_id: str,
    actor_id: str,
    promotion_reason: str,
) -> None:
    tenant_id, name, _dsl_expression = _checkpoint_row(cur, checkpoint_id)
    current_id = _current_checkpoint_id(cur, tenant_id, name)
    if current_id != checkpoint_id:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint version is not current; cannot deactivate.",
        )
    cur.execute(
        """
        DELETE FROM checkpoint_current_version
         WHERE tenant_id = %s AND name = %s
        """,
        (tenant_id, name),
    )
    record_promotion_audit(
        cur,
        tenant_id=tenant_id,
        resource_type="checkpoint",
        resource_id=checkpoint_id,
        resource_name=name,
        actor_id=actor_id,
        promotion_reason=promotion_reason,
        action="deactivate",
        source="deactivate",
    )


def reactivate_checkpoint(
    cur,
    *,
    checkpoint_id: str,
    actor_id: str,
    promotion_reason: str,
) -> None:
    tenant_id, name, dsl_expression = _checkpoint_row(cur, checkpoint_id)
    current_id = _current_checkpoint_id(cur, tenant_id, name)
    if current_id == checkpoint_id:
        raise HTTPException(
            status_code=409,
            detail="Checkpoint version is already current.",
        )
    if current_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Another checkpoint version is current; use promote instead.",
        )
    signal_names = _checkpoint_signal_names(cur, checkpoint_id)
    dsl_result = validate_expression(dsl_expression, signal_names, "strict")
    if not dsl_result.ok:
        raise HTTPException(status_code=422, detail="; ".join(dsl_result.errors))
    cur.execute(
        """
        INSERT INTO checkpoint_current_version (tenant_id, name, checkpoint_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (tenant_id, name)
        DO UPDATE SET checkpoint_id = EXCLUDED.checkpoint_id,
                      updated_at = NOW()
        """,
        (tenant_id, name, checkpoint_id),
    )
    record_promotion_audit(
        cur,
        tenant_id=tenant_id,
        resource_type="checkpoint",
        resource_id=checkpoint_id,
        resource_name=name,
        actor_id=actor_id,
        promotion_reason=promotion_reason,
        action="reactivate",
        source="reactivate",
    )


def deactivate_signal(
    cur,
    *,
    signal_id: str,
    actor_id: str,
    promotion_reason: str,
) -> None:
    tenant_id, name = _signal_row(cur, signal_id)
    current_id = _current_signal_id(cur, tenant_id, name)
    if current_id != signal_id:
        raise HTTPException(
            status_code=409,
            detail="Signal version is not current; cannot deactivate.",
        )
    cur.execute(
        """
        DELETE FROM signal_current_version
         WHERE tenant_id = %s AND name = %s
        """,
        (tenant_id, name),
    )
    record_promotion_audit(
        cur,
        tenant_id=tenant_id,
        resource_type="signal",
        resource_id=signal_id,
        resource_name=name,
        actor_id=actor_id,
        promotion_reason=promotion_reason,
        action="deactivate",
        source="deactivate",
    )


def reactivate_signal(
    cur,
    *,
    signal_id: str,
    actor_id: str,
    promotion_reason: str,
) -> None:
    tenant_id, name = _signal_row(cur, signal_id)
    current_id = _current_signal_id(cur, tenant_id, name)
    if current_id == signal_id:
        raise HTTPException(
            status_code=409,
            detail="Signal version is already current.",
        )
    if current_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Another signal version is current; use promote instead.",
        )
    cur.execute(
        """
        INSERT INTO signal_current_version (tenant_id, name, signal_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (tenant_id, name)
        DO UPDATE SET signal_id = EXCLUDED.signal_id,
                      updated_at = NOW()
        """,
        (tenant_id, name, signal_id),
    )
    record_promotion_audit(
        cur,
        tenant_id=tenant_id,
        resource_type="signal",
        resource_id=signal_id,
        resource_name=name,
        actor_id=actor_id,
        promotion_reason=promotion_reason,
        action="reactivate",
        source="reactivate",
    )


def assert_not_current_checkpoint(cur, checkpoint_id: str) -> None:
    cur.execute(
        """
        SELECT 1
          FROM checkpoint_current_version
         WHERE checkpoint_id = %s
        """,
        (checkpoint_id,),
    )
    if cur.fetchone():
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete the current checkpoint version. "
                "Deactivate or promote another version first."
            ),
        )


def assert_not_current_signal(cur, signal_id: str) -> None:
    cur.execute(
        """
        SELECT 1
          FROM signal_current_version
         WHERE signal_id = %s
        """,
        (signal_id,),
    )
    if cur.fetchone():
        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot delete the current signal version. "
                "Deactivate or promote another version first."
            ),
        )


def normalize_lifecycle_reason(reason: str | None) -> str:
    return normalize_promotion_reason(reason)
