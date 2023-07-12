import pydantic_core

from .components import Components
from .example import Example
from .general import ExternalDocumentation, Reference
from .info import Contact, License, Info
from .media import Encoding, MediaType
from .parameter import Parameter, Header
from .paths import RequestBody, Link, Response, Operation, PathItem, Paths, Callback, RuntimeExpression
from .root import Root
from .schemas import Discriminator, Schema
from .security import OAuthFlow, OAuthFlows, SecurityScheme, SecurityRequirement
from .servers import ServerVariable, Server
from .tag import Tag
from .xml import XML


def __init():
    r = dict()
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
