from pydantic import Field

from ..base import ObjectExtended

from .example import Example
from .paths import RequestBody, Link, Response, Callback, PathItem
from .general import Reference
from .parameter import Header, Parameter
from .schemas import Schema
from .security import SecurityScheme
from .media import MediaType


class Components(ObjectExtended):
    """
    4.7 Components Object
    Holds a set of reusable objects for different aspects of the OAS.
    All objects defined within the Components Object will have no effect on the API unless they are explicitly
    referenced from outside the Components Object.

    As described `here`_
    .. _Components Object: https://spec.openapis.org/oas/v3.2.0.html#components-object
    """

    schemas: dict[str, Schema] = Field(default_factory=dict)
    responses: dict[str, Response | Reference] = Field(default_factory=dict)
    parameters: dict[str, Parameter | Reference] = Field(default_factory=dict)
    examples: dict[str, Example | Reference] = Field(default_factory=dict)
    requestBodies: dict[str, RequestBody | Reference] = Field(default_factory=dict)
    headers: dict[str, Header | Reference] = Field(default_factory=dict)
    securitySchemes: dict[str, SecurityScheme | Reference] = Field(default_factory=dict)
    links: dict[str, Link | Reference] = Field(default_factory=dict)
    callbacks: dict[str, Callback | Reference] = Field(default_factory=dict)
    pathItems: dict[str, PathItem | Reference] = Field(default_factory=dict)
    mediaTypes: dict[str, MediaType | Reference] = Field(default_factory=dict)
