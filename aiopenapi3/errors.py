from typing import List, Tuple, Dict
import dataclasses


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
    paths: List[Tuple[str, str, object]]


class ParameterFormatError(SpecError):
    """
    The specified parameter encoding is invalid for the parameter family
    """

    pass


class HTTPError(ErrorBase):
    pass


@dataclasses.dataclass
class RequestError(HTTPError):
    operation: object
    request: object
    data: object
    parameters: object


class ResponseError(HTTPError):
    """the response can not be processed accordingly"""

    pass


@dataclasses.dataclass
class ContentLengthExceededError(ResponseError):
    """The Content-Length exceeds our Limits"""

    operation: object
    content_length: int
    message: str
    response: object


@dataclasses.dataclass
class ContentTypeError(ResponseError):
    """The content-type is unexpected"""

    operation: object
    content_type: str
    message: str
    response: object


@dataclasses.dataclass
class HTTPStatusError(ResponseError):
    """The HTTP Status is unexpected"""

    operation: object
    http_status: int
    message: str
    response: object


@dataclasses.dataclass
class ResponseDecodingError(ResponseError):
    """the json decoder failed"""

    operation: object
    data: object
    response: object


@dataclasses.dataclass
class ResponseSchemaError(ResponseError):
    """the response data does not match the schema"""

    operation: object
    expectation: object
    schema: object
    response: object
    exception: object


@dataclasses.dataclass
class HeadersMissingError(ResponseError):
    """the response is missing required header/s"""

    operation: object
    missing: Dict[str, object]
    response: object
