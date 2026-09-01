import re
from collections.abc import Sequence
from typing import Literal, TypeAlias

import yaml
from httpx2._types import AuthTypes, FileTypes, RequestContent, RequestFiles
from pydantic import BaseModel

from . import v20, v30, v31, v32

RequestFileParameter = tuple[str, FileTypes]
RequestFilesParameter = Sequence[RequestFileParameter]

JSON: TypeAlias = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None
"""
Define a JSON type
https://github.com/python/typing/issues/182#issuecomment-1320974824
"""

RequestData = JSON | BaseModel | RequestFilesParameter
RequestParameter = str | BaseModel
RequestParameters = dict[str, RequestParameter]

RootType = v20.Root | v30.Root | v31.Root
ServerType = v30.Server | v31.Server
ReferenceType = v20.Reference | v30.Reference | v31.Reference
SchemaType = v20.Schema | v30.Schema | v31.Schema
v3xSchemaType = v30.Schema | v31.Schema
DiscriminatorType = v30.Discriminator | v31.Discriminator
PathItemType = v20.PathItem, v30.PathItem | v31.PathItem
OperationType = v20.Operation | v30.Operation | v31.Operation
ParameterType = v20.Parameter | v30.Parameter | v31.Parameter
HeaderType = v20.Header | v30.Header | v31.Header
RequestType = v20.Request | v30.Request
AsyncRequestType = v20.AsyncRequest | v30.AsyncRequest
MediaTypeType = v30.MediaType | v31.MediaType
ExpectedType = v20.Response | MediaTypeType
ResponseHeadersType = dict[str, str | BaseModel | list[BaseModel]]
ResponseDataType = BaseModel, bytes | str
TagType = v20.Tag | v30.Tag | v32.Tag

YAMLLoaderType = type[yaml.Loader] | type[yaml.CLoader] | type[yaml.SafeLoader] | type[yaml.CSafeLoader]

PrimitiveTypes = str | float | int | bool

HTTPMethodType = Literal["get", "put", "post", "delete", "options", "head", "patch", "trace"]
HTTPMethodMatchType = re.Pattern | HTTPMethodType

__all__: list[str] = [
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
