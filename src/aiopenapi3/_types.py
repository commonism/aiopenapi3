import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal, Optional, TypeAlias, Union

import yaml
from httpx2._types import AuthTypes, FileTypes, RequestContent, RequestFiles  # noqa
from pydantic import BaseModel

from . import v20, v30, v31, v32

if TYPE_CHECKING:
    pass


RequestFileParameter = tuple[str, FileTypes]
RequestFilesParameter = Sequence[RequestFileParameter]

JSON: TypeAlias = Optional[Union[dict[str, "JSON"], list["JSON"], str, int, float, bool]]
"""
Define a JSON type
https://github.com/python/typing/issues/182#issuecomment-1320974824
"""

RequestData = Union[JSON, BaseModel, RequestFilesParameter]
RequestParameter = Union[str, BaseModel]
RequestParameters = dict[str, RequestParameter]

RootType = Union[v20.Root, v30.Root, v31.Root]
ServerType = Union[v30.Server, v31.Server]
ReferenceType = Union[v20.Reference, v30.Reference, v31.Reference]
SchemaType = Union[v20.Schema, v30.Schema, v31.Schema]
v3xSchemaType = Union[v30.Schema, v31.Schema]
DiscriminatorType = Union[v30.Discriminator, v31.Discriminator]
PathItemType = Union[v20.PathItem, v30.PathItem, v31.PathItem]
OperationType = Union[v20.Operation, v30.Operation, v31.Operation]
ParameterType = Union[v20.Parameter, v30.Parameter, v31.Parameter]
HeaderType = Union[v20.Header, v30.Header, v31.Header]
RequestType = Union[v20.Request, v30.Request]
AsyncRequestType = Union[v20.AsyncRequest, v30.AsyncRequest]
MediaTypeType = Union[v30.MediaType, v31.MediaType]
ExpectedType = Union[v20.Response, MediaTypeType]
ResponseHeadersType = dict[str, Union[str, BaseModel, list[BaseModel]]]
ResponseDataType = Union[BaseModel, bytes, str]
TagType = Union[v20.Tag, v30.Tag, v32.Tag]

YAMLLoaderType = Union[type[yaml.Loader], type[yaml.CLoader], type[yaml.SafeLoader], type[yaml.CSafeLoader]]

PrimitiveTypes = Union[str, float, int, bool]

HTTPMethodType = Literal["get", "put", "post", "delete", "options", "head", "patch", "trace"]
HTTPMethodMatchType = Union[re.Pattern, HTTPMethodType]

__all__: list[str] = [
    # end httpx
    "JSON",
    "AuthTypes",
    "DiscriminatorType",
    "ExpectedType",
    "HTTPMethodMatchType",
    "HTTPMethodType",
    "HeaderType",
    "MediaTypeType",
    "OperationType",
    "ParameterType",
    "PathItemType",
    "PrimitiveTypes",
    "ReferenceType",
    # httpx forwards
    "RequestContent",
    "RequestData",
    "RequestFileParameter",
    "RequestFiles",
    "RequestFilesParameter",
    "RequestParameters",
    "RequestType",
    "ResponseDataType",
    "ResponseHeadersType",
    "RootType",
    "SchemaType",
    "ServerType",
    "TagType",
    "YAMLLoaderType",
    "v3xSchemaType",
]
