from typing import Union, Any, Optional

from pydantic import Field, model_validator, ConfigDict

from ..base import ObjectExtended, SchemaBase, DiscriminatorBase
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

    .. _Schema Object: https://datatracker.ietf.org/doc/html/draft-bhutton-json-schema-validation-00#section-6
    """

    model_config = ConfigDict(extra="allow")

    """
    JSON Schema: A Media Type for Describing JSON Documents
    https://json-schema.org/draft/2020-12/json-schema-core.html
    """

    """
    8.  The JSON Schema Core Vocabulary
    """
    schema_: str | None = Field(default=None, alias="$schema")
    vocabulary: dict[str, bool] | None = Field(default=None, alias="$vocabulary")
    id: str | None = Field(default=None, alias="$id")
    anchor: str | None = Field(default=None, alias="$anchor")
    dynamicAnchor: bool | None = Field(default=None, alias="$dynamicAnchor")
    ref: str | None = Field(default=None, alias="$ref")
    dynamicRef: str | None = Field(default=None, alias="$dynamicRef")
    defs: dict[str, Any] | None = Field(default=None, alias="$defs")
    comment: str | None = Field(default=None, alias="$comment")

    """
    10. A Vocabulary for Applying Subschemas
    """

    """
    10.2.1. Keywords for Applying Subschemas With Logic
    """
    allOf: list["Schema"] = Field(default_factory=list)
    oneOf: list["Schema"] = Field(default_factory=list)
    anyOf: list["Schema"] = Field(default_factory=list)
    not_: Optional["Schema"] = Field(default=None, alias="not")

    """
    10.2.2. Keywords for Applying Subschemas Conditionally
    """
    if_: Optional["Schema"] = Field(default=None, alias="if")
    then_: Optional["Schema"] = Field(default=None, alias="then")
    else_: Optional["Schema"] = Field(default=None, alias="else")
    dependentSchemas: dict[str, "Schema"] = Field(default_factory=dict)

    """
    10.3.1. Keywords for Applying Subschemas to Arrays
    """
    prefixItems: list["Schema"] | None = Field(default=None)
    items: Union["Schema", list["Schema"]] | None = Field(default=None)
    contains: Optional["Schema"] = Field(default=None)

    """
    10.3.2. Keywords for Applying Subschemas to Objects
    """
    properties: dict[str, "Schema"] = Field(default_factory=dict)
    patternProperties: dict[str, "Schema"] = Field(default_factory=dict)
    additionalProperties: Optional["Schema"] = Field(default=None)
    propertyNames: Optional["Schema"] = Field(default=None)

    """
    11. A Vocabulary for Unevaluated Locations
    """
    unevaluatedItems: Optional["Schema"] = Field(default=None)
    unevaluatedProperties: Optional["Schema"] = Field(default=None)

    """
    JSON Schema Validation: A Vocabulary for Structural Validation of JSON
    https://json-schema.org/draft/2020-12/json-schema-validation.html
    """

    """
    6.1.  Validation Keywords for Any Instance Type
    """

    type: str | list[str] | None = Field(default=None)
    enum: list[Any] | None = Field(default=None)
    const: str | None = Field(default=None)

    """
    6.2.  Validation Keywords for Numeric Instances (number and integer)
    """
    multipleOf: int | None = Field(default=None)
    maximum: float | None = Field(default=None)  # FIXME Field(discriminator='type') would be better
    exclusiveMaximum: int | None = Field(default=None)
    minimum: float | None = Field(default=None)
    exclusiveMinimum: int | None = Field(default=None)

    """
    6.3.  Validation Keywords for Strings
    """
    maxLength: int | None = Field(default=None)
    minLength: int | None = Field(default=None)
    pattern: str | None = Field(default=None)

    """
    6.4.  Validation Keywords for Arrays
    """
    maxItems: int | None = Field(default=None)
    minItems: int | None = Field(default=None)
    uniqueItems: bool | None = Field(default=None)
    maxContains: int | None = Field(default=None)
    minContains: int | None = Field(default=None)

    """
    6.5.  Validation Keywords for Objects
    """
    maxProperties: int | None = Field(default=None)
    minProperties: int | None = Field(default=None)
    required: list[str] = Field(default_factory=list)
    dependentRequired: dict[str, str] = Field(default_factory=dict)  # FIXME

    """
    7.  A Vocabulary for Semantic Content With "format"
    """
    format: str | None = Field(default=None)

    """
    8.  A Vocabulary for the Contents of String-Encoded Data
    """
    contentEncoding: str | None = Field(default=None)
    contentMediaType: str | None = Field(default=None)
    contentSchema: str | None = Field(default=None)

    """
    9.  A Vocabulary for Basic Meta-Data Annotations
    """
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    default: Any | None = Field(default=None)
    deprecated: bool | None = Field(default=None)
    readOnly: bool | None = Field(default=None)
    writeOnly: bool | None = Field(default=None)
    examples: Any | None = Field(default=None)

    """
    The OpenAPI Specification's base vocabulary is comprised of the following keywords:
    """
    discriminator: Discriminator | None = Field(default=None)  # 'Discriminator'
    xml: XML | None = Field(default=None)  # 'XML'
    externalDocs: dict | None = Field(default=None)  # 'ExternalDocs'
    example: Any | None = Field(default=None)

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
