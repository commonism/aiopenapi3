from pydantic import Field

from ..base import ObjectExtended
from .general import ExternalDocumentation


class Tag(ObjectExtended):
    """
    Allows adding meta data to a single tag that is used by the Operation Object. It is not mandatory to have a Tag Object per tag used there.

    .. _Tag Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#tag-object
    """

    name: str = Field(...)
    description: str | None = Field(default=None)
    externalDocs: ExternalDocumentation | None = Field(default=None)
