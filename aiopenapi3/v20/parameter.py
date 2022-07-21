import io
import enum
from typing import Union, Optional, Any

from pydantic import Field

from .general import Reference
from .schemas import Schema
from ..base import ObjectExtended, ObjectBase, ParameterBase
from ..errors import ParameterFormatError


class _ParameterFormatter:
    """
    Describing Parameters

    https://swagger.io/docs/specification/2-0/describing-parameters/
    """

    def _format__collection(self, values):
        sv = {"csv": ",", "ssv": " ", "tsv": "\t", "pipes": "|"}

        sep = sv.get(self.collectionFormat, None)
        if sep:
            if self.type == "array":
                values = [self.items._format(None, i) for i in values]
            return sep.join(map(str, values))
        elif self.collectionFormat == "multi":
            # foo=value&foo=another_value
            return values
        else:
            raise ParameterFormatError(self)

    def _format(self, name, value):
        if self.type == "array":
            value = self._format__collection(value)
        elif self.in_ == "formData":
            if self.type == "file":
                # https://www.python-httpx.org/quickstart/#sending-multipart-file-uploads
                assert type(value) == tuple and len(value) == 3 and isinstance(value[1], io.IOBase)

        return {name: value}


class Items(ObjectExtended, _ParameterFormatter):
    """
    https://swagger.io/specification/v2/#items-object
    """

    type: str = Field(...)
    format: Optional[str] = Field(default=None)
    items: Optional["Items"] = Field(default=None)
    collectionFormat: Optional[str] = Field(default=None)
    default: Any = Field(default=None)
    maximum: Optional[int] = Field(default=None)
    exclusiveMaximum: Optional[bool] = Field(default=None)
    minimum: Optional[int] = Field(default=None)
    exclusiveMinimum: Optional[bool] = Field(default=None)
    maxLength: Optional[int] = Field(default=None)
    minLength: Optional[int] = Field(default=None)
    pattern: Optional[str] = Field(default=None)
    maxItems: Optional[int] = Field(default=None)
    minItems: Optional[int] = Field(default=None)
    uniqueItems: Optional[bool] = Field(default=None)
    enum: Optional[Any] = Field(default=None)
    multipleOf: Optional[int] = Field(default=None)

    def _format(self, name, value):
        if self.type == "array":
            value = self._format__collection(value)

        return value


class Empty(ObjectExtended):
    pass


class _In(str, enum.Enum):
    query = "query"
    header = "header"
    path = "path"
    formData = "formData"
    body = "body"


class Parameter(ObjectExtended, _ParameterFormatter):
    """
    Describes a single operation parameter.

    .. _Parameter Object: https://swagger.io/specification/v2/#parameter-object
    """

    name: str = Field(required=True)
    in_: _In = Field(required=True, alias="in")

    description: Optional[str] = Field(default=None)
    required: Optional[bool] = Field(default=None)

    schema_: Optional[Union[Schema, Reference]] = Field(default=None, alias="schema")

    type: Optional[str] = Field(default=None)
    format: Optional[str] = Field(default=None)
    allowEmptyValue: Optional[bool] = Field(default=None)
    items: Optional[Union[Items, Empty]] = Field(default=None)
    collectionFormat: Optional[str] = Field(default=None)
    default: Any = Field(default=None)
    maximum: Optional[int] = Field(default=None)
    exclusiveMaximum: Optional[bool] = Field(default=None)
    minimum: Optional[int] = Field(default=None)
    exclusiveMinimum: Optional[bool] = Field(default=None)
    maxLength: Optional[int] = Field(default=None)
    minLength: Optional[int] = Field(default=None)
    pattern: Optional[str] = Field(default=None)
    maxItems: Optional[int] = Field(default=None)
    minItems: Optional[int] = Field(default=None)
    uniqueItems: Optional[bool] = Field(default=None)
    enum: Optional[Any] = Field(default=None)
    multipleOf: Optional[int] = Field(default=None)


class Header(ObjectExtended, _ParameterFormatter):
    """
    https://swagger.io/specification/v2/#header-object
    """

    description: Optional[str] = Field(default=None)

    type: str = Field(...)
    format: Optional[str] = Field(default=None)
    items: Optional[Items] = Field(default=None)
    collectionFormat: Optional[str] = Field(default=None)
    default: Any = Field(default=None)
    maximum: Optional[int] = Field(default=None)
    exclusiveMaximum: Optional[bool] = Field(default=None)
    minimum: Optional[int] = Field(default=None)
    exclusiveMinimum: Optional[bool] = Field(default=None)
    maxLength: Optional[int] = Field(default=None)
    minLength: Optional[int] = Field(default=None)
    pattern: Optional[str] = Field(default=None)
    maxItems: Optional[int] = Field(default=None)
    minItems: Optional[int] = Field(default=None)
    uniqueItems: Optional[bool] = Field(default=None)
    enum: Optional[Any] = Field(default=None)
    multipleOf: Optional[int] = Field(default=None)


Items.update_forward_refs()
