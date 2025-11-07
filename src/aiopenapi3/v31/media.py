from typing import Any

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

    contentType: str | None = Field(default=None)
    headers: dict[str, Header | Reference] = Field(default_factory=dict)
    style: str | None = Field(default=None)
    explode: bool | None = Field(default=None)
    allowReserved: bool | None = Field(default=None)


class MediaType(ObjectExtended):
    """
    A `MediaType`_ object provides schema and examples for the media type identified
    by its key.  These are used in a RequestBody object.

    .. _MediaType: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#media-type-object
    """

    schema_: Schema | None = Field(default=None, alias="schema")
    example: Any | None = Field(default=None)  # 'any' type
    examples: dict[str, Example | Reference] = Field(default_factory=dict)
    encoding: dict[str, Encoding] = Field(default_factory=dict)
