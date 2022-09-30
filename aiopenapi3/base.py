from typing import Optional, Any, List, Dict, ForwardRef

import re
import builtins
import keyword
import uuid

from pydantic import BaseModel, Field, root_validator, Extra

from .json import JSONPointer
from .errors import ReferenceResolutionError, SpecError

# from . import me

HTTP_METHODS = frozenset(["get", "delete", "head", "post", "put", "patch", "trace"])


class ObjectBase(BaseModel):
    """
    The base class for all schema objects.  Includes helpers for common schema-
    related functions.
    """

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = False
        extra = Extra.forbid


class ObjectExtended(ObjectBase):
    extensions: Optional[Any] = Field(default=None)

    @root_validator(pre=True)
    def validate_ObjectExtended_extensions(cls, values):
        """
        FIXME
        https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#specification-extensions
        :param values:
        :return: values
        """
        e = dict()
        for k, v in values.items():
            if k.startswith("x-"):
                e[k[2:]] = v
        if len(e):
            for i in e.keys():
                del values[f"x-{i}"]
            if "extensions" in values.keys():
                raise ValueError("extensions")
            values["extensions"] = e

        return values


class PathsBase(ObjectBase):
    __root__: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from pydantic import Extra

        extra = Extra.allow

    @property
    def extensions(self):
        return self._extensions

    def __getitem__(self, item):
        return self._paths[item]

    def items(self):
        return self._paths.items()

    def values(self):
        return self._paths.values()


class RootBase:
    @staticmethod
    def resolve(api, root, obj, _PathItem, _Reference):
        from . import v20, v30, v31

        def replaceSchemaReference(data):
            def replace(value):
                if not isinstance(value, SchemaBase):
                    return value
                r = getattr(value, "ref", None)
                if not r:
                    return value
                return _Reference.construct(ref=r)

            if isinstance(data, list):
                for idx, item in enumerate(data):
                    n = replace(item)
                    if item != n:
                        data[idx] = n

            elif isinstance(data, dict):
                new = dict()
                for k, v in data.items():
                    n = replace(v)  # Swagger 2.0 Schema.ref resolver …
                    if v != n:
                        v = n
                        new[k] = v
                if new:
                    data.update(new)

        if isinstance(obj, ObjectBase):
            for slot in filter(lambda x: not x.startswith("_") or x == "__root__", obj.__fields_set__):
                value = getattr(obj, slot)
                if value is None:
                    continue

                # v3.1 - Schema $ref
                if isinstance(root, (v20.root.Root, v30.root.Root, v31.root.Root)):
                    if isinstance(value, SchemaBase):
                        r = getattr(value, "ref", None)
                        if r and not isinstance(r, ReferenceBase):
                            value = _Reference.construct(ref=r)
                            setattr(obj, slot, value)

                if not isinstance(value, ReferenceBase):
                    """
                    ref fields embedded in objects -> replace the object with a Reference object

                    PathItem Ref is ambigous
                    https://github.com/OAI/OpenAPI-Specification/issues/2635
                    """
                    if isinstance(root, (v20.root.Root, v30.root.Root, v31.root.Root)):
                        if isinstance(obj, _PathItem) and slot == "ref":
                            ref = _Reference.construct(ref=value)
                            ref._target = api.resolve_jr(root, obj, ref)
                            setattr(obj, slot, ref)

                value = getattr(obj, slot)

                if isinstance(value, PathsBase):
                    value.items()
                    value = value._paths

                if isinstance(value, (str, int, float)):  # , datetime.datetime, datetime.date)):
                    continue
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
    pass


class ParameterBase:
    pass


class DiscriminatorBase:
    pass


class SchemaBase:
    def __getstate__(self):
        """
        pickle can't do the _model_type - remove from pydantic's __getstate__
        :return:
        """
        r = BaseModel.__getstate__(self)
        try:
            if "_model_type" in r["__private_attribute_values__"]:
                r["__private_attribute_values__"] = r["__private_attribute_values__"].copy()
                del r["__private_attribute_values__"]["_model_type"]
        except Exception:
            pass
        return r

    def _get_identity(self, prefix="XLS", name=None):
        if not hasattr(self, "_identity"):
            if name is None:
                name = self.title
            if name:
                n = re.sub(r"[^\w]", "_", name, flags=re.ASCII)
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
        self, names: List[str] = None, discriminators: List[DiscriminatorBase] = None, extra: "SchemaBase" = None
    ):
        from .model import Model

        if extra is None:
            self._model_type = Model.from_schema(self, names, discriminators)
            return self._model_type
        else:
            return Model.from_schema(self, names, discriminators, extra)

    def get_type(
        self,
        names: List[str] = None,
        discriminators: List[DiscriminatorBase] = None,
        extra: "SchemaBase" = None,
        fwdref: bool = False,
    ):
        try:
            if extra is None:
                return self._model_type
            else:
                return self.set_type(names, discriminators, extra)
        except AttributeError:
            if fwdref:
                if "module" in ForwardRef.__init__.__code__.co_varnames:
                    # FIXME Python < 3.9 compat
                    return ForwardRef(self._get_identity("FWD"), module="aiopenapi3.me")
                else:
                    return ForwardRef(self._get_identity("FWD"))
            else:
                return self.set_type(names, discriminators)

    def model(self, data: Dict):
        """
        Generates a model representing this schema from the given data.

        :param data: The data to create the model from.  Should match this schema.
        :type data: dict

        :returns: A new :any:`Model` created in this Schema's type from the data.
        :rtype: self.get_type()
        """
        if self.type in ("string", "number", "boolean", "integer"):
            assert len(self.properties) == 0
            t = Model.typeof(self)
            # data from Headers will be of type str
            if not isinstance(data, t):
                return t(data)
            return data
        elif self.type == "array":
            return [self.items.model(i) for i in data]
        else:
            return self.get_type().parse_obj(data)


class OperationBase:
    def _validate_path_parameters(self, pi: "PathItem", path):
        """
        Ensures that all parameters for this path are valid
        """
        assert isinstance(path, str)
        # FIXME { and } are allowed in parameter name, regex can't handle this e.g. {name}}
        path = frozenset(re.findall(r"{([a-zA-Z0-9\-\._~]+)}", path))

        op = frozenset(map(lambda x: x.name, filter(lambda c: c.in_ == "path", self.parameters)))
        pi = frozenset(map(lambda x: x.name, filter(lambda c: c.in_ == "path", pi.parameters)))

        invalid = sorted(filter(lambda x: re.match(r"^([a-zA-Z0-9\-\._~]+)$", x) is None or len(x) == 0, op | pi))
        if invalid:
            # FIXME
            #   OpenAPI does not allow RFC 6570 URI templates
            #   but name:\d+ may be valid though
            raise SpecError(f"Parameter names are invalid: {invalid}")

        r = (op | pi) - path
        if r:
            raise SpecError(f"Parameter name{'s' if len(r) > 1 else ''} not found in path: {', '.join(sorted(r))}")

        r = path - (op | pi)
        if r:
            raise SpecError(
                f"Parameter name{'s' if len(r) > 1 else ''} not found in parameters: {', '.join(sorted(r))}"
            )


from .model import Model
