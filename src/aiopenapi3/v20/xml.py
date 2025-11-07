from pydantic import Field

from .general import ObjectExtended


class XML(ObjectExtended):
    """
    A metadata object that allows for more fine-tuned XML model definitions.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#xml-object
    """

    name: str = Field(default=None)
    namespace: str = Field(default=None)
    prefix: str = Field(default=None)
    attribute: bool = Field(default=False)
    wrapped: bool = Field(default=False)
