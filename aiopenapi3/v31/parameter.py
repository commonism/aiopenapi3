import enum
from typing import Union, Optional, Dict, Any

from pydantic import Field

from ..base import ObjectExtended

from .example import Example
from .general import Reference
from .schemas import Schema

from ..v30.parameter import _ParameterCodec


class ParameterBase(ObjectExtended):
    """
    A `Parameter Object`_ defines a single operation parameter.

    .. _Parameter Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#parameterObject
    """

    model_config = dict(undefined_types_warning=False)

    description: Optional[str] = Field(default=None)
    required: Optional[bool] = Field(default=None)
    deprecated: Optional[bool] = Field(default=None)
    allowEmptyValue: Optional[bool] = Field(default=None)

    style: Optional[str] = Field(default=None)
    explode: Optional[bool] = Field(default=None)
    allowReserved: Optional[bool] = Field(default=None)
    schema_: Optional[Schema] = Field(default=None, alias="schema")
    example: Optional[Any] = Field(default=None)
    examples: Optional[Dict[str, Union["Example", Reference]]] = Field(default_factory=dict)

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

    model_config = dict(undefined_types_warning=False)

    def _codec(self):
        return "simple", False
