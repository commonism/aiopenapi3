import re
from typing import TYPE_CHECKING, Dict, List, Sequence, Tuple, Union, TypeAlias, Type, Optional, Literal

import yaml

from httpx._types import RequestContent, FileTypes, RequestFiles, AuthTypes  # noqa
from pydantic import BaseModel


from . import v20, v30, v31

if TYPE_CHECKING:
    pass


RequestFileParameter = Tuple[str, FileTypes]
RequestFilesParameter = Sequence[RequestFileParameter]

JSON: TypeAlias = Optional[Union[dict[str, "JSON"], list["JSON"], str, int, float, bool]]
"""
Define a JSON type
https://github.com/python/typing/issues/182#issuecomment-1320974824
"""

RequestData = Union[JSON, BaseModel, RequestFilesParameter]
RequestParameter = Union[str, BaseModel]
RequestParameters = Dict[str, RequestParameter]

RootType = Union[v20.Root, v30.Root, v31.Root]
ServerType = Union[v30.Server, v31.Server]
ReferenceType = Union[v20.Reference, v30.Reference, v31.Reference]
SchemaType = Union[v20.Schema, v30.Schema, v31.Schema]
v3xSchemaType = Union[v30.Schema, v31.Schema]
DiscriminatorType = Union[v30.Discriminator, v31.Discriminator]
PathItemType = Union[v20.PathItem, v30.PathItem, v31.PathItem]
OperationType = Union[v20.Operation, v30.Operation, v31.Operation]
ParameterType = Union[v20.Parameter, v30.Parameter, v31.Parameter]
HeaderType = Union[v30.Header, v30.Header, v31.Header]
RequestType = Union[v20.Request, v30.Request]
MediaTypeType = Union[v30.MediaType, v31.MediaType]
ExpectedType = Union[v20.Response, MediaTypeType]
ResponseHeadersType = Dict[str, str]
ResponseDataType = Union[BaseModel, bytes, str]


YAMLLoaderType = Union[Type[yaml.Loader], Type[yaml.CLoader], Type[yaml.SafeLoader], Type[yaml.CSafeLoader]]

PrimitiveTypes = Union[str, float, int, bool]

HTTPMethodType = Literal["get", "put", "post", "delete", "options", "head", "patch", "trace"]
HTTPMethodMatchType = Union[re.Pattern, HTTPMethodType]

__all__: List[str] = [
    "RootType",
    "ServerType",
    "SchemaType",
    "v3xSchemaType",
    "DiscriminatorType",
    "PathItemType",
    "OperationType",
    "ParameterType",
    "HeaderType",
    "RequestType",
    "ExpectedType",
    "MediaTypeType",
    "ResponseHeadersType",
    "ResponseDataType",
    "RequestData",
    "RequestParameters",
    "ReferenceType",
    "PrimitiveTypes",
    #
    "YAMLLoaderType",
    # httpx forwards
    "RequestContent",
    "RequestFiles",
    "AuthTypes",
    #
    "JSON",
    "RequestFilesParameter",
    "RequestFileParameter",
    "HTTPMethodType",
    "HTTPMethodMatchType",
]
