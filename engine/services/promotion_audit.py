"""Persist and validate governed version promotions."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

ResourceType = Literal["checkpoint", "signal"]
PromotionAction = Literal["promote", "deactivate", "reactivate"]


def normalize_promotion_reason(reason: str | None) -> str:
    if reason is None:
        raise HTTPException(
            status_code=422,
            detail="promotionReason is required for promotion.",
        )
    trimmed = reason.strip()
    if len(trimmed) < 3:
        raise HTTPException(
            status_code=422,
            detail="promotionReason must be at least 3 characters.",
        )
    if len(trimmed) > 2000:
        raise HTTPException(
            status_code=422,
            detail="promotionReason must be at most 2000 characters.",
        )
    return trimmed


def record_promotion_audit(
    cur,
    *,
    tenant_id: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    actor_id: str,
    promotion_reason: str,
    action: str = "promote",
    source: str = "make_current",
) -> None:
    cur.execute(
        """
        INSERT INTO promotion_audit (
            tenant_id, resource_type, resource_id, resource_name,
            actor_id, promotion_reason, action, source
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            tenant_id,
            resource_type,
            resource_id,
            resource_name,
            actor_id,
            promotion_reason,
            action,
            source,
        ),
    )
