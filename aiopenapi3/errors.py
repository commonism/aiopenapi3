import typing
from typing import List, Tuple, Dict, Optional
import dataclasses

import httpx


if typing.TYPE_CHECKING:
    from ._types import (
        OperationType,
        SchemaType,
        RequestType,
        RequestData,
        RequestParameters,
        ServerType,
        HeaderType,
        ExpectedType,
        OperationType,
    )


class ErrorBase(Exception):
    pass


class WarningBase(UserWarning):
    pass


class DiscriminatorWarning(WarningBase):
    pass


class SpecError(ErrorBase, ValueError):
    """
    This error class is used when an invalid format is found while parsing an
    object in the spec.
    """

    def __init__(self, message, element=None):
        self.message = message
        self.element = element


class ReferenceResolutionError(SpecError):
    """
    This error class is used when resolving a reference fails, usually because
    of a malformed path in the reference.
    """

    def __init__(self, message, element=None):
        super().__init__(message, element)
        self.document = None


@dataclasses.dataclass
class OperationParameterValidationError(SpecError):
    """
    The operations parameters do not match the path parameters
    """

    path: str
    method: str
    operationid: str
    message: str


@dataclasses.dataclass
class OperationIdDuplicationError(SpecError):
    """
    The OperationId is not unique
    """

    operationid: str
    paths: List[Tuple[str, str, object, Optional[List["ServerType"]]]]


class ParameterFormatError(SpecError):
    """
    The specified parameter encoding is invalid for the parameter family
    """

    pass


class HTTPError(ErrorBase):
    pass


@dataclasses.dataclass(repr=False)
class RequestError(HTTPError):
    operation: Optional["OperationType"]
    request: Optional["RequestType"]
    data: Optional["RequestData"]
    parameters: Optional["RequestParameters"]

    def __str__(self):
        if self.request:
            return f"<{self.__class__.__name__} {self.operation.operationId}/{self.request.method}#{self.request.path}>"
        else:
            return f"<{self.__class__.__name__}>"


class ResponseError(HTTPError):
    """the response can not be processed accordingly"""

    def __repr__(self):
        if hasattr(self, "__cause__"):
            return f"<{self.__class__} {self.__cause__.__repr__()}"
        else:
            return super().__repr__()

    def __str__(self):
        return f"<{self.__class__.__name__} {self.response.request.method} '{self.response.request.url.path}' ({self.operation.operationId})>"


@dataclasses.dataclass(repr=False)
class ContentLengthExceededError(ResponseError):
    """The Content-Length exceeds our Limits"""

    operation: "OperationType"
    content_length: int
    message: str
    response: httpx.Response


@dataclasses.dataclass(repr=False)
class ContentTypeError(ResponseError):
    """The content-type is unexpected"""

    operation: "OperationType"
    content_type: Optional[str]
    message: str
    response: httpx.Response

    def __str__(self):
        return f"""<{self.__class__.__name__} {self.response.request.method} '{self.response.request.url.path}' ({self.operation.operationId})>
            {self.content_type}"""


@dataclasses.dataclass(repr=False)
class HTTPStatusError(ResponseError):
    """The HTTP Status is unexpected"""

    operation: "OperationType"
    http_status: int
    message: str
    response: httpx.Response

    def __str__(self):
        return f"""<{self.__class__.__name__} {self.response.request.method} '{self.response.request.url.path}' ({self.operation.operationId})>
            {self.http_status}"""


@dataclasses.dataclass(repr=False)
class ResponseDecodingError(ResponseError):
    """the json decoder failed"""

    operation: "OperationType"
    data: str
    response: httpx.Response


@dataclasses.dataclass(repr=False)
class ResponseSchemaError(ResponseError):
    """the response data does not match the schema"""

    operation: "OperationType"
    expectation: "ExpectedType"
    schema: Optional["SchemaType"]
    response: httpx.Response
    exception: Optional[Exception]

    def __str__(self):
        return f"""<{self.__class__.__name__} {self.response.request.method} '{self.response.request.url.path}' ({self.operation.operationId})
        {self.exception}>"""


@dataclasses.dataclass(repr=False)
class HeadersMissingError(ResponseError):
    """the response is missing required header/s"""

    operation: "OperationType"
    missing: Dict[str, "HeaderType"]
    response: httpx.Response

    def __str__(self):
        return f"""<{self.__class__.__name__} {self.response.request.method} '{self.response.request.url.path}' ({self.operation.operationId})
        {self.missing}>"""
