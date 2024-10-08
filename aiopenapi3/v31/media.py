from typing import Union, Optional, Any

from pydantic import Field

from ..base import ObjectExtended

from .example import Example
from .general import Reference
from .schemas import Schema
from .parameter import Header


class Encoding(ObjectExtended):
    """
    A single encoding definition applied to a single schema property.

    .. _Encoding: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#encodingObject
    """

    contentType: Optional[str] = Field(default=None)
    headers: dict[str, Union[Header, Reference]] = Field(default_factory=dict)
    style: Optional[str] = Field(default=None)
    explode: Optional[bool] = Field(default=None)
    allowReserved: Optional[bool] = Field(default=None)


class MediaType(ObjectExtended):
    """
    A `MediaType`_ object provides schema and examples for the media type identified
    by its key.  These are used in a RequestBody object.

    .. _MediaType: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#media-type-object
    """

    schema_: Optional[Schema] = Field(default=None, alias="schema")
    example: Optional[Any] = Field(default=None)  # 'any' type
    examples: dict[str, Union[Example, Reference]] = Field(default_factory=dict)
    encoding: dict[str, Encoding] = Field(default_factory=dict)
