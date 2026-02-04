from typing import Union, Any

from pydantic import Field, model_validator, RootModel

from ..base import ObjectExtended, PathsBase, OperationBase, PathItemBase
from .general import ExternalDocumentation
from .general import Reference
from .media import MediaType
from .parameter import Header, Parameter
from .servers import Server
from .security import SecurityRequirement


class RequestBody(ObjectExtended):
    """
    A `RequestBody`_ object describes a single request body.

    .. _RequestBody: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#requestBodyObject
    """

    description: str | None = Field(default=None)
    content: dict[str, MediaType] = Field(...)
    required: bool | None = Field(default=False)


class Link(ObjectExtended):
    """
    A `Link Object`_ describes a single Link from an API Operation Response to an API Operation Request

    .. _Link Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#link-object
    """

    operationRef: str | None = Field(default=None)
    operationId: str | None = Field(default=None)
    parameters: dict[str, Union[str, Any, "RuntimeExpression"]] | None = Field(default=None)
    requestBody: Union[Any, "RuntimeExpression"] | None = Field(default=None)
    description: str | None = Field(default=None)
    server: Server | None = Field(default=None)

    @model_validator(mode="after")
    def validate_Link_operation(cls, l: '__types["Link"]'):  # type: ignore[name-defined]
        assert not (l.operationId is not None and l.operationRef is not None), (
            "operationId and operationRef are mutually exclusive, only one of them is allowed"
        )
        assert not (l.operationId == l.operationRef is None), (
            "operationId and operationRef are mutually exclusive, one of them must be specified"
        )
        return l


class Response(ObjectExtended):
    """
    A `Response Object`_ describes a single response from an API Operation,
    including design-time, static links to operations based on the response.

    .. _Response Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#responseObject
    """

    description: str = Field(...)
    headers: dict[str, Header | Reference] = Field(default_factory=dict)
    content: dict[str, MediaType] = Field(default_factory=dict)
    links: dict[str, Link | Reference] = Field(default_factory=dict)


class Operation(ObjectExtended, OperationBase):
    """
    An Operation object as defined `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#operationObject
    """

    tags: list[str] | None = Field(default=None)
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    externalDocs: ExternalDocumentation | None = Field(default=None)
    operationId: str | None = Field(default=None)
    parameters: list[Parameter | Reference] = Field(default_factory=list)
    requestBody: RequestBody | Reference | None = Field(default=None)
    responses: dict[str, Response | Reference] = Field(default_factory=dict)
    callbacks: dict[str, Union["Callback", Reference]] = Field(default_factory=dict)
    deprecated: bool | None = Field(default=None)
    security: list[SecurityRequirement] | None = Field(default=None)
    servers: list[Server] | None = Field(default=None)


class PathItem(ObjectExtended, PathItemBase):
    """
    A Path Item, as defined `here`_.
    Describes the operations available on a single path.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#pathItemObject
    """

    ref: str | None = Field(default=None, alias="$ref")
    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    get: Operation | None = Field(default=None)
    put: Operation | None = Field(default=None)
    post: Operation | None = Field(default=None)
    delete: Operation | None = Field(default=None)
    options: Operation | None = Field(default=None)
    head: Operation | None = Field(default=None)
    patch: Operation | None = Field(default=None)
    trace: Operation | None = Field(default=None)
    servers: list[Server] | None = Field(default=None)
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
                e[k[2:]] = v
            else:
                p[k] = v
        return {"paths": p, "extensions": e}


class Callback(RootModel):
    """
    A map of possible out-of band callbacks related to the parent operation.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#callback-object

    This object MAY be extended with Specification Extensions.
    """

    root: dict[str, PathItem]


class RuntimeExpression(RootModel):
    """


    .. Runtime Expression: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#runtimeExpression
    """

    root: str
