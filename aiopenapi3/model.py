import collections
import dataclasses
import inspect
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

from pydantic import BaseModel, TypeAdapter, Field, RootModel, ConfigDict
import pydantic

from .base import ReferenceBase, SchemaBase
from . import me
from .pydanticv2 import field_class_to_schema

if typing.TYPE_CHECKING:
    from .base import DiscriminatorBase
    from ._types import SchemaType, ReferenceType, PrimitiveTypes, DiscriminatorType

type_format_to_class: Dict[str, Dict[str, Type]] = collections.defaultdict(dict)

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
    if _type == "integer":
        return int
    elif _type == "boolean":
        return bool
    a = type_format_to_class[_type]
    b = a.get(s.format, a[None])
    return b


import pydantic_core


class ConfiguredRootModel(RootModel):
    model_config = dict(regex_engine="python-re")


@dataclasses.dataclass
class _ClassInfo:
    @dataclasses.dataclass
    class _PropertyInfo:
        annotation: Any = None
        default: Any = pydantic_core.PydanticUndefined

    name: str
    type_: str

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

    def createFields(self, schema: "SchemaType", overwrite=False):
        if schema.type == "array":
            return

        if Model.is_type(schema, "object") or Model.is_type_any(schema):
            f: Union[SchemaBase, ReferenceBase]
            assert schema.properties is not None
            for name, f in schema.properties.items():
                if (
                    overwrite is False
                    and self.properties[Model.nameof(name)].default != pydantic_core.PydanticUndefined
                ):
                    continue

                args: Dict[str, Any] = dict()
                assert schema.required is not None
                if (v := getattr(f, "default", None)) is not None:
                    args["default"] = v
                elif name not in schema.required:
                    args["default"] = None

                name = Model.nameof(name, args=args)
                self.properties[name].default = Model.createField(f, None, args)
        else:
            raise ValueError(schema.type)
        return

    def createAnnotations(
        self,
        schema: "SchemaType",
        discriminators: List["DiscriminatorType"],
        shmanm: List[str],
        fwdref=False,
        overwrite=False,
    ):
        if isinstance(schema.type, list):
            self.root = Model.createAnnotation(schema)
        elif schema.type is None:
            if schema.properties:
                return self._createAnnotations(schema, "object", discriminators, shmanm, fwdref, overwrite)
            elif schema.items:
                return self._createAnnotations(schema, "array", discriminators, shmanm, fwdref)
        else:
            return self._createAnnotations(schema, schema.type, discriminators, shmanm, fwdref)
        return

    def _createAnnotations(
        self, schema: "SchemaType", _type: str, discriminators, shmanm, fwdref=False, overwrite=False
    ):
        if _type == "array":
            v = Model.createAnnotation(schema)
            if Model.is_nullable(schema):
                v = Optional[v]  # type: ignore[assignment]
            self.root = v
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
                v = Dict[str, Model.createAnnotation(schema.additionalProperties)]  # type: ignore[misc,index]
                if Model.is_nullable(schema):
                    v = Optional[v]  # type: ignore[assignment]
                self.root = v
            else:
                assert schema.properties is not None
                for name, f in schema.properties.items():
                    if overwrite is False and self.properties[Model.nameof(name)].annotation is not None:
                        continue

                    canbenull = True
                    r = Model.createAnnotation(f, fwdref=fwdref)
                    if typing.get_origin(r) == Literal:
                        canbenull = False

                    if canbenull:
                        if getattr(f, "const", None) is None:
                            """not const"""
                            if name not in schema.required or Model.is_nullable(f):
                                """not required - or nullable"""
                                r = Optional[r]  # type: ignore[assignment]

                    self.properties[Model.nameof(name)].annotation = r

        elif _type in ("string", "integer", "boolean", "number"):
            pass
        else:
            raise ValueError()
        return

    def model(self) -> Union[Type[BaseModel], Type[None]]:
        if self.root:
            m = self.root
        else:
            if self.type_ == "object":
                m = pydantic.create_model(
                    self.name,
                    __module__=me.__name__,
                    model_config=self.config,
                    **self.fields,
                )
            else:
                m = None.__class__
        return m

    @classmethod
    def collapse(cls, type_name, items: List["_ClassInfo"]) -> Type[BaseModel]:
        r: List[Union[Type[BaseModel], Type[None]]]

        r = [i.model() for i in items]

        if len(r) > 1:
            ru: object = Union[tuple(r)]
            m: Type[RootModel] = pydantic.create_model(
                type_name, __base__=(ConfiguredRootModel[ru],), __module__=me.__name__
            )
        elif len(r) == 1:
            m: Type[BaseModel] = cast(Type[BaseModel], r[0])
            if not (inspect.isclass(m) and issubclass(m, pydantic.BaseModel)):
                m = pydantic.create_model(type_name, __base__=(ConfiguredRootModel[m],), __module__=me.__name__)
        else:  # == 0
            assert len(r), r
        return m


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
        extra: Optional[List["SchemaType"]] = None,
    ) -> Type[BaseModel]:
        if schemanames is None:
            schemanames = []

        if discriminators is None:
            discriminators = []

        r: List[_ClassInfo] = list()

        for _type in Model.types(schema):
            r.append(Model.createClassInfo(schema, _type, schemanames, discriminators, extra))

        m = _ClassInfo.collapse(schema._get_identity("L8"), r)

        return cast(Type[BaseModel], m)

    @classmethod
    def createClassInfo(
        cls,
        schema: "SchemaType",
        _type: str,
        schemanames: List[str],
        discriminators: List["DiscriminatorType"],
        extra: Optional[List["SchemaType"]],
    ) -> _ClassInfo:
        from . import v20, v30, v31

        type_name = schema._get_identity("L8")  # + f"_{type}"

        classinfo = _ClassInfo(type_name, _type)

        # create models for primitive types to be nullable
        if _type in ("string", "integer", "number", "boolean"):
            """
            for primitive types the anyOf/oneOf is taken care of in Model.createAnnotation
            """
            if typing.get_origin(_t := Model.createAnnotation(schema, _type=_type)) != Literal:
                classinfo.root = Annotated[_t, Model.createField(schema, _type=_type, args=None)]
            else:
                classinfo.root = _t
        elif _type == "array":
            """anyOf/oneOf is taken care in in createAnnotation"""
            classinfo.root = Model.createAnnotation(schema, _type="array")
        elif _type == "null":
            classinfo.root = None.__class__
        elif _type == "object":
            # this is a anyOf/oneOf - the parent may have properties which will collide with __root__
            # so - add the parent properties to this model
            if extra:
                for exi in extra:
                    classinfo.createAnnotations(exi, discriminators, schemanames)
                    classinfo.createFields(exi)

            if hasattr(schema, "anyOf") and schema.anyOf:
                assert all(schema.anyOf)
                assert isinstance(schema, (v30.Schema, v31.Schema))
                t = tuple(
                    i.get_type(
                        names=schemanames + ([cast(str, i.ref)] if isinstance(i, ReferenceBase) else []),
                        discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                        extra=[schema] if schema.properties else [] + schema.allOf,
                    )
                    for i in schema.anyOf
                    if _type in Model.types(i)
                )
                if schema.discriminator and schema.discriminator.mapping:
                    classinfo.root = Annotated[
                        Union[t], Field(discriminator=Model.nameof(schema.discriminator.propertyName))
                    ]
                else:
                    if len(t):
                        classinfo.root = Union[t]
            elif hasattr(schema, "oneOf") and schema.oneOf:
                assert isinstance(schema, (v30.Schema, v31.Schema))
                t = tuple(
                    i.get_type(
                        names=schemanames + ([cast(str, i.ref)] if isinstance(i, ReferenceBase) else []),
                        discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                        extra=[schema] if schema.properties else [] + schema.allOf,
                    )
                    for i in schema.oneOf
                    if _type in Model.types(i)
                )
                if schema.discriminator and schema.discriminator.mapping:
                    classinfo.root = Annotated[
                        Union[t], Field(discriminator=Model.nameof(schema.discriminator.propertyName))
                    ]
                else:
                    if len(t):
                        classinfo.root = Union[t]
            else:
                # default schema properties …
                classinfo._createAnnotations(schema, _type, discriminators, schemanames, fwdref=True, overwrite=True)
                classinfo.createFields(schema, overwrite=True)
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

                    if not schema.additionalProperties:

                        def mkx():
                            def validate_patternProperties(self_):
                                patterns = typing.get_args(self_.aio3_patternProperty.__annotations__["item"])
                                for name, value in self_.model_extra.items():
                                    for pattern in patterns:
                                        if re.match(pattern, name):
                                            break
                                    else:
                                        raise ValueError(f"unmatched property {name}")
                                return self_

                            return validate_patternProperties

                        classinfo.properties["aio3_validate_patternProperties"].default = pydantic.model_validator(
                            mode="after"
                        )(mkx())

                if schema.allOf:
                    for i in schema.allOf:
                        classinfo.createAnnotations(i, discriminators, schemanames, fwdref=True)
                        classinfo.createFields(i)
        else:
            raise ValueError(_type)

        if _type in ("array", "object"):
            if schema.enum or getattr(schema, "const", None):
                raise NotImplementedError("complex enums/const are not supported")

        classinfo.config = Model.createConfigDict(schema)

        if classinfo.config["extra"] == "allow" and classinfo.root is None:

            def mkx():
                def get_additionalProperties(x):
                    return x.model_extra

                return get_additionalProperties, None, None

            classinfo.properties["aio3_additionalProperties"].default = property(mkx()[0])

        classinfo.validate()
        return classinfo

    @staticmethod
    def createConfigDict(schema: "SchemaType"):
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
            regex_engine="python-re",
            # defer_build=True,
            # validate_assignment=True
        )

    @staticmethod
    def createAnnotation(
        schema: Optional[Union["SchemaType", "ReferenceType"]], _type: Optional[str] = None, fwdref: bool = False
    ) -> Type:
        if schema is None:
            return BaseModel
        if isinstance(schema, SchemaBase):
            nullable = Model.is_nullable(schema)
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
                    if _type in ("boolean", "integer", "number", "string"):
                        oneOf = [i for i in getattr(schema, "oneOf", []) if _type in Model.types(i)]
                        anyOf = [i for i in getattr(schema, "anyOf", []) if _type in Model.types(i)]
                        allOf = [i for i in getattr(schema, "allOf", []) if _type in Model.types(i)]

                        if not (anyOf or oneOf or allOf):
                            v = class_from_schema(schema, _type)
                            r.append(v)
                        else:
                            v = [Model.createAnnotation(i, _type=_type) for i in oneOf]
                            r.extend(v)
                            v = [Model.createAnnotation(i, _type=_type) for i in anyOf]
                            r.extend(v)
                            v = [Model.createAnnotation(i, _type=_type) for i in allOf]
                            r.extend(v)
                    elif _type == "array":
                        r.extend(
                            list(
                                Model.createAnnotation(i, _type=_type)
                                for i in getattr(schema, "oneOf", [])
                                if Model.is_type(i, _type)
                            )
                        )

                        r.extend(
                            list(
                                Model.createAnnotation(i, _type=_type)
                                for i in getattr(schema, "anyOf", [])
                                if Model.is_type(i, _type)
                            )
                        )

                        if isinstance(schema.items, list):
                            v = Tuple[tuple(Model.createAnnotation(i, fwdref=True) for i in schema.items)]
                        elif schema.items:
                            if isinstance(schema.items, ReferenceBase) and schema.items._target == schema:
                                """
                                self referencing array
                                """
                                v = List[schema.get_type(fwdref=True)]  # type: ignore[misc,index]
                            else:
                                v = List[Model.createAnnotation(schema.items, fwdref=True)]  # type: ignore[misc,index]
                        elif schema.items is None:
                            continue
                        else:
                            raise TypeError(schema.items)
                        r.append(v)  # type: ignore[arg-type]
                    elif _type == "object":
                        r.append(schema.get_type(fwdref=fwdref))
                    elif _type == "null":
                        nullable = True
                    else:
                        raise ValueError(_type)

            if len(r) == 1:
                rr = r[0]
            elif len(r) > 1:
                rr = Union[tuple(r)]  # type: ignore[assignment]
            else:
                rr = None  # type: ignore[assignment]
            if nullable is True:
                rr = Optional[rr]  # type: ignore[assignment]
        elif isinstance(schema, ReferenceBase):
            rr = Model.createAnnotation(schema._target, fwdref=True)
        else:
            raise TypeError(type(schema))
        return rr

    @staticmethod
    def types(schema: "SchemaType"):
        if isinstance(schema.type, str):
            yield schema.type
            if getattr(schema, "nullable", False):
                yield "null"
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
                    typesfilter |= {cast(str, TYPES_SCHEMA_MAP.get(type(i))) for i in enum}

                """
                allOf / anyOf / oneOf do not need to be of type object
                but the type of their children can be used to limit the type of the parent
                """
                totalOf: List["SchemaType"]
                allOf, anyOf, oneOf = (
                    set(SCHEMA_TYPES),
                    set(SCHEMA_TYPES),
                    set(SCHEMA_TYPES),
                )

                # allOf - intersection of types
                allOfs: List["SchemaType"]
                if allOfs := sum([getattr(schema, "allOf", [])], []):
                    for x in allOfs:
                        allOf &= set(Model.types(x))

                # anyOf - union of types
                anyOfs: List["SchemaType"]
                if anyOfs := sum([getattr(schema, "anyOf", [])], []):
                    anyOf = set.union(*[set(Model.types(x)) for x in anyOfs]) if anyOfs else set()

                # oneOf - union of types
                oneOfs: List["SchemaType"]
                if oneOfs := sum([getattr(schema, "oneOf", [])], []):
                    oneOf = set.union(*[set(Model.types(x)) for x in oneOfs]) if oneOfs else set()

                if allOfs or anyOfs or oneOfs:
                    tmp = oneOf & allOf & anyOf
                    typesfilter |= tmp
            else:
                raise StopIteration

            if typesfilter:
                values = values & typesfilter

            yield from values

    @staticmethod
    def is_type(schema: "SchemaType", type_) -> bool:
        return isinstance(schema.type, str) and schema.type == type_ or Model.or_type(schema, type_, l=None)

    @staticmethod
    def or_type(schema: "SchemaType", type_: str, l: Optional[int] = 2) -> bool:
        return isinstance((t := schema.type), list) and (l is None or len(t) == l) and type_ in t

    @staticmethod
    def is_nullable(schema: "SchemaType") -> bool:
        return Model.or_type(schema, "null", l=None) or getattr(schema, "nullable", False) is True

    @staticmethod
    def is_type_any(schema: "SchemaType"):
        return schema.type is None

    @staticmethod
    def createField(schema: "SchemaType", _type=None, args=None):
        if args is None:
            args = dict(default=getattr(schema, "default", None))

        # """
        # readOnly & writeOnly are Optional default None
        # """
        # if (v:= (getattr(schema,"readOnly", None) or getattr(schema,"writeOnly", None))) is not None:
        #     if "default" not in args:
        #         args["default"] = None

        """
        collect allOf validators for this field in args before proceeding
        """
        allOf = [i for i in getattr(schema, "allOf", []) if _type in Model.types(i)]
        for i in allOf:
            Model.createField(i, _type, args)

        if Model.is_type(schema, "integer") or Model.is_type(schema, "number") or (_type in {"integer", "number"}):
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
        if Model.is_type(schema, "string") or _type == "string":
            """
            https://docs.pydantic.dev/latest/usage/fields/#string-constraints
            """
            for k, m in {
                "maxLength": "max_length",
                "minLength": "min_length",
                "pattern": "pattern",
            }.items():
                if (v := getattr(schema, k, None)) is not None:
                    args[m] = v

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
