from __future__ import annotations

import collections
import dataclasses
import logging
import sys
import re
from typing import Any


import pydantic
import pydantic_core

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path


from .json import JSONReference
from .base import ReferenceBase, SchemaBase
from . import me

if sys.version_info >= (3, 9):
    from typing import List, Optional, Union, Tuple, Dict, Annotated, Literal
else:
    from typing import List, Optional, Union, Tuple, Dict
    from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Extra, Field, RootModel
from .pydanticv2 import field_class_to_schema


type_format_to_class = collections.defaultdict(lambda: dict())

log = logging.getLogger("aiopenapi3.model")

SCHEMA_TYPES_MAP = {"string": str, "number": float, "boolean": bool, "integer": int}
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
    from pydantic import Base64Str, Base64Bytes

    type_format_to_class["string"]["byte"] = Base64Str


def class_from_schema(s, type):
    a = type_format_to_class[type]
    b = a.get(s.format, a[None])
    return b


@dataclasses.dataclass
class _ClassInfo:
    @dataclasses.dataclass
    class _PropertyInfo:
        annotation: Any = None
        default: Any = None

    root: Any = None
    config: Dict[str, Any] = None
    properties: Dict[str, _PropertyInfo] = dataclasses.field(
        default_factory=lambda: collections.defaultdict(lambda: _ClassInfo._PropertyInfo())
    )


class Model:  # (BaseModel):
    #    class Config:
    #        extra: "forbid"

    TypeInfo = collections.namedtuple("annotation", "value")
    ALIASES = dict()

    @classmethod
    def from_schema(
        cls,
        schema: "SchemaBase",
        schemanames: List[str] = None,
        discriminators: List["DiscriminatorBase"] = None,
        extra: "SchemaBase" = None,
    ):
        if schemanames is None:
            schemanames = []

        if discriminators is None:
            discriminators = []

        r = list()

        for _type in Model.types(schema):
            r.append(Model.from_schema_type(schema, _type, schemanames, discriminators, extra))

        if len(r) > 1:
            r = Union[tuple(r)]
            type_name = schema._get_identity("L8")
            m = pydantic.create_model(type_name, __base__=(RootModel[r],), __module__=me.__name__)
        else:
            m = r[0]
        return m

    @classmethod
    def from_schema_type(
        cls,
        schema: "SchemaBase",
        type: str,
        schemanames: List[str] = None,
        discriminators: List["DiscriminatorBase"] = None,
        extra: "SchemaBase" = None,
    ):
        type_name = schema._get_identity("L8") + f"_{type}"

        classinfo = _ClassInfo()

        # do not create models for primitive types
        if type in ("string", "integer", "number", "boolean"):
            if schema.format is None:
                return Model.typeof(schema, type=type)
            else:
                classinfo.root = Model.typeof(schema, type=type)
        elif type == "object":
            if hasattr(schema, "anyOf") and schema.anyOf:
                assert all(schema.anyOf)
                #                types_ |= set(map(lambda x: x.type, schema.anyOf))
                t = tuple(
                    i.get_type(
                        names=schemanames + ([i.ref] if isinstance(i, ReferenceBase) else []),
                        discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                        extra=schema,
                    )
                    for i in schema.anyOf
                )
                if schema.discriminator and schema.discriminator.mapping:
                    classinfo.root = Annotated[Union[t], Field(discriminator=schema.discriminator.propertyName)]
                else:
                    classinfo.root = Union[t]
            elif hasattr(schema, "oneOf") and schema.oneOf:
                #                types_ &= set(map(lambda x: x.type, schema.anyOf))
                t = tuple(
                    i.get_type(
                        names=schemanames + ([i.ref] if isinstance(i, ReferenceBase) else []),
                        discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                        extra=schema,
                    )
                    for i in schema.oneOf
                )

                if schema.discriminator and schema.discriminator.mapping:
                    classinfo.root = Annotated[Union[t], Field(discriminator=schema.discriminator.propertyName)]
                else:
                    classinfo.root = Union[t]
            else:
                # default schema properties …
                Model.annotationsof_type(schema, type, discriminators, schemanames, classinfo, fwdref=True)
                Model.fieldof(schema, classinfo)
                if "patternProperties" in schema.model_fields_set:

                    def mkx():
                        def get_patternProperties(x, item):
                            for name, value in x.model_extra.items():
                                if re.match(item, name):
                                    yield name, value

                        get_patternProperties.__annotations__["item"] = Literal[
                            tuple(sorted(schema.patternProperties.keys()))
                        ]
                        return get_patternProperties

                    classinfo.properties["aio3_patternProperties"].default = mkx()
                if schema.allOf:
                    #                    types_ &= set(map(lambda x: x.type, schema.allOf))
                    for i in schema.allOf:
                        Model.annotationsof(i, discriminators, schemanames, classinfo, fwdref=True)
                        Model.fieldof(i, classinfo)

            # this is a anyOf/oneOf - the parent may have properties which will collide with __root__
            # so - add the parent properties to this model
            if extra:
                Model.annotationsof(extra, discriminators, schemanames, classinfo)
                Model.fieldof(extra, classinfo)
        elif type == "array":
            classinfo.root = Model.typeof(schema, "array")

        classinfo.properties["__module__"].default = me.__name__
        classinfo.config = Model.configof(schema)

        if classinfo.config["extra"] == "allow" and classinfo.root is None:

            def mkx():
                def get_additionalProperties(x):
                    return x.model_extra

                return get_additionalProperties, None, None

            classinfo.properties["aio3_additionalProperties"].default = property(mkx()[0])

        if classinfo.root:
            m = pydantic.create_model(type_name, __base__=(RootModel[classinfo.root],), __module__=me.__name__)
        else:
            properties = dict([(k, (v.annotation, v.default)) for k, v in classinfo.properties.items()])
            m = pydantic.create_model(type_name, __base__=(BaseModel,), model_config=classinfo.config, **properties)
        return m

    @staticmethod
    def configof(schema):
        """
        create pydantic model_config for the BaseModel
        we need to set "extra" - "allow" is not an option though …

        "allow" is a problem
          * overwriting class attributes/members/methods
          * pydantic type identification does not work reliable due to missing rejects,

        """
        arbitrary_types_allowed_ = False
        extra_ = "allow"

        if schema.additionalProperties is not None:
            if isinstance(schema.additionalProperties, bool):
                if schema.additionalProperties == False:
                    extra_ = "forbid"
                else:
                    arbitrary_types_allowed_ = True
            elif isinstance(schema.additionalProperties, (SchemaBase, ReferenceBase)):
                """
                we allow arbitrary types if additionalProperties has no properties
                """
                if len(schema.additionalProperties.properties) == 0:
                    arbitrary_types_allowed_ = True
            else:
                raise TypeError(schema.additionalProperties)

        """
        PR?
        """
        if extra_ == "forbid" and schema.extensions:
            extra_ = "ignore"

        #        extra_ = "ignore" if extra_ == "allow" else extra_

        return dict(
            undefined_types_warning=False,
            extra=extra_,
            arbitrary_types_allowed=arbitrary_types_allowed_,
            # validate_assignment=True
        )

    @staticmethod
    def typeof(schema: "SchemaBase", type=None, fwdref=False):
        r = None
        #        assert schema is not None
        if schema is None:
            return BaseModel
        if isinstance(schema, SchemaBase):
            nullable = False
            r = list()
            for type in Model.types(schema) if not type else [type]:
                if type == "integer":
                    r.append(int)
                elif type == "number":
                    r.append(class_from_schema(schema, "number"))
                elif type == "string":
                    if schema.enum:
                        # un-Reference
                        _names = tuple(
                            i for i in map(lambda x: x._target if isinstance(x, ReferenceBase) else x, schema.enum)
                        )
                        v = Literal[_names]
                    else:
                        v = class_from_schema(schema, "string")
                    r.append(v)
                elif type == "boolean":
                    r.append(bool)
                elif type == "array":
                    if isinstance(schema.items, list):
                        v = Tuple[tuple(Model.typeof(i, fwdref=True) for i in schema.items)]
                    elif schema.items:
                        v = List[Model.typeof(schema.items, fwdref=fwdref)]
                    elif schema.items is None:
                        return None
                    else:
                        raise TypeError(schema.items)
                    r.append(v)
                elif type == "object":
                    r.append(schema.get_type(fwdref=fwdref))
                elif type == "null":
                    nullable = True
                else:
                    raise ValueError(type)
            if len(r) == 1:
                r = r[0]
            else:
                r = Union[tuple(r)]
            if nullable is True:
                r = Optional[r]
        elif isinstance(schema, ReferenceBase):
            r = Model.typeof(schema._target, fwdref=True)
        else:
            raise TypeError(type(schema))
        return r

    @staticmethod
    def annotationsof(schema: "SchemaBase", discriminators, shmanm, classinfo: _ClassInfo, fwdref=False):
        if isinstance(schema.type, list):
            classinfo.root = Model.typeof(schema)
        elif schema.type is None:
            pass
        else:
            return Model.annotationsof_type(schema, schema.type, discriminators, shmanm, classinfo, fwdref)
        return classinfo

    @staticmethod
    def annotationsof_type(
        schema: "SchemaBase", type: str, discriminators, shmanm, classinfo: _ClassInfo, fwdref=False
    ):
        if type == "array":
            v = Model.typeof(schema)
            if Model.is_nullable(schema):
                v = Optional[v]
            classinfo.root = v
        elif type == "object":
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
                v = Dict[str, Model.typeof(schema.additionalProperties)]
                if Model.is_nullable(schema):
                    v = Optional[v]
                classinfo.root = v
            else:
                for name, f in schema.properties.items():
                    r = None
                    try:
                        discriminator = next(filter(lambda x: name == x.propertyName, discriminators))
                        # the property is a discriminiator
                        if discriminator.mapping:
                            for disc, v in discriminator.mapping.items():
                                # lookup the mapping value for the schema
                                if v in shmanm:
                                    r = Literal[disc]
                                    break
                            else:
                                raise ValueError(f"unmatched discriminator in mapping for {schema}")
                        else:
                            # the discriminator lacks a mapping, use the last name
                            # JSONPointer.decode required ?
                            literal = Path(JSONReference.split(shmanm[-1])[1]).parts[-1]
                            r = Literal[literal]

                        # this got Literal avoid getting Optional
                        classinfo.properties[Model.nameof(name)].annotation = r
                        continue
                    except StopIteration:
                        r = Model.typeof(f, fwdref=fwdref)

                    if name not in schema.required or Model.is_nullable(f):
                        r = Optional[r]

                    classinfo.properties[Model.nameof(name)].annotation = r

        elif type in ("string", "integer", "boolean", "number"):
            pass
        else:
            raise ValueError()
        return classinfo

    @staticmethod
    def types(schema: "SchemaBase"):
        if isinstance(schema.type, str):
            yield schema.type
        else:
            typesfilter = None
            if isinstance(schema.type, list):
                values = schema.type
            elif schema.type is None:
                values = list(SCHEMA_TYPES) + ["object", "array"]
                typesfilter = set()
                if (const := getattr(schema, "const", None)) is not None:
                    typesfilter.add(type(const))

                if enum := getattr(schema, "enum", None):
                    typesfilter |= set([type(i) for i in enum])

            for i in values:
                if typesfilter and SCHEMA_TYPES_MAP.get(i) not in typesfilter:
                    """
                    filter types using enum & const
                    """
                    continue
                yield i

    @staticmethod
    def is_type(schema: "SchemaBase", type_) -> bool:
        if isinstance(schema.type, str) and schema.type == type_ or Model.or_type(schema, type_):
            return True

    @staticmethod
    def or_type(schema: "SchemaBase", type_: str) -> bool:
        return isinstance((t := schema.type), list) and len(t) == 2 and type_ in t

    @staticmethod
    def is_nullable(schema: "SchemaBase") -> bool:
        return Model.is_type(schema, "null")

    @staticmethod
    def or_nullable(schema: "SchemaBase") -> bool:
        return Model.or_type(schema, "null")

    @staticmethod
    def is_type_any(schema: "SchemaBase"):
        return schema.type is None

    @staticmethod
    def fieldof(schema: "SchemaBase", classinfo: _ClassInfo):
        if schema.type == "array":
            return classinfo
        if Model.is_type(schema, "object") or Model.is_type_any(schema):
            for name, f in schema.properties.items():
                args = dict()
                if name not in schema.required:
                    args["default"] = None
                name = Model.nameof(name, args=args)
                if Model.is_nullable(f):
                    args["default"] = f"default-{name}"
                for i in ["default"]:
                    if (v := getattr(f, i, None)) is not None:
                        args[i] = v
                classinfo.properties[name].default = Field(**args)
        return classinfo

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
