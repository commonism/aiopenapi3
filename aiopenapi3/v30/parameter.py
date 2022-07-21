import enum
from typing import Union, Optional, Dict, Any

from pydantic import Field, root_validator

from ..base import ObjectExtended
from ..errors import ParameterFormatError

from .example import Example
from .general import Reference
from .schemas import Schema


class _ParameterFormatter:
    def _format(self, name, value):
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
        return self._format_value(name, value, explode, style)

    def _format_value(self, name, value, explode, style):
        f = getattr(self, f"_format__{style}")
        return f(name, value, explode)

    def _format__matrix(self, name, value, explode):
        """
        3.2.7.  Path-Style Parameter Expansion: {;var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.8
        """
        if self.schema_.type in frozenset(["string", "number", "bool", "integer"]):
            # ;color=blue
            if value:
                value = f";{name}={value}"
            else:
                value = f";{name}"
        elif self.schema_.type == "array":
            if explode is False:
                # ;color=blue,black,brown
                value = f";{name}={','.join(value)}"
            else:
                # ;color=blue;color=black;color=brown
                value = "".join([f";{name}={v}" for v in value])
        elif self.schema_.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            value = ",".join([f"{k},{v}" for k, v in values.items()])
            if explode is False:
                # ;color=R,100,G,200,B,150
                value = f";{name}={value}"
            else:
                # ;R=100;G=200;B=150
                value = f";{value}"
            pass
        return {name: value}

    def _format__label(self, name, value, explode):
        """
        3.2.5.  Label Expansion with Dot-Prefix: {.var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.8
        """
        if self.schema_.type in frozenset(["string", "number", "bool", "integer"]):
            # .blue
            if value:
                value = f".{value}"
            else:
                value = "."
        elif self.schema_.type == "array":
            # .blue.black.brown
            value = "." + ".".join(value)
        elif self.schema_.type == "object":

            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            if explode:
                # .R=100.G=200.B=150
                value = ".".join([f"{k}={v}" for k, v in values.items()])
            else:
                # .R.100.G.200.B.150
                value = ".".join([f"{k}.{v}" for k, v in values.items()])
            value = "." + value

        return {name: value}

    def _format__form(self, name, value, explode):
        """
        https://spec.openapis.org/oas/v3.1.0#style-examples

        3.2.8.  Form-Style Query Expansion: {?var}
        3.2.9.  Form-Style Query Continuation: {&var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.8
        """
        if self.schema_.type in frozenset(["string", "number", "bool", "integer"]):
            # color=blue
            return {name: value}
        elif self.schema_.type == "array":
            assert isinstance(value, (list, tuple))
            if explode is False:
                # color=blue,black,brown
                value = ",".join(map(str, value))
            else:
                # color=blue&color=black&color=brown
                pass
            return {name: value}
        elif self.schema_.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))

            if explode is False:
                # color=R,100,G,200,B,150
                value = ",".join([f"{k},{v}" for k, v in values.items()])
            else:
                # R=100&G=200&B=150
                return values
        return {name: value}

    def _format__simple(self, name, value, explode):
        """
        3.2.2.  Simple String Expansion: {var}

        https://www.rfc-editor.org/rfc/rfc6570#section-3.2.2
        """
        if value is None:
            return dict()

        if self.schema_.type in frozenset(["string", "number", "bool", "integer"]):
            return {name: value}
        elif self.schema_.type == "array":
            assert isinstance(value, (list, tuple))
            # blue,black,brown
            value = ",".join(map(str, value))
            return {name: value}
        elif self.schema_.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            if explode is False:
                # R,100,G,200,B,150
                value = ",".join([f"{k},{v}" for k, v in values.items()])
            else:
                # R=100,G=200,B=150
                value = ",".join([f"{k}={v}" for k, v in values.items()])
            return {name: value}

    def _format__spaceDelimited(self, name, value, explode):
        # blue%20black%20brown
        # R%20100%20G%20200%20B%20150
        return self._format__Delimited(" ", name, value, explode)

    def _format__pipeDelimited(self, name, value, explode):
        # blue|black|brown
        # R|100|G|200|B|150
        return self._format__Delimited("|", name, value, explode)

    def _format__Delimited(self, sep, name, value, explode):
        assert explode is False

        if value is None:
            return dict()

        if self.schema_.type == "array":
            value = sep.join(value)
        elif self.schema_.type == "object":
            values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
            value = sep.join([f"{k}{sep}{v}" for k, v in values.items()])
        return {name: value}

    def _format__deepObject(self, name, value, explode):
        assert self.schema_.type == "object" and explode is True

        if not value:
            return dict()

        values = value if isinstance(value, dict) else dict(value._iter(to_dict=True))
        # color[R]=100&color[G]=200&color[B]=150
        values = {f"{name}[{k}]": v for k, v in values.items()}
        return values


class ParameterBase(ObjectExtended):
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
    examples: Optional[Dict[str, Union["Example", Reference]]] = Field(default_factory=dict)

    content: Optional[Dict[str, "MediaType"]]

    @root_validator
    def validate_ParameterBase(cls, values):
        #        if values["in_"] ==
        #        if self.in_ == "path" and self.required is not True:
        #            err_msg = 'Parameter {} must be required since it is in the path'
        #            raise SpecError(err_msg.format(self.get_path()), path=self._path)
        return values


class _In(str, enum.Enum):
    query = "query"
    header = "header"
    path = "path"
    cookie = "cookie"


class Parameter(ParameterBase, _ParameterFormatter):
    name: str = Field(required=True)
    in_: _In = Field(required=True, alias="in")  # TODO must be one of ["query","header","path","cookie"]


class Header(ParameterBase, _ParameterFormatter):
    """

    .. _HeaderObject: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#header-object
    """

    def _format(self, name, value):
        style = self.style or "simple"
        explode = False
        return self._format_value(name, value, explode, style)


from .media import MediaType

Parameter.update_forward_refs()
Header.update_forward_refs()
