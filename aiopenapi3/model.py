import collections
import dataclasses
import logging
import re
import sys
from typing import Any, Set, Type, cast, TypeVar
import typing

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

if sys.version_info >= (3, 9):
    from typing import List, Optional, Union, Tuple, Dict, Annotated, Literal
else:
    from typing import List, Optional, Union, Tuple, Dict
    from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Field, RootModel, ConfigDict
import pydantic

from .base import ReferenceBase, SchemaBase
from . import me
from .pydanticv2 import field_class_to_schema

if typing.TYPE_CHECKING:
    from .base import DiscriminatorBase
    from ._types import SchemaType, ReferenceType, PrimitiveTypes, DiscriminatorType

type_format_to_class: Dict[str, Dict[str, Type]] = collections.defaultdict(lambda: dict())

log = logging.getLogger("aiopenapi3.model")

SCHEMA_TYPES_MAP = {
    "string": str,
    "number": float,
    "boolean": bool,
    "integer": int,
    "null": None.__class__,
    "object": SchemaBase,
    "array": list,
}
TYPES_SCHEMA_MAP = {v: k for k, v in SCHEMA_TYPES_MAP.items()}
SCHEMA_TYPES = frozenset(SCHEMA_TYPES_MAP.keys())


def generate_type_format_to_class():
    """
    initialize type_format_to_class
    :return: None
    """
    global type_format_to_class
    for cls, spec in field_class_to_schema:
        if "type" not in spec:
            # FIXME Decimal is anyOf now
            continue
        if spec["type"] not in frozenset(["string", "number"]):
            continue
        type_format_to_class[spec["type"]][spec.get("format", None)] = cls
    from pydantic import Base64Str

    type_format_to_class["string"]["byte"] = Base64Str


def class_from_schema(s, _type):
    a = type_format_to_class[_type]
    b = a.get(s.format, a[None])
    return b


@dataclasses.dataclass
class _ClassInfo:
    @dataclasses.dataclass
    class _PropertyInfo:
        annotation: Any = None
        default: Any = None

    root: Any = None
    config: Dict[str, Any] = dataclasses.field(default_factory=dict)
    properties: Dict[str, _PropertyInfo] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(lambda: _ClassInfo._PropertyInfo())
    )

    def validate(self):
        report = list(filter(lambda i: not (i[1].annotation or i[0].startswith("aio3_")), self.properties.items()))
        assert len(report) == 0, report

    @property
    def fields(self):
        r = list()
        for k, v in self.properties.items():
            r.append((k, (v.annotation, v.default)))
        return dict(r)


_T = TypeVar("_T")


def _follow(r: "ReferenceType", t: Type[_T]) -> TypeGuard[_T]:
    assert isinstance(r, ReferenceBase)
    if isinstance(r._target, t):
        return r._target
    assert r._target
    return _follow(r._target, t)


class Model:  # (BaseModel):
    ALIASES: Dict[str, str] = dict()

    @classmethod
    def from_schema(
        cls,
        schema: "SchemaType",
        schemanames: Optional[List[str]] = None,
        discriminators: Optional[List["DiscriminatorType"]] = None,
        extra: Optional["SchemaType"] = None,
    ) -> Type[BaseModel]:
        if schemanames is None:
            schemanames = []

        if discriminators is None:
            discriminators = []

        r: List[Type[BaseModel]] = list()

        for _type in Model.types(schema):
            r.append(Model.from_schema_type(schema, _type, schemanames, discriminators, extra))

        if len(r) > 1:
            ru: object = Union[tuple(r)]
            type_name = schema._get_identity("L8")
            m: Type[RootModel] = pydantic.create_model(type_name, __base__=(RootModel[ru],), __module__=me.__name__)
        elif len(r) == 1:
            m: Type[BaseModel] = cast(Type[BaseModel], r[0])
        else:  # == 0
            raise ValueError(r)
        return cast(Type[BaseModel], m)

    @classmethod
    def from_schema_type(
        cls,
        schema: "SchemaType",
        _type: str,
        schemanames: List[str],
        discriminators: List["DiscriminatorType"],
        extra: Optional["SchemaType"],
    ) -> Type[BaseModel]:
        from . import v20, v30, v31

        type_name = schema._get_identity("L8")  # + f"_{type}"

        classinfo = _ClassInfo()

        # do not create models for primitive types
        if _type in ("string", "integer", "number", "boolean"):
            if _type == "boolean":
                return bool

            if typing.get_origin((_t := Model.typeof(schema, _type=_type))) != Literal:
                classinfo.root = Annotated[_t, Model.fieldof_args(schema, None)]
            else:
                classinfo.root = _t
        elif _type == "object":
            # this is a anyOf/oneOf - the parent may have properties which will collide with __root__
            # so - add the parent properties to this model
            if extra:
                Model.annotationsof(extra, discriminators, schemanames, classinfo)
                Model.fieldof(extra, classinfo)

            if hasattr(schema, "anyOf") and schema.anyOf:
                assert all(schema.anyOf)
                assert isinstance(schema, (v30.Schema, v31.Schema))
                t = tuple(
                    i.get_type(
                        names=schemanames + ([cast(str, i.ref)] if isinstance(i, ReferenceBase) else []),
                        discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                        extra=schema if schema.properties else None,
                    )
                    for i in schema.anyOf
                )
                if schema.discriminator and schema.discriminator.mapping:
                    classinfo.root = Annotated[
                        Union[t], Field(discriminator=Model.nameof(schema.discriminator.propertyName))
                    ]
                else:
                    classinfo.root = Union[t]
            elif hasattr(schema, "oneOf") and schema.oneOf:
                assert isinstance(schema, (v30.Schema, v31.Schema))
                t = tuple(
                    i.get_type(
                        names=schemanames + ([cast(str, i.ref)] if isinstance(i, ReferenceBase) else []),
                        discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                        extra=schema if schema.properties else None,
                    )
                    for i in schema.oneOf
                )
                if schema.discriminator and schema.discriminator.mapping:
                    classinfo.root = Annotated[
                        Union[t], Field(discriminator=Model.nameof(schema.discriminator.propertyName))
                    ]
                else:
                    classinfo.root = Union[t]
            else:
                # default schema properties …
                Model.annotationsof_type(schema, _type, discriminators, schemanames, classinfo, fwdref=True)
                Model.fieldof(schema, classinfo)
                if "patternProperties" in schema.model_fields_set:

                    def mkx():
                        def get_patternProperty(self_, item):
                            patterns = typing.get_args(self_.aio3_patternProperty.__annotations__["item"])

                            for name, value in self_.model_extra.items():
                                if re.match(item, name):
                                    yield name, value

                        get_patternProperty.__annotations__["item"] = Literal[
                            tuple(sorted(schema.patternProperties.keys()))
                        ]
                        return get_patternProperty

                    classinfo.properties["aio3_patternProperty"].default = mkx()

                    def mkx():
                        def get_patternProperties(self_):
                            patterns = typing.get_args(self_.aio3_patternProperty.__annotations__["item"])
                            r = {k: list() for k in patterns}
                            for name, value in self_.model_extra.items():
                                for pattern in patterns:
                                    if re.match(pattern, name):
                                        r[pattern].append((name, value))
                                        break
                                    else:
                                        # unmatched …
                                        pass
                            return r

                        return get_patternProperties

                    classinfo.properties["aio3_patternProperties"].default = property(mkx())

                if schema.allOf:
                    for i in schema.allOf:
                        Model.annotationsof(i, discriminators, schemanames, classinfo, fwdref=True)
                        Model.fieldof(i, classinfo)

        elif _type == "array":
            classinfo.root = Model.typeof(schema, _type="array")

        if _type in ("array", "object"):
            if schema.enum or getattr(schema, "const", None):
                raise NotImplementedError("complex enums/const are not supported")

        classinfo.config = Model.configof(schema)

        if classinfo.config["extra"] == "allow" and classinfo.root is None:

            def mkx():
                def get_additionalProperties(x):
                    return x.model_extra

                return get_additionalProperties, None, None

            classinfo.properties["aio3_additionalProperties"].default = property(mkx()[0])

        classinfo.validate()
        if classinfo.root:
            m = pydantic.create_model(type_name, __base__=(RootModel[classinfo.root],), __module__=me.__name__)
        else:
            m = pydantic.create_model(
                type_name,
                #                __base__=(BaseModel,),
                __module__=me.__name__,
                model_config=classinfo.config,
                **classinfo.fields,
            )
        return cast(Type[BaseModel], m)

    @staticmethod
    def configof(schema: "SchemaType"):
        """
        create pydantic model_config for the BaseModel
        we need to set "extra" - "allow" is not an option though …

        "allow" is a problem
          * overwriting class attributes/members/methods
          * pydantic type identification does not work reliable due to missing rejects,

        """
        from . import v20, v30, v31

        arbitrary_types_allowed_ = False
        extra_ = "allow"

        if schema.additionalProperties is not None:
            if isinstance(schema.additionalProperties, bool):
                if not schema.additionalProperties:
                    extra_ = "forbid"
                else:
                    arbitrary_types_allowed_ = True
            elif isinstance(schema.additionalProperties, (SchemaBase, ReferenceBase)):
                """
                we allow arbitrary types if additionalProperties has no properties
                """
                assert schema.additionalProperties.properties is not None
                if len(schema.additionalProperties.properties) == 0:
                    arbitrary_types_allowed_ = True
            else:
                raise TypeError(schema.additionalProperties)

        if getattr(schema, "patternProperties", None):
            extra_ = "allow"

        return ConfigDict(
            extra=extra_,
            arbitrary_types_allowed=arbitrary_types_allowed_,
            # validate_assignment=True
        )

    @staticmethod
    def typeof(
        schema: Optional[Union["SchemaType", "ReferenceType"]], _type: Optional[str] = None, fwdref: bool = False
    ) -> Type:
        if schema is None:
            return BaseModel
        if isinstance(schema, SchemaBase):
            nullable = False
            schema = cast("SchemaType", schema)
            """
            Required, can be None: Optional[str]
            Not required, can be None, is … by default: f4: Optional[str] = …
            """
            r: List[Type] = list()
            rr: Type
            if (v := getattr(schema, "const", None)) is not None:
                """
                const - is not nullable
                """
                r = [Literal[cast(str, v)]]  # type: ignore[assignment,list-item]
                nullable = False
            elif schema.enum:
                if None in (_names := tuple(schema.enum)):
                    nullable = True
                    _names = tuple(filter(lambda x: x, _names))
                r = [Literal[_names]]  # type: ignore[assignment,list-item]
            else:
                for _type in Model.types(schema) if not _type else [_type]:
                    if _type == "integer":
                        r.append(int)
                    elif _type == "number":
                        r.append(class_from_schema(schema, "number"))
                    elif _type == "string":
                        v = class_from_schema(schema, "string")
                        r.append(v)
                    elif _type == "boolean":
                        r.append(bool)
                    elif _type == "array":
                        if isinstance(schema.items, list):
                            v = Tuple[tuple(Model.typeof(i, fwdref=True) for i in schema.items)]
                        elif schema.items:
                            if isinstance(schema.items, ReferenceBase) and schema.items._target == schema:
                                """
                                self referencing array
                                """
                                v = List[schema.get_type(fwdref=True)]  # type: ignore[misc,index]
                            else:
                                v = List[Model.typeof(schema.items, fwdref=True)]  # type: ignore[misc,index]
                        elif schema.items is None:
                            continue
                        else:
                            raise TypeError(schema.items)
                        r.append(v)
                    elif _type == "object":
                        r.append(schema.get_type(fwdref=fwdref))
                    elif _type == "null":
                        nullable = True
                    else:
                        raise ValueError(_type)

            if len(r) == 1:
                rr = r[0]
            elif len(r) > 1:
                rr = Union[tuple(r)]  # type: ignore[arg-type]
            else:
                rr = None  # type: ignore[assignment]
            if nullable is True:
                rr = Optional[rr]
        elif isinstance(schema, ReferenceBase):
            rr = Model.typeof(schema._target, fwdref=True)
        else:
            raise TypeError(type(schema))
        return rr

    @staticmethod
    def annotationsof(
        schema: "SchemaType",
        discriminators: List["DiscriminatorType"],
        shmanm: List[str],
        classinfo: _ClassInfo,
        fwdref=False,
    ):
        if isinstance(schema.type, list):
            classinfo.root = Model.typeof(schema)
        elif schema.type is None:
            if schema.properties:
                return Model.annotationsof_type(schema, "object", discriminators, shmanm, classinfo, fwdref)
            elif schema.items:
                return Model.annotationsof_type(schema, "array", discriminators, shmanm, classinfo, fwdref)
        else:
            return Model.annotationsof_type(schema, schema.type, discriminators, shmanm, classinfo, fwdref)
        return classinfo

    @staticmethod
    def annotationsof_type(
        schema: "SchemaType", _type: str, discriminators, shmanm, classinfo: _ClassInfo, fwdref=False
    ):
        if _type == "array":
            v = Model.typeof(schema)
            if Model.is_nullable(schema):
                v = Optional[v]  # type: ignore[assignment]
            classinfo.root = v
        elif _type == "object":
            if (
                schema.additionalProperties
                and isinstance(schema.additionalProperties, (SchemaBase, ReferenceBase))
                and not schema.properties
            ):
                """
                https://swagger.io/docs/specification/data-models/dictionaries/

                For example, a string-to-string dictionary like this:

                    {
                      "en": "English",
                      "fr": "French"
                    }

                is defined using the following schema:

                    type: object
                    additionalProperties:
                      type: string
                """
                v = Dict[str, Model.typeof(schema.additionalProperties)]  # type: ignore[misc,index]
                if Model.is_nullable(schema):
                    v = Optional[v]  # type: ignore[assignment]
                classinfo.root = v
            else:
                assert schema.properties is not None
                for name, f in schema.properties.items():
                    canbenull = True
                    r = Model.typeof(f, fwdref=fwdref)
                    if typing.get_origin(r) == Literal:
                        canbenull = False

                    if canbenull:
                        if getattr(f, "const", None) is None:
                            """not const"""
                            if name not in schema.required or Model.is_nullable(f):
                                """not required - or nullable"""
                                r = Optional[r]  # type: ignore[assignment]

                    classinfo.properties[Model.nameof(name)].annotation = r

        elif _type in ("string", "integer", "boolean", "number"):
            pass
        else:
            raise ValueError()
        return classinfo

    @staticmethod
    def types(schema: "SchemaType"):
        if isinstance(schema.type, str):
            yield schema.type
        else:
            typesfilter: Set[str] = set()
            values: Set[str]
            if isinstance(schema.type, list):
                values = set(schema.type)
            elif schema.type is None:
                values = set(SCHEMA_TYPES)
                typesfilter = set()

                if (const := getattr(schema, "const", None)) is not None:
                    typesfilter.add(cast(str, TYPES_SCHEMA_MAP.get(type(const))))

                if enum := getattr(schema, "enum", None):
                    typesfilter |= set([cast(str, TYPES_SCHEMA_MAP.get(type(i))) for i in enum])

                """
                anyOf / oneOf / allOf do not need to be of type object
                but the type of their children can be used to limit the type of the parent
                """

                totalOf: List["SchemaType"]
                if totalOf := sum([getattr(schema, i, []) for i in ["anyOf", "allOf", "oneOf"]], []):
                    tmp = set.union(*[set(Model.types(x)) for x in totalOf])
                    typesfilter |= tmp
            #                    typesfilter.add("object")

            #                if (v:=getattr(schema, "items", None)) is None and "array" not in typesfilter:
            #                    values.discard("array")
            else:
                raise StopIteration

            if typesfilter:
                values = values & typesfilter

            for i in values:
                yield i

    @staticmethod
    def is_type(schema: "SchemaType", type_) -> bool:
        return isinstance(schema.type, str) and schema.type == type_ or Model.or_type(schema, type_, l=None)

    @staticmethod
    def or_type(schema: "SchemaType", type_: str, l: Optional[int] = 2) -> bool:
        return isinstance((t := schema.type), list) and (l is None or len(t) == l) and type_ in t

    @staticmethod
    def is_nullable(schema: "SchemaType") -> bool:
        return Model.or_type(schema, "null", l=None) or getattr(schema, "nullable", False)

    @staticmethod
    def is_type_any(schema: "SchemaType"):
        return schema.type is None

    @staticmethod
    def fieldof(schema: "SchemaType", classinfo: _ClassInfo):
        if schema.type == "array":
            return classinfo

        if Model.is_type(schema, "object") or Model.is_type_any(schema):
            f: Union[SchemaBase, ReferenceBase]
            assert schema.properties is not None
            for name, f in schema.properties.items():
                args: Dict[str, Any] = dict()
                assert schema.required is not None
                if name not in schema.required:
                    args["default"] = None
                name = Model.nameof(name, args=args)
                if Model.is_nullable(f):
                    args["default"] = None
                for i in ["default"]:
                    if (v := getattr(f, i, None)) is not None:
                        args[i] = v
                classinfo.properties[name].default = Model.fieldof_args(f, args)
        else:
            raise ValueError(schema.type)
        return classinfo

    @staticmethod
    def fieldof_args(schema: "SchemaType", args=None):
        if args is None:
            args = dict(default=getattr(schema, "default", None))

        # """
        # readOnly & writeOnly are Optional default None
        # """
        # if (v:= (getattr(schema,"readOnly", None) or getattr(schema,"writeOnly", None))) is not None:
        #     if "default" not in args:
        #         args["default"] = None

        if Model.is_type(schema, "integer") or Model.is_type(schema, "number"):
            """
            https://docs.pydantic.dev/latest/usage/fields/#numeric-constraints
            """
            from . import v20, v30, v31

            if isinstance(schema, (v20.Schema, v30.Schema)):
                mof: Tuple[str, str] = ("multipleOf", "multiple_of")
                if (v := getattr(schema, mof[0], None)) is not None:
                    args[mof[1]] = v

                mum: List[Tuple[str, str, str, str]] = [
                    ("maximum", "exclusiveMaximum", "le", "lt"),
                    ("minimum", "exclusiveMinimum", "ge", "gt"),
                ]
                for v0, v1, t0, t1 in mum:
                    if v := getattr(schema, v0):
                        if getattr(schema, v1, False):  # exclusive
                            args[t1] = v
                        else:
                            args[t0] = v
            elif isinstance(schema, v31.Schema):
                for k, m in {
                    "multipleOf": "multiple_of",
                    "exclusiveMaximum": "lt",
                    "maximum": "le",
                    "exclusiveMinimum": "gt",
                    "minimum": "ge",
                }.items():
                    if (v := getattr(schema, k, None)) is not None:
                        args[m] = v
        if Model.is_type(schema, "string"):
            """
            https://docs.pydantic.dev/latest/usage/fields/#string-constraints
            """

            if (v := getattr(schema, "maxLength", None)) is not None:
                args["max_length"] = v

            if (v := getattr(schema, "minLength", None)) is not None:
                args["min_length"] = v
        return Field(**args)

    @staticmethod
    def nameof(name: str, args=None):
        """
        fixes

        Field name "validate" shadows a BaseModel attribute; use a different field name with "alias='validate'".

        :param name:
        :param args:
        :return:
        """

        if len(name) == 0:
            # FIXME
            #  are empty property names valid?
            raise ValueError("empty property name")

        if getattr(BaseModel, name, None):
            rename = f"{name}_"
        else:
            rename = Model.ALIASES.get(name, name)

        if name.startswith("model_"):
            rename = f"x{name}"

        try:
            rename = re.sub(r"[#@\.-]", "_", rename)
        except Exception as e:
            print(e)

        if rename[0] == "_":
            rename = rename.lstrip("_") + "_"

        if rename != name:
            if args is not None:
                args["alias"] = name
            return rename
        return name


if len(type_format_to_class) == 0:
    generate_type_format_to_class()
