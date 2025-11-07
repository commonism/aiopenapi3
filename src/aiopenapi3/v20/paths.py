from typing import Any

from pydantic import Field, model_validator

from .general import ExternalDocumentation
from .general import Reference
from .parameter import Header, Parameter
from .schemas import Schema
from .security import SecurityRequirement
from ..base import ObjectExtended, PathsBase, OperationBase, PathItemBase


class Response(ObjectExtended):
    """
    Describes a single response from an API Operation.

    .. _Response Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#response-object
    """

    description: str = Field(...)
    schema_: Schema | None = Field(default=None, alias="schema")
    headers: dict[str, Header] = Field(default_factory=dict)
    examples: dict[str, Any] | None = Field(default=None)


class Operation(ObjectExtended, OperationBase):
    """
    An Operation object as defined `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#operation-object
    """

    tags: list[str] | None = Field(default=None)
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    externalDocs: ExternalDocumentation | None = Field(default=None)
    operationId: str | None = Field(default=None)
    consumes: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    parameters: list[Parameter | Reference] = Field(default_factory=list)
    responses: dict[str, Reference | Response] = Field(default_factory=dict)
    schemes: list[str] = Field(default_factory=list)
    deprecated: bool | None = Field(default=None)
    security: list[SecurityRequirement] | None = Field(default=None)


class PathItem(ObjectExtended, PathItemBase):
    """
    A Path Item, as defined `here`_.
    Describes the operations available on a single path.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#path-item-object
    """

    ref: str | None = Field(default=None, alias="$ref")
    get: Operation | None = Field(default=None)
    put: Operation | None = Field(default=None)
    post: Operation | None = Field(default=None)
    delete: Operation | None = Field(default=None)
    options: Operation | None = Field(default=None)
    head: Operation | None = Field(default=None)
    patch: Operation | None = Field(default=None)
    parameters: list[Parameter | Reference] = Field(default_factory=list)


class Paths(PathsBase):
    paths: dict[str, PathItem]

    @model_validator(mode="before")
    def validate_Paths(cls, values):
        assert values is not None
        p = {}
        e = {}
        for k, v in values.items():
            if k[:2] == "x-":
                e[k] = v
            else:
                p[k] = v
        return {"paths": p, "extensions": e}
