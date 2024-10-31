from typing import Any, Optional, Union

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
    jsonSchemaDialect: Optional[str] = Field(default=None)  # FIXME should be URI
    servers: Optional[list[Server]] = Field(default_factory=list)
    #    paths: Dict[str, PathItem] = Field(default_factory=dict)
    paths: Paths = Field(default_factory=dict)
    webhooks: dict[str, Union[PathItem, Reference]] = Field(default_factory=dict)
    components: Optional[Components] = Field(default_factory=Components)
    security: Optional[list[SecurityRequirement]] = Field(default_factory=list)
    tags: list[Tag] = Field(default_factory=list)
    externalDocs: dict[Any, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    @classmethod
    def validate_Root(cls, r: "Root") -> "Self":
        assert r.paths or r.components or r.webhooks
        return r

    def _resolve_references(self, api):
        RootBase.resolve(api, self, self, PathItem, Reference)
