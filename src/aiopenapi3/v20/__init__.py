import pydantic_core

from .glue import Request, AsyncRequest

from .general import ExternalDocumentation, Reference
from .info import Contact, License, Info
from .parameter import Parameter, Header
from .paths import Response, Operation, PathItem, Paths
from .root import Root
from .schemas import Schema
from .security import SecurityScheme, SecurityRequirement
from .tag import Tag
from .xml import XML


def __init():
    r = dict()
    CLASSES = [
        ExternalDocumentation,
        Reference,
        Contact,
        License,
        Info,
        Parameter,
        Header,
        Response,
        Operation,
        PathItem,
        Paths,
        Schema,
        SecurityScheme,
        SecurityRequirement,
        Tag,
        XML,
        Root,
    ]
    for i in CLASSES:
        r[i.__name__] = i
    for i in CLASSES:
        i.model_rebuild(_types_namespace=r)


__init()
