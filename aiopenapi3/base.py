import typing
import warnings
from typing import Optional, Any, List, Dict, ForwardRef, Union, Tuple, cast, Type, FrozenSet, Sequence

import re
import builtins
import keyword
import uuid
import sys

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard

from pydantic import BaseModel, Field, AnyUrl, model_validator, PrivateAttr, ConfigDict

from .json import JSONPointer, JSONReference
from .errors import ReferenceResolutionError, OperationParameterValidationError

if typing.TYPE_CHECKING:
    from aiopenapi3 import OpenAPI
    from ._types import SchemaType, JSON, PathItemType, ParameterType, ReferenceType, DiscriminatorType

HTTP_METHODS = frozenset(["get", "delete", "head", "post", "put", "patch", "trace"])


class ObjectBase(BaseModel):
    """
    The base class for all schema objects.  Includes helpers for common schema-related functions.
    """

    model_config = ConfigDict(extra="forbid")


class ObjectExtended(ObjectBase):
    extensions: Optional[Any] = Field(default=None)

    @model_validator(mode="before")
    def validate_ObjectExtended_extensions(cls, values):
        """
        FIXME
        https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#specification-extensions
        :param values:
        :return: values
        """
        if values is None:
            return None
        if not isinstance(values, dict):
            return values
        e = dict()
        rm = set()
        for k, v in values.items():
            if k.startswith("x-"):
                e[k[2:]] = v
                rm.add(k)
        if len(e):
            for i in rm:
                del values[i]
            if "extensions" in values.keys():
                raise ValueError("extensions")
            values["extensions"] = e

        return values


class PathsBase(ObjectBase):
    extensions: Dict[str, Any]

    @property
    def _paths(self):
        return self.paths

    def __getitem__(self, item):
        return self.paths[item]

    def items(self):
        return self.paths.items()

    def values(self):
        return self.paths.values()


class PathItemBase:
    #    parameters: Optional[List[Union["ParameterBase", "ReferenceBase"]]]
    parameters: List[Any]


class RootBase:
    @staticmethod
    def resolve(api: "OpenAPI", root: "RootBase", obj, _PathItem, _Reference):
        from . import v20, v30, v31

        def replaceSchemaReference(data):
            def replace(ivalue):
                if not isinstance(ivalue, SchemaBase):
                    return ivalue
                ir = getattr(ivalue, "ref", None)
                if not ir:
                    return ivalue
                return _Reference.model_construct(ref=ir)

            if isinstance(data, list):
                for idx, _item in enumerate(data):
                    n = replace(_item)
                    if _item != n:
                        data[idx] = n

            elif isinstance(data, dict):
                new = dict()
                for _k, _v in data.items():
                    n = replace(_v)  # Swagger 2.0 Schema.ref resolver …
                    if _v != n:
                        _v = n
                        new[_k] = _v
                if new:
                    data.update(new)

        if isinstance(obj, ObjectBase):
            for slot in filter(lambda x: not x.startswith("_") or x == "__root__", obj.model_fields_set):
                value = getattr(obj, slot)
                if value is None:
                    continue
                if isinstance(value, (int, bool, float)):
                    continue

                # v3.1 - Schema $ref
                if isinstance(root, (v20.root.Root, v30.root.Root, v31.root.Root)):
                    if isinstance(value, SchemaBase):
                        if (r := getattr(value, "ref", None)) and not isinstance(r, ReferenceBase):
                            value = _Reference.model_construct(ref=r)
                            setattr(obj, slot, value)

                if isinstance(root, (v30.root.Root, v31.root.Root)):
                    if isinstance(value, (v30.Discriminator, v31.Discriminator)):
                        """
                        Discriminated Unions - implementing undefined behavior
                        sub-schemas not having the discriminated property "const" or enum or mismatching the mapping
                        are a problem
                        pydantic requires these to be mapping Literal and unique
                        creating a separate Model for the sub-schema with the mapping Literal is possible
                        but makes using them horrible

                        we warn about it and force feed the mapping Literal to make it work
                        """

                        if not value.mapping:
                            value.mapping = dict()

                            for v in (obj.oneOf or []) + (obj.anyOf or []):
                                k = Path(JSONReference.split(v.ref)[1]).parts[-1]
                                value.mapping[k] = v

                        for k, v in value.mapping.items():
                            if not isinstance(v, _Reference):
                                value.mapping[k] = _Reference.model_construct(ref=v)
                            else:
                                if v._target is None:
                                    continue
                                from .model import Model
                                from . import errors

                                if "object" not in (t := sorted(Model.types(v._target))):
                                    raise errors.SpecError(f"Discriminated Union on a schema with types {t}")

                                if (p := v.properties.get(value.propertyName, None)) is None:
                                    # Warning Model 'Volume' needs a discriminator field for key 'type'
                                    p = v.properties[value.propertyName] = v._target.__class__(
                                        type="string", additionalProperties=False, enum=[k]
                                    )

                                if (c := getattr(p, "const", None)) is None and len(p.enum or []) == 0:
                                    warnings.warn(
                                        f"Discriminated Union member {v.ref} without const/enum key property {value.propertyName}",
                                        category=errors.DiscriminatorWarning,
                                    )
                                    v.properties[value.propertyName].enum = [k]
                                else:
                                    if c and c != k:
                                        warnings.warn(
                                            f"Discriminated Union member key property const mismatches property mapping {c} != {k}",
                                            category=errors.DiscriminatorWarning,
                                        )
                                        v.properties[value.propertyName].const = k
                                    if p.enum and (len(p.enum) != 1 or p.enum[0] != k):
                                        warnings.warn(
                                            f"Discriminated Union member key property enum mismatches property mapping {p.enum[0]} != {k}",
                                            category=errors.DiscriminatorWarning,
                                        )
                                        v.properties[value.propertyName].enum = [k]

                if not isinstance(value, ReferenceBase):
                    """
                    ref fields embedded in objects -> replace the object with a Reference object

                    PathItem Ref is ambiguous
                    https://github.com/OAI/OpenAPI-Specification/issues/2635
                    """
                    if isinstance(root, (v20.root.Root, v30.root.Root, v31.root.Root)):
                        if isinstance(obj, _PathItem) and slot == "ref":
                            ref = _Reference.model_construct(ref=value)
                            ref._target = api.resolve_jr(root, obj, ref)
                            setattr(obj, slot, ref)

                value = getattr(obj, slot)

                if isinstance(value, PathsBase):
                    value.items()
                    value = value._paths

                if isinstance(value, (str, int, float)):  # , datetime.datetime, datetime.date)):
                    continue
                elif isinstance(value, AnyUrl):
                    pass
                elif isinstance(value, _Reference):
                    value._target = api.resolve_jr(root, obj, value)
                elif issubclass(type(value), ObjectBase) or isinstance(value, (dict, list)):
                    # otherwise, continue resolving down the tree
                    RootBase.resolve(api, root, value, _PathItem, _Reference)
                else:
                    raise TypeError(type(value), value)
        elif isinstance(obj, dict):
            if isinstance(root, (v20.root.Root, v31.root.Root)):
                """
                Resolving/Replacing Swagger 2.0 nested Schema.ref
                Schema.properties[name] -> Schema.ref ==> Schema.properties[name] -> Reference
                """
                replaceSchemaReference(obj)

            for k, v in obj.items():
                if isinstance(v, _Reference):
                    if v.ref:
                        v._target = api.resolve_jr(root, obj, v)
                elif isinstance(v, (ObjectBase, dict, list)):
                    RootBase.resolve(api, root, v, _PathItem, _Reference)

        elif isinstance(obj, list):
            if isinstance(root, (v20.root.Root, v31.root.Root)):
                replaceSchemaReference(obj)

            # if it's a list, resolve its item's references
            for item in obj:
                if isinstance(item, _Reference):
                    item._target = api.resolve_jr(root, obj, item)
                elif isinstance(item, (ObjectBase, dict, list)):
                    RootBase.resolve(api, root, item, _PathItem, _Reference)

    def _resolve_references(self, api):
        """
        Resolves all reference objects below this object and notes their original
        value was a reference.
        """
        # RootBase.resolve(api, self, self, None, None)
        raise NotImplementedError("specific")

    def resolve_jp(self, jp):
        """
        Given a $ref path, follows the document tree and returns the given attribute.

        :param jp: The path down the spec tree to follow
        :type jp: str #/foo/bar

        :returns: The node requested
        :rtype: ObjectBase
        :raises ValueError: if the given path is not valid
        """
        path = jp.split("/")[1:]
        node = self

        for idx, part in enumerate(path, start=1):
            part = JSONPointer.decode(part)

            if isinstance(node, PathsBase):  # forward
                node = node._paths  # will be dict

            if isinstance(node, dict):
                if part not in node:  # pylint: disable=unsupported-membership-test
                    raise ReferenceResolutionError(f"Invalid path {path[:idx]} in Reference")
                node = node.get(part)
            elif isinstance(node, list):
                node = node[int(part)]
            elif isinstance(node, ObjectBase):
                part = Model.nameof(part)
                if not hasattr(node, part):
                    raise ReferenceResolutionError(f"Invalid path {path[:idx]} in Reference")
                node = getattr(node, part)
            else:
                raise ReferenceResolutionError(f"Invalid node {node} in Reference {path[:idx]}")

        return node


class ReferenceBase:
    ref: str
    _target: Union["SchemaType", "PathItemType"]


class ParameterBase:
    pass


class DiscriminatorBase:
    pass


#    propertyName: str
#    mapping: Dict[str, str] = Field(default_factory=dict)


class SchemaBase(BaseModel):
    """
    The Base for the Schema
    """

    _model_type: Type["BaseModel"] = PrivateAttr(default=None)
    """
    use to store _the_ model
    """

    _model_types: List[Type["BaseModel"]] = PrivateAttr(default_factory=list)
    """
    sub-schemas add the properties of the parent to the model of the subschemas

    e.g.:

    A:
      type: object
      allOf:
      - B
      - C
      properties:
        data: str

    has to add 'A.data' to B - making B(&A) incompatible to B
    same for C

    A = Union[B(&A)|C(&A)]

    _model_types is used to store these different model representations of the same schema
    """

    _identity: str = PrivateAttr(default=None)
    """
    The _identity attribute is set during OpenAPI.__init__ and used to create the class name in get_type()
    """

    #    items: Optional[Union["SchemaType", List["SchemaType"]]]

    def __getstate__(self):
        """
        pickle can't do the _model_type - remove from pydantic's __getstate__
        :return:
        """
        r = BaseModel.__getstate__(self)
        try:
            for k, v in {"_model_type": None, "_model_types": list()}.items():
                if k in r["__pydantic_private__"]:
                    r["__pydantic_private__"] = r["__pydantic_private__"].copy()
                    r["__pydantic_private__"][k] = v

        except Exception:
            pass
        return r

    def _get_identity(self, prefix="XLS", name=None):
        if self._identity is None:
            if name is None:
                name = self.title
            if name:
                n = re.sub(r"\W", "_", name, flags=re.ASCII)
            else:
                n = str(uuid.uuid4()).replace("-", "_")

            try:
                # n = re.sub(r"^([0-9]+)(.*)", r"CLS\1\2", n)
                int(n[0])
                n += "_"
            except ValueError:
                pass

            if keyword.iskeyword(n) or hasattr(builtins, n):
                n += "_"

            if n != name:
                self._identity = f"{prefix}{n}"
            else:
                self._identity = name
        return self._identity

    def set_type(
        self,
        names: Optional[List[str]] = None,
        discriminators: Optional[Sequence[DiscriminatorBase]] = None,
        extra: Optional["SchemaBase"] = None,
    ) -> Type[BaseModel]:
        from .model import Model

        if extra is None:
            self._model_type = Model.from_schema(
                cast("SchemaType", self), names, cast(List["DiscriminatorType"], discriminators)
            )
            return self._model_type
        else:
            identity = self._identity
            self._identity = f"{identity}.c{len(self._model_types)}"
            r = Model.from_schema(
                cast("SchemaType", self), names, cast(List["DiscriminatorType"], discriminators), extra
            )
            self._model_types.append(r)
            self._identity = identity
            return r

    def get_type(
        self,
        names: Optional[List[str]] = None,
        discriminators: Optional[Sequence[DiscriminatorBase]] = None,
        extra: Optional["SchemaBase"] = None,
        fwdref: bool = False,
    ) -> Union[Type[BaseModel], ForwardRef]:
        if fwdref:
            if "module" in ForwardRef.__init__.__code__.co_varnames:
                # FIXME Python < 3.9 compat
                return ForwardRef(f'__types["{self._get_identity("FWD")}"]', module="aiopenapi3.me")
            else:
                return ForwardRef(f'__types["{self._get_identity("FWD")}"]')
        if extra is None:
            if self._model_type is None:
                self._model_type = self.set_type(names, discriminators, extra)
            return self._model_type
        else:
            return self.set_type(names, discriminators, extra)

    def model(self, data: "JSON") -> Union[BaseModel, List[BaseModel]]:
        """
        Generates a model representing this schema from the given data.

        :param data: The data to create the model from.  Should match this schema.
        :type data: dict

        :returns: A new :any:`Model` created in this Schema's type from the data.
        :rtype: self.get_type()
        """

        if self.type == "boolean":
            assert len(self.properties) == 0
            t = Model.typeof(cast("SchemaType", self))
            if not isinstance(data, t):
                return t(data)
            return data
        else:
            type_ = cast("SchemaType", self.get_type())
            r = type_.model_validate(data)
            if self.type in ("string", "number", "integer", "array"):
                return r.root
            return r


class OperationBase:
    # parameters: Optional[List[Union[ParameterBase, ReferenceBase]]]
    parameters: List[Any]

    def _validate_path_parameters(self, pi_: "PathItemBase", path_: str, loc: Tuple[Any, str]):
        """
        Ensures that all parameters for this path are valid
        """
        assert isinstance(path_, str)
        # FIXME { and } are allowed in parameter name, regex can't handle this e.g. {name}}
        path = frozenset(re.findall(r"{([a-zA-Z0-9\-\._~]+)}", path_))

        def parameter_in_path(c: Union["ParameterType", "ReferenceType"]) -> TypeGuard["ParameterType"]:
            if isinstance(c, ParameterBase):
                return c.in_ == "path"
            assert isinstance(c, ReferenceBase)
            return parameter_in_path(c._target)

        assert self.parameters is not None
        assert pi_.parameters is not None
        op: FrozenSet[str] = frozenset(map(lambda x: x.name, filter(parameter_in_path, self.parameters)))
        pi: FrozenSet[str] = frozenset(map(lambda x: x.name, filter(parameter_in_path, pi_.parameters)))

        invalid = sorted(filter(lambda x: re.match(r"^([a-zA-Z0-9\-\._~]+)$", x) is None or len(x) == 0, op | pi))
        if invalid:
            # FIXME
            #   OpenAPI does not allow RFC 6570 URI templates
            #   but name:\d+ may be valid though
            raise OperationParameterValidationError(path_, *loc, f"Parameter names are invalid: {invalid}")

        r = (op | pi) - path
        if r:
            raise OperationParameterValidationError(
                path_, *loc, f"Parameter name{'s' if len(r) > 1 else ''} not found in path: {', '.join(sorted(r))}"
            )

        r = path - (op | pi)
        if r:
            raise OperationParameterValidationError(
                path_,
                *loc,
                f"Parameter name{'s' if len(r) > 1 else ''} not found in parameters: {', '.join(sorted(r))}",
            )


from .model import Model
