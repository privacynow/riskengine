"""Shared validated types for API models and path parameters."""

from __future__ import annotations

from typing import Annotated, Optional
from uuid import UUID

from pydantic import AfterValidator


def parse_uuid(value: object, *, field: str = "id") -> str:
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError(f"Invalid {field}.") from exc


def parse_optional_uuid(value: object, *, field: str = "id") -> Optional[str]:
    if value is None or value == "":
        return None
    return parse_uuid(value, field=field)


UuidStr = Annotated[str, AfterValidator(lambda value: parse_uuid(value))]
OptionalUuidStr = Annotated[
    Optional[str],
    AfterValidator(lambda value: parse_optional_uuid(value)),
]
