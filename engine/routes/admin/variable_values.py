from fastapi import APIRouter

from ...models import VariableValueCreateUpdate
from ...services.admin.variable_values import (
    create_variable_value,
    delete_variable_value,
    get_variable_value_item,
    list_signal_variable_values,
    update_variable_value,
)
from ...types import UuidStr
from ._deps import AdminRead, AdminWrite

router = APIRouter()


@router.post("/ui/variable_values", dependencies=[AdminWrite])
def create_variable_value_route(payload: VariableValueCreateUpdate):
    return create_variable_value(payload)


@router.get("/ui/signals/{signal_id}/variable_values", dependencies=[AdminRead])
def list_signal_variable_values_route(signal_id: UuidStr, page: int = 1, size: int = 10):
    return list_signal_variable_values(signal_id, page=page, size=size)


@router.get("/ui/variable_values/{variable_value_id}", dependencies=[AdminRead])
def get_variable_value_item_route(variable_value_id: UuidStr):
    return get_variable_value_item(variable_value_id)


@router.put("/ui/variable_values/{variable_value_id}", dependencies=[AdminWrite])
def update_variable_value_route(
    variable_value_id: UuidStr,
    payload: VariableValueCreateUpdate,
):
    return update_variable_value(variable_value_id, payload)


@router.delete("/ui/variable_values/{variable_value_id}", dependencies=[AdminWrite])
def delete_variable_value_route(variable_value_id: UuidStr):
    return delete_variable_value(variable_value_id)
