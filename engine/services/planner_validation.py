"""Validated enums for execution planner policy fields."""

from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

Criticality = Literal["required", "preferred", "optional"]
ExecutionRole = Literal["referenced_policy", "always_run_audit", "manual_test_only"]
BillableEvent = Literal["success", "attempt", "never"]
CacheScope = Literal[
    "tenant_applicant_signal",
    "tenant_case_signal",
    "tenant_checkpoint_applicant",
    "tenant_signal",
]
BudgetExceededPolicy = Literal["refer", "fail_closed"]
VendorFailurePolicy = Literal["refer", "fail_closed", "error"]

CRITICALITIES = frozenset({"required", "preferred", "optional"})
EXECUTION_ROLES = frozenset({"referenced_policy", "always_run_audit", "manual_test_only"})
BILLABLE_EVENTS = frozenset({"success", "attempt", "never"})
CACHE_SCOPES = frozenset(
    {"tenant_applicant_signal", "tenant_case_signal", "tenant_checkpoint_applicant", "tenant_signal"}
)
BUDGET_EXCEEDED_POLICIES = frozenset({"refer", "fail_closed"})
VENDOR_FAILURE_POLICIES = frozenset({"refer", "fail_closed", "error"})


def _validate(value: str, allowed: frozenset[str], field: str) -> str:
    if value not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"{field} must be one of: {', '.join(sorted(allowed))}.",
        )
    return value


def validate_criticality(value: str) -> str:
    return _validate(value, CRITICALITIES, "criticality")


def validate_execution_role(value: str) -> str:
    return _validate(value, EXECUTION_ROLES, "execution_role")


def validate_billable_event(value: str) -> str:
    return _validate(value, BILLABLE_EVENTS, "billable_event")


def validate_cache_scope(value: str) -> str:
    return _validate(value, CACHE_SCOPES, "cache_scope")


def validate_budget_exceeded_policy(value: str) -> str:
    return _validate(value, BUDGET_EXCEEDED_POLICIES, "budget_exceeded_policy")


def validate_vendor_failure_policy(value: str) -> str:
    return _validate(value, VENDOR_FAILURE_POLICIES, "vendor_failure_policy")
