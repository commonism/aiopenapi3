import enum
import typing
from typing import Union, Optional, Dict, Any

from pydantic import Field

from ..base import ObjectExtended, ParameterBase as _ParameterBase

from .example import Example
from .general import Reference
from .schemas import Schema

from ..v30.parameter import _ParameterCodec

if typing.TYPE_CHECKING:
    from .paths import MediaType


class ParameterBase(ObjectExtended, _ParameterBase):
    """
    A `Parameter Object`_ defines a single operation parameter.

    .. _Parameter Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#parameterObject
    """

    description: Optional[str] = Field(default=None)
    required: Optional[bool] = Field(default=None)
    deprecated: Optional[bool] = Field(default=None)
    allowEmptyValue: Optional[bool] = Field(default=None)

    style: Optional[str] = Field(default=None)
    explode: Optional[bool] = Field(default=None)
    allowReserved: Optional[bool] = Field(default=None)
    schema_: Optional[Schema] = Field(default=None, alias="schema")
    example: Optional[Any] = Field(default=None)
    examples: Dict[str, Union["Example", Reference]] = Field(default_factory=dict)

    content: Optional[Dict[str, "MediaType"]] = None


class _In(str, enum.Enum):
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"


class Parameter(ParameterBase, _ParameterCodec):
    name: str = Field()
    in_: _In = Field(alias="in")


class Header(ParameterBase, _ParameterCodec):
    """

    .. _HeaderObject: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#headerObject
    """

    def _codec(self):
        schema = self.schema_ or self.content.get("application/json").schema_
        return schema, "simple", False
