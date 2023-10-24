import enum
import datetime
import decimal
import typing
import uuid
from typing import Union, Optional, Dict, Any
from collections.abc import MutableMapping

from pydantic import Field, model_validator
import more_itertools

from ..base import ObjectExtended, ParameterBase as ParameterBase_, ReferenceBase
from ..errors import ParameterFormatError

from .example import Example
from .general import Reference
from .schemas import Schema

if typing.TYPE_CHECKING:
    from .paths import MediaType
    from .._types import v3xSchemaType


class _ParameterCodec:
    def _codec(self):
        if self.in_ == "path":
            style = self.style or "simple"
            assert style in frozenset(["matrix", "label", "simple"])
            explode = self.explode or False
        elif self.in_ == "header":
            style = self.style or "simple"
            assert style in frozenset(["simple"])
            explode = False
        elif self.in_ == "query":
            style = self.style or "form"
            assert style in frozenset(["form", "spaceDelimited", "pipeDelimited", "deepObject"])
            explode = self.explode if self.explode is not None else (False if style != "form" else True)
        elif self.in_ == "cookie":
            style = self.style or "form"
            assert style in frozenset(["form"])
            explode = self.explode if self.explode is not None else (False if style != "form" else True)
        else:
            raise ParameterFormatError(self)

        schema = self.schema_ or self.content.get("application/json").schema_
        if isinstance(schema, ReferenceBase):
            schema = schema._target

        return schema, style, explode

    def _encode(self, name: str, value):
        schema, style, explode = self._codec()
        return self._encode_value(name, value, schema, explode, style)

    def _encode_value(self, name: str, value, schema: "v3xSchemaType", explode: bool, style: str):
        f = getattr(self, f"_encode__{style}")
        return f(name, value, schema, explode)

    def _encode__matrix(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        """
        3.2.7.  Path-Style Parameter Expansion: {;var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.8
        """
        if schema.type in frozenset(["string", "number", "bool", "integer"]):
            # ;color=blue
            if value:
                value = f";{name}={value}"
            else:
                value = f";{name}"
        elif schema.type == "array":
            if explode is False:
                # ;color=blue,black,brown
                value = f";{name}={','.join(value)}"
            else:
                # ;color=blue;color=black;color=brown
                value = "".join([f";{name}={v}" for v in value])
        elif schema.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            value = ",".join([f"{k},{v}" for k, v in values.items()])
            if explode is False:
                # ;color=R,100,G,200,B,150
                value = f";{name}={value}"
            else:
                # ;R=100;G=200;B=150
                value = f";{value}"
        return {name: value}

    def _encode__label(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        """
        3.2.5.  Label Expansion with Dot-Prefix: {.var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.8
        """
        if schema.type in frozenset(["string", "number", "bool", "integer"]):
            # .blue
            if value:
                value = f".{value}"
            else:
                value = "."
        elif schema.type == "array":
            # .blue.black.brown
            value = "." + ".".join(value)
        elif schema.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            if explode:
                # .R=100.G=200.B=150
                value = ".".join([f"{k}={v}" for k, v in values.items()])
            else:
                # .R.100.G.200.B.150
                value = ".".join([f"{k}.{v}" for k, v in values.items()])
            value = "." + value

        return {name: value}

    def _encode__form(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        """
        https://spec.openapis.org/oas/v3.1.0#style-examples

        3.2.8.  Form-Style Query Expansion: {?var}
        3.2.9.  Form-Style Query Continuation: {&var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.8
        """
        if schema.type in frozenset(["string", "number", "bool", "integer"]):
            # color=blue
            return {name: value}
        elif schema.type == "array":
            assert isinstance(value, (list, tuple))
            if explode is False:
                # color=blue,black,brown
                value = ",".join(map(str, value))
            else:
                # color=blue&color=black&color=brown
                pass
            return {name: value}
        elif schema.type == "object":
            values = value if isinstance(value, dict) else value.model_dump()

            if explode is False:
                # color=R,100,G,200,B,150
                value = ",".join([f"{k},{v}" for k, v in values.items()])
            else:
                # R=100&G=200&B=150
                return values
        return {name: value}

    def _encode__simple(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        """
        3.2.2.  Simple String Expansion: {var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.2
        """
        if value is None:
            return dict()

        if schema.type in frozenset(["string", "number", "bool", "integer"]):
            return {name: value}
        elif schema.type == "array":
            assert isinstance(value, (list, tuple))
            # blue,black,brown
            value = ",".join(map(str, value))
            return {name: value}
        elif schema.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            if explode is False:
                # R,100,G,200,B,150
                value = ",".join([f"{k},{v}" for k, v in values.items()])
            else:
                # R=100,G=200,B=150
                value = ",".join([f"{k}={v}" for k, v in values.items()])
            return {name: value}

    def _encode__spaceDelimited(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        # blue%20black%20brown
        # R%20100%20G%20200%20B%20150
        return self._encode__Delimited(" ", name, value, schema, explode)

    def _encode__pipeDelimited(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        # blue|black|brown
        # R|100|G|200|B|150
        return self._encode__Delimited("|", name, value, schema, explode)

    def _encode__Delimited(self, sep: str, name: str, value, schema: "v3xSchemaType", explode: bool):
        assert explode is False

        if value is None:
            return dict()

        if schema.type == "array":
            value = sep.join(value)
        elif schema.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            value = sep.join([f"{k}{sep}{v}" for k, v in values.items()])
        return {name: value}

    def _encode__deepObject(self, name: str, value, schema: "v3xSchemaType", explode: bool):
        assert schema.type == "object" and explode is True

        if not value:
            return dict()

        values = value if isinstance(value, dict) else value.model_dump()
        # color[R]=100&color[G]=200&color[B]=150

        def _flatten_dict(data, key_):
            for k, v in data.items():
                key = f"{key_}[{k}]"
                if isinstance(v, MutableMapping):
                    yield from flatten_dict(v, key).items()
                else:
                    yield key, v

        def flatten_dict(d: MutableMapping, key: str = ""):
            return dict(_flatten_dict(d, key))

        values = {k: v for k, v in flatten_dict(values, name).items()}
        return values

    def _decode(self, value):
        schema, style, explode = self._codec()
        if style == "simple":
            return self._decode_simple(value, schema, explode)
        else:
            raise ValueError(f"style {style} can not be decoded")

    def _decode_simple(self, value, schema: "v3xSchemaType", explode: bool):
        if schema.type == "array":
            return value.split(",")
        elif schema.type == "object":
            if explode is False:
                # R,100,G,200,B,150
                return dict(more_itertools.chunked(value.split(","), 2))
            else:
                # R=100,G=200,B=150
                return dict(map(lambda y: (y[0], y[2]), map(lambda x: x.partition("="), value.split(","))))
        else:
            # convert basic type
            return value


class ParameterBase(ObjectExtended, ParameterBase_):
    """
    A `Parameter Object`_ defines a single operation parameter.

    .. _Parameter Object: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#external-documentation-object
    """

    description: Optional[str] = Field(default=None)
    required: Optional[bool] = Field(default=None)
    deprecated: Optional[bool] = Field(default=None)
    allowEmptyValue: Optional[bool] = Field(default=None)

    style: Optional[str] = Field(default=None)
    explode: Optional[bool] = Field(default=None)
    allowReserved: Optional[bool] = Field(default=None)
    schema_: Optional[Union[Schema, Reference]] = Field(default=None, alias="schema")
    example: Optional[Any] = Field(default=None)
    examples: Dict[str, Union["Example", Reference]] = Field(default_factory=dict)

    content: Dict[str, "MediaType"] = Field(default_factory=dict)


class _In(str, enum.Enum):
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"


class Parameter(ParameterBase, _ParameterCodec):
    name: str = Field()
    in_: _In = Field(alias="in")  # TODO must be one of ["query","header","path","cookie"]

    @model_validator(mode="after")
    def validate_Parameter(cls, p: "ParameterBase"):
        assert p.in_ != "path" or p.required is True, "Parameter '%s' must be required since it is in the path" % p.name
        return p


def encode_parameter(
    name: str,
    value: object,
    style: Optional[str],
    explode: Optional[bool],
    allowReserved: Optional[bool],
    in_: str,
    schema_: Schema,
) -> Union[str, bytes]:
    p = Parameter(name=name, style=style, explode=explode, allowReserved=allowReserved, **{"in": in_, "schema": None})
    p.schema_ = schema_
    r = p._encode(name, value)[name]
    if isinstance(r, (int, float, decimal.Decimal, datetime.datetime, datetime.date, datetime.time, uuid.UUID)):
        r = str(r)
    assert isinstance(r, (str, bytes))
    return r


class Header(ParameterBase, _ParameterCodec):
    """

    .. _HeaderObject: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#header-object
    """

    def _codec(self):
        schema = self.schema_ or self.content.get("application/json").schema_
        return schema, "simple", False
