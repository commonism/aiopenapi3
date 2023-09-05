from typing import List, Optional, Dict

from pydantic import Field, validator

from .general import Reference, ExternalDocumentation
from .info import Info
from .parameter import Parameter
from .paths import Response, Paths, PathItem
from .schemas import Schema
from .security import SecurityScheme, SecurityRequirement
from .tag import Tag
from ..base import ObjectExtended, RootBase


class Root(ObjectExtended, RootBase):
    """
    This is the root document object for the API specification.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#swagger-object
    """

    swagger: str = Field(...)
    info: Info = Field(...)
    host: Optional[str] = Field(default=None)
    basePath: Optional[str] = Field(default=None)
    schemes: List[str] = Field(default_factory=list)
    consumes: List[str] = Field(default_factory=list)
    produces: List[str] = Field(default_factory=list)
    paths: Paths = Field(default_factory=dict)
    definitions: Dict[str, Schema] = Field(default_factory=dict)
    parameters: Dict[str, Parameter] = Field(default_factory=dict)
    responses: Dict[str, Response] = Field(default_factory=dict)
    securityDefinitions: Dict[str, SecurityScheme] = Field(default_factory=dict)
    security: Optional[List[SecurityRequirement]] = Field(default=None)
    tags: List[Tag] = Field(default_factory=list)
    externalDocs: Optional[ExternalDocumentation] = Field(default=None)

    def _resolve_references(self, api):
        RootBase.resolve(api, self, self, PathItem, Reference)
