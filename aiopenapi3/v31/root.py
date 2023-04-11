from typing import Any, List, Optional, Dict, Union

import pydantic_core
from pydantic import Field, root_validator, validator

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

    model_config = dict(undefined_types_warning=False)

    openapi: str = Field(...)
    info: Info = Field(...)
    jsonSchemaDialect: Optional[str] = Field(default=None)  # FIXME should be URI
    servers: Optional[List[Server]] = Field(default=None)
    #    paths: Dict[str, PathItem] = Field(default_factory=dict)
    paths: Paths = Field(default_factory=dict)
    webhooks: Optional[Dict[str, Union[PathItem, Reference]]] = Field(default_factory=dict)
    components: Optional[Components] = Field(default=None)
    security: Optional[List[SecurityRequirement]] = Field(default=None)
    tags: Optional[List[Tag]] = Field(default_factory=list)
    externalDocs: Optional[Dict[Any, Any]] = Field(default_factory=dict)

    def validate_Root(cls, values):
        assert any([values.get(i) is not None for i in ["paths", "components", "webhooks"]]), values
        return values

    def _resolve_references(self, api):
        RootBase.resolve(api, self, self, PathItem, Reference)
