"""Shared helpers for admin routes — re-exported from services.admin.common."""

from ...services.admin.common import (  # noqa: F401
    GENERIC_ADMIN_ERROR,
    admin_signal_item_from_row,
    admin_signal_item_from_row as _admin_signal_item_from_row,
    assert_checkpoint_tenant,
    assert_checkpoint_tenant as _assert_checkpoint_tenant,
    checkpoint_item_from_row,
    collect_all_pages,
    collect_all_pages as _collect_all_pages,
    get_signal_tenant_id,
    get_signal_tenant_id as _get_signal_tenant_id,
    promotion_audit_row_to_item,
    promotion_audit_row_to_item as _promotion_audit_row_to_item,
    raise_admin_error,
    resolve_signal_bearer_token,
    resolve_signal_bearer_token as _resolve_signal_bearer_token,
    validate_signal_templates,
    validate_signal_templates as _validate_signal_templates,
)
