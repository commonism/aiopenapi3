from typing import Any

from pydantic import Field

from ..base import ObjectExtended


class Example(ObjectExtended):
    """
    4.19 Example Object

    An object grouping an internal or external example value with basic summary and description metadata.
    The examples can show either data suitable for schema validation, or serialized data as required by the
    containing Media Type Object, Parameter Object, or Header Object.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#example-object
    """

    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    dataValue: Any | None = Field(default=None)
    serializedValue: str | None = Field(default=None)
    externalValue: str | None = Field(default=None)
    value: Any | None = Field(default=None)
