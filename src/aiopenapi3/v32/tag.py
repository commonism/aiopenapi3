from pydantic import Field

from ..base import ObjectExtended
from .general import ExternalDocumentation


class Tag(ObjectExtended):
    """
    4.22 Tag Object
    Adds metadata to a single tag that is used by the Operation Object.
    It is not mandatory to have a Tag Object per tag defined in the Operation Object instances.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#tag-object
    """

    name: str = Field(...)
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    externalDocs: ExternalDocumentation | None = Field(default=None)
    parent: str | None = Field(default=None)
    kind: str | None = Field(default=None)
