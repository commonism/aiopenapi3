import typing
from typing import Union, Any

from pydantic import Field, AnyUrl, PrivateAttr, ConfigDict


from ..base import ObjectExtended, ObjectBase, ReferenceBase

if typing.TYPE_CHECKING:
    from .schemas import Schema
    from .paths import Parameter, PathItem


class ExternalDocumentation(ObjectExtended):
    """
    4.11 External Documentation Object
    Allows referencing an external resource for extended documentation.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#external-documentation-object
    """

    url: AnyUrl = Field(...)
    description: str | None = Field(default=None)


class Reference(ObjectBase, ReferenceBase):
    """
    4.23 Reference Object
    A simple object to allow referencing other components in the OpenAPI Description, internally and externally.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#reference-object
    """

    ref: str = Field(alias="$ref")
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)

    _target: Union["Schema", "Parameter", "Reference", "PathItem"] = PrivateAttr(default=None)

    model_config = ConfigDict(
        # """This object cannot be extended with additional properties and any properties added SHALL be ignored."""
        extra="ignore"
    )

    def __getattr__(self, item: str) -> Any:
        if item != "_target" and not item.startswith("__pydantic_private__"):
            return getattr(self._target, item)
        else:
            return super().__getattr__(item)

    def __setattr__(self, item, value):
        if item != "_target" and not item.startswith("__pydantic_private__"):
            setattr(self._target, item, value)
        else:
            super().__setattr__(item, value)
