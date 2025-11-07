from typing import Any

from pydantic import Field

from ..base import ObjectExtended

from .general import Reference


class Example(ObjectExtended):
    """
    A `Example Object`_ holds a reusable set of different aspects of the OAS
    spec.

    .. _Example Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#example-object
    """

    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    value: Any | None = Field(default=None)
    externalValue: str | None = Field(default=None)
