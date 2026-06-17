from fastapi import APIRouter, Depends

from ...auth import AuthContext, require_permission
from ...models import PromotionRequest
from ...services.admin.common import (
    assert_checkpoint_resource_access,
    assert_signal_resource_access,
    raise_admin_error,
)
from ...services.admin.promotion import make_checkpoint_current, make_signal_current
from ...services.admin_responses import admin_mutation
from ...services.promotion_audit import normalize_promotion_reason
from ...services.resource_lifecycle import (
    deactivate_checkpoint,
    deactivate_signal,
    normalize_lifecycle_reason,
    reactivate_checkpoint,
    reactivate_signal,
)
from ...db import get_db_connection
from ...types import UuidStr

router = APIRouter()


@router.post("/ui/checkpoints/{checkpoint_id}/make_current")
def make_checkpoint_current_route(
    checkpoint_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:promote")),
):
    assert_checkpoint_resource_access(auth, checkpoint_id)
    promotion_reason = normalize_promotion_reason(payload.promotion_reason)
    return make_checkpoint_current(
        checkpoint_id,
        promotion_reason=promotion_reason,
        actor_id=auth.actor_id,
    )


@router.post("/ui/signals/{signal_id}/make_current")
def make_signal_current_route(
    signal_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:promote")),
):
    assert_signal_resource_access(auth, signal_id)
    promotion_reason = normalize_promotion_reason(payload.promotion_reason)
    return make_signal_current(
        signal_id,
        promotion_reason=promotion_reason,
        actor_id=auth.actor_id,
    )


@router.post("/ui/checkpoints/{checkpoint_id}/deactivate")
def deactivate_checkpoint_version(
    checkpoint_id: UuidStr,
    payload: PromotionRequest,
    auth: AuthContext = Depends(require_permission("config:deactivate")),
):
    assert_checkpoint_resource_access(auth, checkpoint_id)
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
    assert_checkpoint_resource_access(auth, checkpoint_id)
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
    assert_signal_resource_access(auth, signal_id)
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
    assert_signal_resource_access(auth, signal_id)
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
