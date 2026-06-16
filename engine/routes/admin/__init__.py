from fastapi import APIRouter

from . import (
    associations,
    audit,
    checkpoints,
    dsl,
    lifecycle,
    search,
    signals,
    tenants,
    testing,
    variable_values,
)

router = APIRouter(tags=["admin"])

router.include_router(testing.router)
router.include_router(tenants.router)
router.include_router(checkpoints.router)
router.include_router(signals.router)
router.include_router(variable_values.router)
router.include_router(associations.router)
router.include_router(search.router)
router.include_router(audit.router)
router.include_router(dsl.router)
router.include_router(lifecycle.router)
