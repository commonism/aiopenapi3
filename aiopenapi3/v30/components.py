from typing import Union, Dict

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

    schemas: Dict[str, Union[Schema, Reference]] = Field(default_factory=dict)
    responses: Dict[str, Union[Response, Reference]] = Field(default_factory=dict)
    parameters: Dict[str, Union[Parameter, Reference]] = Field(default_factory=dict)
    examples: Dict[str, Union[Example, Reference]] = Field(default_factory=dict)
    requestBodies: Dict[str, Union[RequestBody, Reference]] = Field(default_factory=dict)
    headers: Dict[str, Union[Header, Reference]] = Field(default_factory=dict)
    securitySchemes: Dict[str, Union[SecurityScheme, Reference]] = Field(default_factory=dict)
    links: Dict[str, Union[Link, Reference]] = Field(default_factory=dict)
    callbacks: Dict[str, Union[Callback, Reference]] = Field(default_factory=dict)
