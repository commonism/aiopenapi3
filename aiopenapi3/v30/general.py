import typing
from typing import Optional, Union, Any

from pydantic import Field, PrivateAttr, ConfigDict


from ..base import ObjectExtended, ObjectBase, ReferenceBase


if typing.TYPE_CHECKING:
    from .schemas import Schema
    from .parameter import Parameter


class ExternalDocumentation(ObjectExtended):
    """
    An `External Documentation Object`_ references external resources for extended
    documentation.

    .. _External Documentation Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#external-documentation-object
    """

    url: str = Field(...)
    description: Optional[str] = Field(default=None)


class Reference(ObjectBase, ReferenceBase):
    """
    A `Reference Object`_ designates a reference to another node in the specification.

    .. _Reference Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#reference-object
    """

    ref: str = Field(alias="$ref")

    _target: Union["Schema", "Parameter", "Reference"] = PrivateAttr(default=None)

    model_config = ConfigDict(
        extra="ignore",  # """This object cannot be extended with additional properties and any properties added SHALL be ignored."""
    )

    def __getattr__(self, item: str) -> Any:
        if item != "_target":
            return getattr(self._target, item)
        else:
            return super().__getattr__(item)

    def __setattr__(self, item, value):
        if item != "_target":
            setattr(self._target, item, value)
        else:
            super().__setattr__(item, value)
