from fastapi import Depends, Request

from ..auth import reject_supplied_tenant


async def reject_runtime_tenant_query(request: Request) -> None:
    query = request.query_params
    reject_supplied_tenant(
        has_tenant_id="tenant_id" in query,
        has_tenant_name="tenant_name" in query,
    )
