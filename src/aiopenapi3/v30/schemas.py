from typing import Union, Any

from pydantic import Field, model_validator, ConfigDict

from ..base import ObjectExtended, SchemaBase, DiscriminatorBase
from .general import Reference
from .xml import XML


class Discriminator(ObjectExtended, DiscriminatorBase):
    """

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#discriminator-object
    """

    propertyName: str = Field(...)
    mapping: dict[str, str] = Field(default_factory=dict)


class Schema(ObjectExtended, SchemaBase):
    """
    The `Schema Object`_ allows the definition of input and output data types.

    .. _Schema Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#schema-object
    """

    title: str | None = Field(default=None)
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
    allOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    oneOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    anyOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    not_: Union["Schema", Reference] | None = Field(default=None, alias="not")
    items: Union["Schema", Reference] | None = Field(default=None)
    properties: dict[str, Union["Schema", Reference]] = Field(default_factory=dict)
    additionalProperties: Union["Schema", Reference] | None = Field(default=None)
    description: str | None = Field(default=None)
    format: str | None = Field(default=None)
    default: Any | None = Field(default=None)
    nullable: bool | None = Field(default=None)
    discriminator: Discriminator | None = Field(default=None)  # 'Discriminator'
    readOnly: bool | None = Field(default=None)
    writeOnly: bool | None = Field(default=None)
    xml: XML | None = Field(default=None)  # 'XML'
    externalDocs: dict | None = Field(default=None)  # 'ExternalDocs'
    example: Any | None = Field(default=None)
    deprecated: bool | None = Field(default=None)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def is_boolean_schema(cls, data: Any) -> Any:
        if not isinstance(data, bool):
            return data
        if data:
            return {}
        else:
            return {"not": {}}

    @model_validator(mode="after")
    def validate_Schema_number_type(self):
        if self.type == "integer":
            for i in ["minimum", "maximum"]:
                if (v := getattr(self, i, None)) is not None and not isinstance(v, int):
                    setattr(self, i, int(v))
        return self

    def __getstate__(self):
        return SchemaBase.__getstate__(self)
