from .components import Components
from .example import Example
from .general import ExternalDocumentation, Reference
from .glue import AsyncRequest, Request
from .info import Contact, Info, License
from .media import Encoding, MediaType
from .parameter import Header, Parameter
from .paths import Callback, Link, Operation, PathItem, Paths, RequestBody, Response, RuntimeExpression
from .root import Root
from .schemas import Discriminator, Schema
from .security import OAuthFlow, OAuthFlows, SecurityRequirement, SecurityScheme
from .servers import Server, ServerVariable
from .tag import Tag
from .xml import XML


def __init():
    r = {}
    CLASSES = [
        Components,
        Example,
        ExternalDocumentation,
        Reference,
        Contact,
        License,
        Info,
        Encoding,
        MediaType,
        Parameter,
        Header,
        RequestBody,
        Link,
        Response,
        Operation,
        PathItem,
        Paths,
        Callback,
        RuntimeExpression,
        Discriminator,
        Schema,
        OAuthFlow,
        OAuthFlows,
        SecurityScheme,
        SecurityRequirement,
        ServerVariable,
        Server,
        Tag,
        XML,
        Root,
    ]
    for i in CLASSES:
        r[i.__name__] = i
    for i in CLASSES:
        i.model_rebuild(_types_namespace=r)


__init()

__all__ = [
    "XML",
    "AsyncRequest",
    "Callback",
    "Components",
    "Contact",
    "Discriminator",
    "Encoding",
    "Example",
    "ExternalDocumentation",
    "Header",
    "Info",
    "License",
    "Link",
    "MediaType",
    "OAuthFlow",
    "OAuthFlows",
    "Operation",
    "Parameter",
    "PathItem",
    "Paths",
    "Reference",
    "Request",
    "RequestBody",
    "Response",
    "Root",
    "RuntimeExpression",
    "Schema",
    "SecurityRequirement",
    "SecurityScheme",
    "Server",
    "ServerVariable",
    "Tag",
]
