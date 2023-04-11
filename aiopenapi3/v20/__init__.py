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
        print(f"{i.__name__} {i.__pydantic_model_complete__}")
        #        if i in [Components, Callback]:
        #            continue
        try:
            i.model_rebuild(_localns=r)
        except pydantic_core.SchemaError as e:
            print(e)


__init()
