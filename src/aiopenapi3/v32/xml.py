from pydantic import Field

from .general import ObjectExtended


class XML(ObjectExtended):
    """

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#xml-object
    """

    nodeType: str | None = Field(default=None)
    name: str | None = Field(default=None)
    namespace: str | None = Field(default=None)
    prefix: str | None = Field(default=None)
    attribute: bool = Field(default=False, deprecated=True)
    wrapped: bool = Field(default=False, deprecated=True)
