from typing import Optional

from pydantic import Field, Extra

from ..base import ObjectExtended, ObjectBase, ReferenceBase


class ExternalDocumentation(ObjectExtended):
    """
    An `External Documentation Object`_ references external resources for extended
    documentation.

    .. _External Documentation Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#external-documentation-object
    """

    description: Optional[str] = Field(default=None)
    url: str = Field(...)


class Reference(ObjectBase, ReferenceBase):
    """
    A `Reference Object`_ designates a reference to another node in the specification.

    .. _Reference Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#reference-object
    """

    ref: str = Field(alias="$ref")

    _target: object = None

    class Config:
        extra = Extra.ignore

    def __getattr__(self, item):
        if item != "_target":
            return getattr(self._target, item)
        else:
            return getattr(self, item)

    def __setattr__(self, item, value):
        if item != "_target":
            setattr(self._target, item, value)
        else:
            super().__setattr__(item, value)
