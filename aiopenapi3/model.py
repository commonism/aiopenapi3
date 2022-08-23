from __future__ import annotations

import collections
import logging
import sys
import re
import warnings

import types
import pydantic

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path


from .json import JSONReference
from .base import ReferenceBase, SchemaBase
from . import me

if sys.version_info >= (3, 9):
    from typing import List, Optional, Literal, Union, Annotated, Tuple, Dict
else:
    from typing import List, Optional, Union, Dict
    from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Extra, Field
from pydantic.schema import field_class_to_schema

type_format_to_class = collections.defaultdict(lambda: dict())

log = logging.getLogger("aiopenapi3.model")


def generate_type_format_to_class():
    """
    initialize type_format_to_class
    :return: None
    """
    global type_format_to_class
    for cls, spec in field_class_to_schema:
        if spec["type"] not in frozenset(["string", "number"]):
            continue
        type_format_to_class[spec["type"]][spec.get("format", None)] = cls


def class_from_schema(s):
    a = type_format_to_class[s.type]
    b = a.get(s.format, a[None])
    return b


class Model:  # (BaseModel):
    #    class Config:
    #        extra: Extra.forbid

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

        # do not create models for primitive types
        if schema.type in ("string", "integer", "number", "boolean"):
            return Model.typeof(schema)

        type_name = schema._get_identity("L8")
        fields = dict()
        annotations = dict()

        if hasattr(schema, "anyOf") and schema.anyOf:
            assert all(schema.anyOf)
            t = tuple(
                i.get_type(
                    names=schemanames + ([i.ref] if isinstance(i, ReferenceBase) else []),
                    discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                    extra=schema,
                )
                for i in schema.anyOf
            )
            if schema.discriminator and schema.discriminator.mapping:
                annotations["__root__"] = Annotated[Union[t], Field(discriminator=schema.discriminator.propertyName)]
            else:
                annotations["__root__"] = Union[t]
        elif hasattr(schema, "oneOf") and schema.oneOf:
            t = tuple(
                i.get_type(
                    names=schemanames + ([i.ref] if isinstance(i, ReferenceBase) else []),
                    discriminators=discriminators + ([schema.discriminator] if schema.discriminator else []),
                    extra=schema,
                )
                for i in schema.oneOf
            )

            if schema.discriminator and schema.discriminator.mapping:
                annotations["__root__"] = Annotated[Union[t], Field(discriminator=schema.discriminator.propertyName)]
            else:
                annotations["__root__"] = Union[t]
        else:
            # default schema properties …
            annotations.update(Model.annotationsof(schema, discriminators, schemanames, fwdref=True))
            fields.update(Model.fieldof(schema))

            if schema.allOf:
                for i in schema.allOf:
                    annotations.update(Model.annotationsof(i, discriminators, schemanames, fwdref=True))

        # this is a anyOf/oneOf - the parent may have properties which will collide with __root__
        # so - add the parent properties to this model
        if extra:
            annotations.update(Model.annotationsof(extra, discriminators, schemanames))
            fields.update(Model.fieldof(extra))

        # FAILS ON PYTHON3.7
        #
        # if fields and "__root__" in annotations and typing.get_origin(annotations["__root__"]) == typing.Dict:
        #     warnings.warn("Dropping __root__ Dict mapping …")
        #     log.warning(
        #         f"Dropping __root__ Dict mapping {annotations['__root__']} due to fields {sorted(fields.keys())}"
        #     )
        #     del annotations["__root__"]

        fields["__annotations__"] = annotations

        fields["__module__"] = me.__name__

        # dif not work for __root__
        # xf = dict()
        # for k in filter(lambda x: x != "__annotations__", fields.keys()):
        #    xf[k] = (annotations.get(k, None), fields.get(k, None))
        # m = pydantic.create_model(type_name, __base__=BaseModel, **xf, __module__=__name__)

        fields["Config"] = Model.configof(schema)

        m = types.new_class(type_name, (BaseModel,), {}, lambda ns: ns.update(fields))
        return m

    @staticmethod
    def configof(schema):
        """
        create pydantic Config for the BaseModel
        we need to set "extra" - Extra.allow is not an option though …

        Extra.allow is a problem
          * overwriting class attributes/members/methods
          * pydantic type identification does not work reliable due to missing rejects,

        """
        arbitrary_types_allowed_ = False
        if schema.additionalProperties is not None:
            if isinstance(schema.additionalProperties, bool):
                if schema.additionalProperties == False:
                    extra_ = Extra.forbid
                else:
                    extra_ = Extra.allow
                    arbitrary_types_allowed_ = True
            elif isinstance(schema.additionalProperties, (SchemaBase, ReferenceBase)):
                extra_ = Extra.forbid
                """
                we allow arbitrary types if additionalProperties has no properties
                """

                if len(schema.additionalProperties.properties) == 0:
                    arbitrary_types_allowed_ = True
            else:
                raise TypeError(schema.additionalProperties)
        else:
            extra_ = Extra.allow

        """
        PR?
        """
        if extra_ == Extra.forbid and schema.extensions:
            extra_ = Extra.ignore

        extra_ = Extra.ignore if extra_ == Extra.allow else extra_

        class Config:
            extra = extra_
            arbitrary_types_allowed = arbitrary_types_allowed_

        return Config

    @staticmethod
    def typeof(schema: "SchemaBase", fwdref=False):
        r = None
        #        assert schema is not None
        if schema is None:
            return BaseModel
        if isinstance(schema, SchemaBase):
            if schema.enum:
                # un-Reference
                _names = tuple(i for i in map(lambda x: x._target if isinstance(x, ReferenceBase) else x, schema.enum))
                r = Literal[_names]
            elif schema.type == "integer":
                r = int
            elif schema.type == "number":
                r = class_from_schema(schema)
            elif schema.type == "string":
                r = class_from_schema(schema)
            elif schema.type == "boolean":
                r = bool
            elif schema.type == "array":
                if isinstance(schema.items, list):
                    r = Tuple[tuple(i.ref.get_type(fwdref=True) for i in schema.items)]
                elif schema.items:
                    r = List[Model.typeof(schema.items)]
                elif schema.items is None:
                    return
                else:
                    raise TypeError(schema.items)
            elif schema.type == "object":
                return schema.get_type(fwdref=fwdref)
            elif schema.type is None:  # discriminated root
                """
                recursively define related discriminated objects
                """
                return schema.get_type(fwdref=fwdref)
        elif isinstance(schema, ReferenceBase):
            r = Model.typeof(schema._target, fwdref=True)
        else:
            raise TypeError(type(schema))

        return r

    @staticmethod
    def annotationsof(schema: "SchemaBase", discriminators, shmanm, fwdref=False):
        from . import v20

        annotations = dict()
        if schema.type == "array":
            annotations["__root__"] = Model.typeof(schema)
        elif (
            schema.type == "object"
            and schema.additionalProperties
            and isinstance(schema.additionalProperties, (SchemaBase, ReferenceBase))
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
            annotations["__root__"] = Dict[str, Model.typeof(schema.additionalProperties)]
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
                    annotations[Model.nameof(name)] = r
                    continue
                except StopIteration:
                    r = Model.typeof(f, fwdref=fwdref)

                from . import v20, v30, v31

                if isinstance(schema, (v20.Schema, v20.Reference)):
                    if not f.required:
                        annotations[Model.nameof(name)] = Optional[r]
                    else:
                        annotations[Model.nameof(name)] = r
                elif isinstance(schema, (v30.Schema, v31.Schema, v30.Reference, v31.Reference)):
                    if name not in schema.required:
                        annotations[Model.nameof(name)] = Optional[r]
                    else:
                        annotations[Model.nameof(name)] = r
                else:
                    raise TypeError(schema)

        return annotations

    @staticmethod
    def fieldof(schema: "SchemaBase"):
        fields = dict()
        if schema.type == "array":
            return fields
        elif (
            schema.type == "object"
            and schema.additionalProperties
            and isinstance(schema.additionalProperties, (SchemaBase, ReferenceBase))
        ):
            if schema.properties:
                """
                Schema with additionalProperties and named properties …

                we can't serve this.
                """
                warnings.warn("Ignoring Schema with additionalProperties and named properties")
        else:
            for name, f in schema.properties.items():
                args = dict()
                name = Model.nameof(name, args=args)
                for i in ["default"]:
                    v = getattr(f, i, None)
                    if v:
                        args[i] = v
                fields[name] = Field(**args)

        return fields

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

        try:
            rename = re.sub(r"[@\.-]", "_", rename)
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
