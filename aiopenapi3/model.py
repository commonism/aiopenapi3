from __future__ import annotations

import collections
import types
import uuid
import sys

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path


from .json import JSONReference
from .base import ReferenceBase


if sys.version_info >= (3, 9):
    from typing import List, Optional, Literal, Union, Annotated
else:
    from typing import List, Optional, Union
    from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Extra, Field
from pydantic.schema import field_class_to_schema

type_format_to_class = collections.defaultdict(lambda: dict())


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


class Model(BaseModel):
    class Config:
        extra: Extra.forbid

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

        type_name = schema.title or getattr(schema, "_identity", None) or str(uuid.uuid4())
        fields = dict()
        annotations = dict()

        if hasattr(schema, "anyOf") and schema.anyOf:
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
            annotations.update(Model.annotationsof(schema, discriminators, schemanames))
            fields.update(Model.fieldof(schema))

            if schema.allOf:
                for i in schema.allOf:
                    annotations.update(Model.annotationsof(i, discriminators, schemanames))

        # this is a anyOf/oneOf - the parent may have properties which will collide with __root__
        # so - add the parent properties to this model
        if extra:
            annotations.update(Model.annotationsof(extra, discriminators, schemanames))
            fields.update(Model.fieldof(extra))

        fields["__annotations__"] = annotations

        m = types.new_class(type_name, (BaseModel,), {}, lambda ns: ns.update(fields))
        m.update_forward_refs()
        return m

    @staticmethod
    def typeof(schema: "SchemaBase"):
        r = None
        if schema.enum:
            r = Literal[tuple(i for i in schema.enum)]
        elif schema.type == "integer":
            r = int
        elif schema.type == "number":
            r = class_from_schema(schema)
        elif schema.type == "string":
            r = class_from_schema(schema)
        elif schema.type == "boolean":
            r = bool
        elif schema.type == "array":
            r = List[schema.items.get_type()]
        elif schema.type == "object":
            return schema.get_type()
        elif schema.type is None:  # discriminated root
            """
            recursively define related discriminated objects
            """
            schema.get_type()
            return None
        else:
            raise TypeError(schema.type)

        return r

    @staticmethod
    def annotationsof(schema: "SchemaBase", discriminators, shmanm):
        annotations = dict()
        if schema.type == "array":
            annotations["__root__"] = Model.typeof(schema)
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
                    annotations[name] = r
                    continue
                except StopIteration:
                    r = Model.typeof(f)

                from . import v20, v30, v31

                if isinstance(schema, (v20.Schema, v20.Reference)):
                    if not f.required:
                        annotations[name] = Optional[r]
                    else:
                        annotations[name] = r
                elif isinstance(schema, (v30.Schema, v31.Schema, v30.Reference, v31.Reference)):
                    if name not in schema.required:
                        annotations[name] = Optional[r]
                    else:
                        annotations[name] = r
                else:
                    raise TypeError(schema)

        return annotations

    @staticmethod
    def fieldof(schema: "SchemaBase"):
        fields = dict()
        if schema.type == "array":
            return fields
        else:
            for name, f in schema.properties.items():
                args = dict()
                for i in ["default"]:
                    v = getattr(f, i, None)
                    if v:
                        args[i] = v
                fields[name] = Field(**args)
        return fields


if len(type_format_to_class) == 0:
    generate_type_format_to_class()
