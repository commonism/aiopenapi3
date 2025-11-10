from typing import Any

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
    This class represents the root of the OpenAPI schema document, as defined
    in `the spec`_

    .. _the spec: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#openapi-object
    """

    openapi: str = Field(...)
    info: Info = Field(...)
    jsonSchemaDialect: str | None = Field(default=None)  # FIXME should be URI
    servers: list[Server] | None = Field(default_factory=list)
    #    paths: Dict[str, PathItem] = Field(default_factory=dict)
    paths: Paths = Field(default_factory=dict)
    webhooks: dict[str, PathItem | Reference] = Field(default_factory=dict)
    components: Components | None = Field(default_factory=Components)
    security: list[SecurityRequirement] | None = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    externalDocs: dict[Any, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_Root(self) -> "Self":
        assert self.paths or self.components or self.webhooks
        return self

    def _resolve_references(self, api):
        RootBase.resolve(api, self, self, PathItem, Reference)
