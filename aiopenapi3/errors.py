import dataclasses


class SpecError(ValueError):
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


class ParameterFormatError(ValueError):
    pass


class HTTPError(ValueError):
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
