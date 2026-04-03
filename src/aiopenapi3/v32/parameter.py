import enum
import typing
from typing import Union, Any

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
    4.12 Parameter Object

    Describes a single operation parameter.

    A `Parameter Object`_ defines a single operation parameter.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#parameter-object
    """

    description: str | None = Field(default=None)
    required: bool | None = Field(default=None)
    deprecated: bool | None = Field(default=None)
    allowEmptyValue: bool | None = Field(default=None)
    example: Any | None = Field(default=None)
    examples: dict[str, Union["Example", Reference]] = Field(default_factory=dict)

    # 4.12.2.2 Fixed Fields for use with schema
    style: str | None = Field(default=None)  # FIXME 4.12.3 Style Values
    explode: bool | None = Field(default=None)
    allowReserved: bool | None = Field(default=None)
    schema_: Schema | None = Field(default=None, alias="schema")

    # 4.12.2.3 Fixed Fields for use with content
    content: dict[str, "MediaType"] | None = None


class _In(str, enum.Enum):
    query = "query"
    querystring = "querystring"
    header = "header"
    path = "path"
    cookie = "cookie"


class Parameter(ParameterBase, _ParameterCodec):
    name: str = Field()
    in_: _In = Field(alias="in")


class Header(ParameterBase, _ParameterCodec):
    """
    4.21 Header Object
    Describes a single header for HTTP responses and for individual parts in multipart representations;
    see the relevant Response Object and Encoding Object documentation for restrictions on which headers
    can be described.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#header-object
    """

    allowEmptyValue: None
    allowReserved: None

    def _codec(self):
        schema = self.schema_ or self.content.get("application/json").schema_
        return schema, "simple", False
