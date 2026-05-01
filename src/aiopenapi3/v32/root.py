from typing import Any

import pydantic
from pydantic import Field, model_validator

from ..base import ObjectExtended, RootBase

from .info import Info
from .paths import Paths, PathItem
from .security import SecurityRequirement
from .servers import Server

from .components import Components
from .general import Reference
from .tag import Tag


class Root(ObjectExtended, RootBase):
    """
    4.1 OpenAPI Object

    This is the root object of the `OpenAPI Description`_

    .. _OpenAPI Description: https://spec.openapis.org/oas/v3.2.0.html#openapi-object
    """

    openapi: str = Field(...)
    self_: pydantic.AnyHttpUrl | None = Field(default=None, alias="$self")
    info: Info = Field(...)
    jsonSchemaDialect: pydantic.AnyHttpUrl | None = Field(default=None)
    servers: list[Server] | None = Field(default_factory=list)
    paths: Paths = Field(default_factory=dict)
    webhooks: dict[str, PathItem | Reference] = Field(default_factory=dict)
    components: Components | None = Field(default_factory=Components)
    security: list[SecurityRequirement] | None = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    externalDocs: dict[Any, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_Root(self) -> "Self":  # noqa: F821
        assert self.paths or self.components or self.webhooks
        return self

    def _resolve_references(self, api):
        RootBase.resolve(api, self, self, PathItem, Reference)
