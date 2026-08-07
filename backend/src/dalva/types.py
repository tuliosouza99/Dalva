from collections.abc import Mapping
from typing import TypeAlias, TypedDict, Union

SingleElement: TypeAlias = str | bool | int | float | None
ConfigValue: TypeAlias = SingleElement | list
OutputDict: TypeAlias = dict[str, SingleElement]
ConfigOutputDict: TypeAlias = dict[str, ConfigValue]

InputValue: TypeAlias = SingleElement | list | dict

InputDict: TypeAlias = Mapping[
    str, Union[SingleElement, "list[SingleElement | InputDict]", "InputDict"]
]

TableRowValue: TypeAlias = Union[
    str, bool, int, float, None, "list[TableRowValue]", "dict[str, TableRowValue]"
]


class Metric(TypedDict):
    key: str
    value: int | float | str | bool | None
    step: int | None
