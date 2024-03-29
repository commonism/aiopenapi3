from typing import Union, List, Optional, Dict, Any

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

    .. _RequestBody: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#request-body-object
    """

    description: Optional[str] = Field(default=None)
    content: Dict[str, MediaType] = Field(...)
    required: Optional[bool] = Field(default=False)


class Link(ObjectExtended):
    """
    A `Link Object`_ describes a single Link from an API Operation Response to an API Operation Request

    .. _Link Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#link-object
    """

    operationRef: Optional[str] = Field(default=None)
    operationId: Optional[str] = Field(default=None)
    parameters: Optional[Dict[str, Union[str, Any, "RuntimeExpression"]]] = Field(default=None)
    requestBody: Optional[Union[str, "RuntimeExpression"]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    server: Optional[Server] = Field(default=None)

    @model_validator(mode="after")
    @classmethod
    def validate_Link_operation(cls, l: '__types["Link"]'):  # type: ignore[name-defined]
        assert not (
            l.operationId != None and l.operationRef != None
        ), "operationId and operationRef are mutually exclusive, only one of them is allowed"
        assert not (
            l.operationId == l.operationRef == None
        ), "operationId and operationRef are mutually exclusive, one of them must be specified"
        return l


class Response(ObjectExtended):
    """
    A `Response Object`_ describes a single response from an API Operation,
    including design-time, static links to operations based on the response.

    .. _Response Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#responses-object
    """

    description: str = Field(...)
    headers: Dict[str, Union[Header, Reference]] = Field(default_factory=dict)
    content: Dict[str, MediaType] = Field(default_factory=dict)
    links: Dict[str, Union[Link, Reference]] = Field(default_factory=dict)


class Operation(ObjectExtended, OperationBase):
    """
    An Operation object as defined `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#operation-object
    """

    tags: Optional[List[str]] = Field(default=None)
    summary: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    externalDocs: Optional[ExternalDocumentation] = Field(default=None)
    operationId: Optional[str] = Field(default=None)
    parameters: List[Union[Parameter, Reference]] = Field(default_factory=list)
    requestBody: Optional[Union[RequestBody, Reference]] = Field(default=None)
    responses: Dict[str, Union[Response, Reference]] = Field(...)
    callbacks: Dict[str, Union["Callback", Reference]] = Field(default_factory=dict)
    deprecated: Optional[bool] = Field(default=None)
    security: Optional[List[SecurityRequirement]] = Field(default=None)
    servers: Optional[List[Server]] = Field(default=None)


class PathItem(ObjectExtended, PathItemBase):
    """
    A Path Item, as defined `here`_.
    Describes the operations available on a single path.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#paths-object
    """

    ref: Optional[str] = Field(default=None, alias="$ref")
    summary: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    get: Optional[Operation] = Field(default=None)
    put: Optional[Operation] = Field(default=None)
    post: Optional[Operation] = Field(default=None)
    delete: Optional[Operation] = Field(default=None)
    options: Optional[Operation] = Field(default=None)
    head: Optional[Operation] = Field(default=None)
    patch: Optional[Operation] = Field(default=None)
    trace: Optional[Operation] = Field(default=None)
    servers: Optional[List[Server]] = Field(default=None)
    parameters: List[Union[Parameter, Reference]] = Field(default_factory=list)


class Paths(PathsBase):
    paths: Dict[str, PathItem]

    @model_validator(mode="before")
    def validate_Paths(cls, values):
        assert values is not None and isinstance(values, dict)
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

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#callback-object

    This object MAY be extended with Specification Extensions.
    """

    root: Dict[str, PathItem]


class RuntimeExpression(RootModel):
    """


    .. Runtime Expression: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#runtime-expressions
    """

    root: str
