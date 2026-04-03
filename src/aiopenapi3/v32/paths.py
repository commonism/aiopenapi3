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
    4.13 Request Body Object
    Describes a single request body.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#request-body-object
    """

    description: str | None = Field(default=None)
    content: dict[str, MediaType] = Field(...)
    required: bool | None = Field(default=False)


class Link(ObjectExtended):
    """
    4.20 Link Object
    The Link Object represents a possible design-time link for a response.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#link-object
    """

    operationRef: str | None = Field(default=None)
    operationId: str | None = Field(default=None)
    parameters: dict[str, Union[str, Any, "RuntimeExpression"]] | None = Field(default=None)
    requestBody: Union[Any, "RuntimeExpression"] | None = Field(default=None)
    description: str | None = Field(default=None)
    server: Server | None = Field(default=None)

    @model_validator(mode="after")
    def validate_Link_operation(self):  # type: ignore[name-defined]
        assert not (self.operationId is not None and self.operationRef is not None), (
            "operationId and operationRef are mutually exclusive, only one of them is allowed"
        )
        assert not (self.operationId == self.operationRef is None), (
            "operationId and operationRef are mutually exclusive, one of them must be specified"
        )
        return self


class Response(ObjectExtended):
    """
    4.17 Response Object
    Describes a single response from an API operation, including design-time, static links to operations
    based on the response.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#response-object
    """

    summary: str | None = Field(default=None)
    description: str | None = Field(default=None)
    headers: dict[str, Header | Reference] = Field(default_factory=dict)
    content: dict[str, MediaType] = Field(default_factory=dict)
    links: dict[str, Link | Reference] = Field(default_factory=dict)


class Operation(ObjectExtended, OperationBase):
    """
    4.10 Operation Object
    Describes a single API operation on a path.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#operation-object
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
    4.9 Path Item Object
    Describes the operations available on a single path. A Path Item MAY be empty, due to ACL constraints.
    The path itself is still exposed to the documentation viewer but they will not know which operations and
    parameters are available.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#path-item-object
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
    query: Operation | None = Field(default=None)
    additionalOperations: dict[str, Operation] | None = Field(default_factory=dict)
    servers: list[Server] | None = Field(default=None)
    parameters: list[Parameter | Reference] = Field(default_factory=list)


class Paths(PathsBase):
    """
    4.8 Paths Object
    Holds the relative paths to the individual endpoints and their operations. The path is appended to the URL from the
    Server Object in order to construct the full URL.
    The Paths Object MAY be empty, due to Access Control List (ACL) constraints.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#paths-object
    """

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
    4.18 Callback Object

    A map of possible out-of band callbacks related to the parent operation.
    Each value in the map is a Path Item Object that describes a set of requests that may be initiated by
    the API provider and the expected responses.

    .. _here: https://spec.openapis.org/oas/v3.2.0.html#callback-object

    This object MAY be extended with Specification Extensions.
    """

    """
    4.18.2 Key Expression
    The key that identifies the Path Item Object is a runtime expression that can be evaluated in the context of a
    runtime HTTP request/response to identify the URL to be used for the callback request.
    """
    root: dict["RuntimeExpression", PathItem]


class RuntimeExpression(RootModel):
    """
    4.20.3 Runtime Expressions
    Runtime expressions allow defining values based on information that will only be available within the HTTP message
    in an actual API call. This mechanism is used by Link Objects and Callback Objects.


    .. _here: https://spec.openapis.org/oas/v3.2.0.html#runtime-expressions
    """

    root: str
