from typing import Union, Any, Optional

from pydantic import Field, model_validator, ValidatorFunctionWrapHandler, ValidationInfo

from .general import Reference
from .xml import XML
from ..base import ObjectExtended, SchemaBase


class Schema(ObjectExtended, SchemaBase):
    """
    The Schema Object allows the definition of input and output data types.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md##schema-object
    """

    ref: str | None = Field(default=None, alias="$ref")
    format: str | None = Field(default=None)
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    default: Any | None = Field(default=None)

    multipleOf: int | None = Field(default=None)
    maximum: float | None = Field(default=None)  # FIXME Field(discriminator='type') would be better
    exclusiveMaximum: bool | None = Field(default=None)
    minimum: float | None = Field(default=None)
    exclusiveMinimum: bool | None = Field(default=None)
    maxLength: int | None = Field(default=None)
    minLength: int | None = Field(default=None)
    pattern: str | None = Field(default=None)
    maxItems: int | None = Field(default=None)
    minItems: int | None = Field(default=None)
    uniqueItems: bool | None = Field(default=None)
    maxProperties: int | None = Field(default=None)
    minProperties: int | None = Field(default=None)
    required: list[str] = Field(default_factory=list)
    enum: list[Any] | None = Field(default=None)
    type: str | None = Field(default=None)

    items: list[Union["Schema", Reference]] | Union["Schema", Reference] | None = Field(default=None)
    allOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    properties: dict[str, Union["Schema", Reference]] = Field(default_factory=dict)
    additionalProperties: Union["Schema", Reference, bool] | None = Field(default=None)

    discriminator: str | None = Field(default=None)  # 'Discriminator'
    readOnly: bool | None = Field(default=None)
    xml: XML | None = Field(default=None)  # 'XML'
    externalDocs: dict | None = Field(default=None)  # 'ExternalDocs'
    example: Any | None = Field(default=None)

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
