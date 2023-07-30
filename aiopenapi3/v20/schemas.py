from typing import Union, List, Any, Optional, Dict

from pydantic import Field, PrivateAttr

from .general import Reference
from .xml import XML
from ..base import ObjectExtended, SchemaBase


class Schema(ObjectExtended, SchemaBase):
    """
    The Schema Object allows the definition of input and output data types.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md##schema-object
    """

    ref: Optional[str] = Field(default=None, alias="$ref")
    format: Optional[str] = Field(default=None)
    title: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    default: Optional[Any] = Field(default=None)

    multipleOf: Optional[int] = Field(default=None)
    maximum: Optional[float] = Field(default=None)  # FIXME Field(discriminator='type') would be better
    exclusiveMaximum: Optional[bool] = Field(default=None)
    minimum: Optional[float] = Field(default=None)
    exclusiveMinimum: Optional[bool] = Field(default=None)
    maxLength: Optional[int] = Field(default=None)
    minLength: Optional[int] = Field(default=None)
    pattern: Optional[str] = Field(default=None)
    maxItems: Optional[int] = Field(default=None)
    minItems: Optional[int] = Field(default=None)
    uniqueItems: Optional[bool] = Field(default=None)
    maxProperties: Optional[int] = Field(default=None)
    minProperties: Optional[int] = Field(default=None)
    required: Optional[List[str]] = Field(default_factory=list)
    enum: Optional[List[Any]] = Field(default=None)
    type: Optional[str] = Field(default=None)

    items: Optional[Union[List[Union["Schema", Reference]], Union["Schema", Reference]]] = Field(default=None)
    allOf: Optional[List[Union["Schema", Reference]]] = Field(default_factory=list)
    properties: Optional[Dict[str, Union["Schema", Reference]]] = Field(default_factory=dict)
    additionalProperties: Optional[Union[bool, "Schema", Reference]] = Field(default=None)

    discriminator: Optional[str] = Field(default=None)  # 'Discriminator'
    readOnly: Optional[bool] = Field(default=None)
    xml: Optional[XML] = Field(default=None)  # 'XML'
    externalDocs: Optional[dict] = Field(default=None)  # 'ExternalDocs'
    example: Optional[Any] = Field(default=None)

    def __getstate__(self):
        return SchemaBase.__getstate__(self)
