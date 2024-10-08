from typing import Union, Optional, Any

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
    schema_: Optional[Schema] = Field(default=None, alias="schema")
    headers: dict[str, Header] = Field(default_factory=dict)
    examples: Optional[dict[str, Any]] = Field(default=None)


class Operation(ObjectExtended, OperationBase):
    """
    An Operation object as defined `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#operation-object
    """

    tags: Optional[list[str]] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    externalDocs: Optional[ExternalDocumentation] = Field(default=None)
    operationId: Optional[str] = Field(default=None)
    consumes: list[str] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    parameters: list[Union[Parameter, Reference]] = Field(default_factory=list)
    responses: dict[str, Union[Reference, Response]] = Field(default_factory=dict)
    schemes: list[str] = Field(default_factory=list)
    deprecated: Optional[bool] = Field(default=None)
    security: Optional[list[SecurityRequirement]] = Field(default=None)


class PathItem(ObjectExtended, PathItemBase):
    """
    A Path Item, as defined `here`_.
    Describes the operations available on a single path.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#path-item-object
    """

    ref: Optional[str] = Field(default=None, alias="$ref")
    get: Optional[Operation] = Field(default=None)
    put: Optional[Operation] = Field(default=None)
    post: Optional[Operation] = Field(default=None)
    delete: Optional[Operation] = Field(default=None)
    options: Optional[Operation] = Field(default=None)
    head: Optional[Operation] = Field(default=None)
    patch: Optional[Operation] = Field(default=None)
    parameters: list[Union[Parameter, Reference]] = Field(default_factory=list)


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
