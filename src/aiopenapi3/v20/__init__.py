from .general import ExternalDocumentation, Reference
from .glue import AsyncRequest, Request
from .info import Contact, Info, License
from .parameter import Header, Parameter
from .paths import Operation, PathItem, Paths, Response
from .root import Root
from .schemas import Schema
from .security import SecurityRequirement, SecurityScheme
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

__all__ = [
    "XML",
    "AsyncRequest",
    "Contact",
    "ExternalDocumentation",
    "Header",
    "Info",
    "License",
    "Operation",
    "Parameter",
    "PathItem",
    "Paths",
    "Reference",
    "Request",
    "Response",
    "Root",
    "Schema",
    "SecurityRequirement",
    "SecurityScheme",
    "Tag",
]
