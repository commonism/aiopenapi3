from typing import Union

from pydantic import Field

from ..base import ObjectExtended

from .example import Example
from .paths import RequestBody, Link, Response, Callback
from .general import Reference
from .parameter import Header, Parameter
from .schemas import Schema
from .security import SecurityScheme


class Components(ObjectExtended):
    """
    A `Components Object`_ holds a reusable set of different aspects of the OAS
    spec.

    .. _Components Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#components-object
    """

    schemas: dict[str, Union[Schema, Reference]] = Field(default_factory=dict)
    responses: dict[str, Union[Response, Reference]] = Field(default_factory=dict)
    parameters: dict[str, Union[Parameter, Reference]] = Field(default_factory=dict)
    examples: dict[str, Union[Example, Reference]] = Field(default_factory=dict)
    requestBodies: dict[str, Union[RequestBody, Reference]] = Field(default_factory=dict)
    headers: dict[str, Union[Header, Reference]] = Field(default_factory=dict)
    securitySchemes: dict[str, Union[SecurityScheme, Reference]] = Field(default_factory=dict)
    links: dict[str, Union[Link, Reference]] = Field(default_factory=dict)
    callbacks: dict[str, Union[Callback, Reference]] = Field(default_factory=dict)
