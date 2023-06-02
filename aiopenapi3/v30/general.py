from typing import Optional

from pydantic import Field
from pydantic._internal._model_construction import model_extra_private_getattr

from ..base import ObjectExtended, ObjectBase, ReferenceBase


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

    _target: object = None

    model_config = dict(
        extra="ignore",  # """This object cannot be extended with additional properties and any properties added SHALL be ignored."""
    )

    def l__getattr__(self, item):
        if item != "_target":
            return getattr(self._target, item)
        else:
            return model_extra_private_getattr(self, "_target")

    def __setattr__(self, item, value):
        if item != "_target":
            setattr(self._target, item, value)
        else:
            super().__setattr__(item, value)


Reference.__getattr__ = Reference.l__getattr__
