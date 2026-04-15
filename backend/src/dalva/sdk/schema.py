"""DalvaSchema — Pydantic-based table schema with type validation."""

from __future__ import annotations

import types
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

_UNION_TYPES = {Union}
try:
    _UNION_TYPES.add(types.UnionType)
except AttributeError:
    pass


_ALLOWED_SCALAR_TYPES = {int, float, str, bool, type(None)}
_ALLOWED_CONTAINER_TYPES = {list, dict}
_ALLOWED_TYPES = _ALLOWED_SCALAR_TYPES | _ALLOWED_CONTAINER_TYPES

_TYPE_MAP = {
    int: "int",
    float: "float",
    str: "str",
    bool: "bool",
    type(None): "null",
    list: "list",
    dict: "dict",
}


def _unwrap_annotation(annotation: Any) -> list[type]:
    if annotation is type(None):
        return [type(None)]
    origin = get_origin(annotation)
    if origin in _UNION_TYPES:
        args = get_args(annotation)
        result = []
        for a in args:
            result.extend(_unwrap_annotation(a))
        return result
    if origin is not None:
        return [origin]
    if isinstance(annotation, type):
        return [annotation]
    return [annotation]


def _extract_base_type(annotation: Any) -> type | None:
    unwrapped = _unwrap_annotation(annotation)
    non_none = [t for t in unwrapped if t is not type(None)]
    if len(non_none) == 0:
        return None
    if len(non_none) == 1:
        t = non_none[0]
        if t in _ALLOWED_TYPES:
            return t
        return None
    return None


def _validate_annotation(annotation: Any) -> None:
    unwrapped = _unwrap_annotation(annotation)
    for t in unwrapped:
        if t is type(None):
            continue
        if t in _ALLOWED_TYPES:
            continue
        raise TypeError(
            f"Type {t} is unsupported. "
            f"Allowed types: int, str, bool, float, None, list, dict"
        )


class DalvaSchema(BaseModel):
    """Base class for Dalva table schemas.

    Subclass this with fields of type: int, str, bool, float, None, list, dict.
    Optional[X] is supported (maps to type X, nullable).

    Example:
        class MySchema(DalvaSchema):
            name: str
            score: float
            tags: list | None = None
    """

    model_config = {"extra": "forbid"}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        for field_name, field_info in cls.model_fields.items():
            _validate_annotation(field_info.annotation)

    @classmethod
    def to_column_schema(cls) -> list[dict[str, str]]:
        """Return column schema as [{"name": ..., "type": ...}, ...]."""
        cols = []
        for field_name, field_info in cls.model_fields.items():
            base = _extract_base_type(field_info.annotation)
            if base is None:
                continue
            cols.append({"name": field_name, "type": _TYPE_MAP[base]})
        return cols

    @classmethod
    def validate_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        """Validate a row dict against this schema. Returns cleaned dict."""
        return cls(**row).model_dump()
