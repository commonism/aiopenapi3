import sys

if sys.version_info < (3, 12):
    from typing import Any
    from typing_extensions import Self
else:
    from typing import Any, Self

from pydantic import Field

from ..base import ObjectExtended

from .example import Example
from .general import Reference
from .schemas import Schema
from .parameter import Header


class Encoding(ObjectExtended):
    """
    4.15 Encoding Object

    A single encoding definition applied to a single value, with the mapping of Encoding Objects to values determined by
    the Media Type Object as described under Encoding Usage and Restrictions.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#encoding-object
    """

    contentType: str | None = Field(default=None)
    headers: dict[str, Header | Reference] = Field(default_factory=dict)

    encoding: dict[str, Self] = Field(default_factory=dict)
    prefixEncoding: list[Self] = Field(default_factory=list)
    itemEncoding: Self | None = Field(default=None)

    # 4.15.1.2 Fixed Fields for RFC6570-style Serialization
    style: str | None = Field(default=None)
    explode: bool | None = Field(default=None)
    allowReserved: bool | None = Field(default=None)


class MediaType(ObjectExtended):
    """
    4.14 Media Type Object
    Each Media Type Object describes content structured in accordance with the media type identified by its key.
    Multiple Media Type Objects can be used to describe content that can appear in any of several different media types.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#media-type-object
    """

    schema_: Schema | None = Field(default=None, alias="schema")
    itemSchema: Schema | None = Field(default=None)
    example: Any | None = Field(default=None)  # 'any' type
    examples: dict[str, Example | Reference] = Field(default_factory=dict)
    encoding: dict[str, Encoding] = Field(default_factory=dict)
    prefixEncoding: list[Encoding] = Field(default_factory=list)
    itemEncoding: Encoding | None = Field(default=None)
