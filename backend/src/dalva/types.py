from typing import Mapping, TypeAlias, TypeVar, Union

SingleElement: TypeAlias = Union[str, bool, int, float, None]
ConfigValue: TypeAlias = Union[SingleElement, list]
OutputDict: TypeAlias = dict[str, SingleElement]
ConfigOutputDict: TypeAlias = dict[str, ConfigValue]

InputValue: TypeAlias = Union[SingleElement, list, dict]

InputDict: TypeAlias = Mapping[
    str, Union[SingleElement, "list[SingleElement | InputDict]", "InputDict"]
]

TableRowValue: TypeAlias = Union[
    str, bool, int, float, None, "list[TableRowValue]", "dict[str, TableRowValue]"
]

_T = TypeVar("_T")
