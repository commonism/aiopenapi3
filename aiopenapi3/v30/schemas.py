from typing import Union, Any, Optional

from pydantic import Field, model_validator, PrivateAttr, ConfigDict

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

    title: Optional[str] = Field(default=None)
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
    allOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    oneOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    anyOf: list[Union["Schema", Reference]] = Field(default_factory=list)
    not_: Optional[Union["Schema", Reference]] = Field(default=None, alias="not")
    items: Optional[Union["Schema", Reference]] = Field(default=None)
    properties: dict[str, Union["Schema", Reference]] = Field(default_factory=dict)
    additionalProperties: Optional[Union["Schema", Reference]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    format: Optional[str] = Field(default=None)
    default: Optional[Any] = Field(default=None)
    nullable: Optional[bool] = Field(default=None)
    discriminator: Optional[Discriminator] = Field(default=None)  # 'Discriminator'
    readOnly: Optional[bool] = Field(default=None)
    writeOnly: Optional[bool] = Field(default=None)
    xml: Optional[XML] = Field(default=None)  # 'XML'
    externalDocs: Optional[dict] = Field(default=None)  # 'ExternalDocs'
    example: Optional[Any] = Field(default=None)
    deprecated: Optional[bool] = Field(default=None)

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
    @classmethod
    def validate_Schema_number_type(cls, s: "Schema"):
        if s.type == "integer":
            for i in ["minimum", "maximum"]:
                if (v := getattr(s, i, None)) is not None and not isinstance(v, int):
                    setattr(s, i, int(v))
        return s

    def __getstate__(self):
        return SchemaBase.__getstate__(self)
