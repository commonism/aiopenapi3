from typing import Union, Any, Optional

from pydantic import Field, PrivateAttr, model_validator

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
    required: list[str] = Field(default_factory=list)
    enum: Optional[list[Any]] = Field(default=None)
    type: Optional[str] = Field(default=None)

    items: Optional[Union[list[Union["Schema", Reference]], Union["Schema", Reference]]] = Field(default=None)
    allOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    properties: dict[str, Union["Schema", Reference]] = Field(default_factory=dict)
    additionalProperties: Optional[Union["Schema", Reference, bool]] = Field(default=None)

    discriminator: Optional[str] = Field(default=None)  # 'Discriminator'
    readOnly: Optional[bool] = Field(default=None)
    xml: Optional[XML] = Field(default=None)  # 'XML'
    externalDocs: Optional[dict] = Field(default=None)  # 'ExternalDocs'
    example: Optional[Any] = Field(default=None)

    @model_validator(mode="wrap")
    @classmethod
    def is_boolean_schema(cls, data: Any, handler: "ValidatorFunctionWrapHandler", info: "ValidationInfo") -> Any:
        if not isinstance(data, bool):
            return handler(data)
        if data:
            return handler(cls.model_validate({}))
        else:
            return handler(_Not.model_validate({"not": {}}))

    def __getstate__(self):
        return SchemaBase.__getstate__(self)


class _Not(Schema):
    not_: Optional["Schema"] = Field(alias="not")
