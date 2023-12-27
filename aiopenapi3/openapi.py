import sys
import typing

from typing import List, Dict, Set, Callable, Tuple, Any, Union, cast, Optional, Type, ForwardRef
import inspect
import logging
import copy
import pickle
import random

if sys.version_info >= (3, 9):
    import pathlib
else:
    import pathlib3x as pathlib


if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard


import httpx
import yarl
from pydantic import BaseModel

from aiopenapi3.v30.general import Reference
import aiopenapi3.request
from .json import JSONReference
from . import v20
from . import v30
from . import v31
from . import log
from .request import OperationIndex, HTTP_METHODS
from .errors import ReferenceResolutionError
from .loader import Loader, NullLoader
from .plugin import Plugin, Plugins
from .base import RootBase, ReferenceBase, SchemaBase, OperationBase, DiscriminatorBase
from .request import RequestBase
from .v30.paths import Operation

if typing.TYPE_CHECKING:
    from ._types import (
        RootType,
        JSON,
        PathItemType,
        SchemaType,
        OperationType,
        ReferenceType,
        RequestType,
        HTTPMethodType,
    )


def has_components(y: Optional["RootType"]) -> TypeGuard[Union[v30.Root, v31.Root]]:
    #    return all([typing.cast("RootType", y), typing.cast("RootType", y).components])
    #    return isinstance(y, (v30.Root, v31.Root))
    #    return all([y, y.components])
    if y is None:
        return False
    if y.components is None:
        return False
    return True


def is_schema(v: Tuple[str, "SchemaType"]) -> TypeGuard["SchemaType"]:
    return isinstance(v[1], (v20.Schema, v30.Schema, v31.Schema))


class OpenAPI:
    log = logging.getLogger("aiopenapi3.OpenAPI")
    #    _root: Union[v20.Root, v30.Root, v31.Root] | None
    _root: "RootType"

    @property
    def paths(self):
        return self._root.paths

    @property
    def components(self):
        return self._root.components

    @property
    def info(self):
        return self._root.info

    @property
    def openapi(self):
        return self._root.openapi

    @property
    def servers(self):
        return self._root.servers

    @classmethod
    def load_sync(
        cls,
        url,
        session_factory: Callable[..., httpx.Client] = httpx.Client,
        loader: Optional[Loader] = None,
        plugins: Optional[List[Plugin]] = None,
        use_operation_tags: bool = False,
    ) -> "OpenAPI":
        """
        Create a synchronous OpenAPI object from a description document.

        :param url: the url of the description document
        :param session_factory: used to create the session for http/s io
        :param loader: the backend to access referenced description documents
        :param plugins: potions to cure defects in the description document or requests/responses
        :param use_operation_tags: honor tags
        """

        with session_factory() as client:
            resp = client.get(url)
        return cls._load_response(url, resp, session_factory, loader, plugins, use_operation_tags)

    @classmethod
    async def load_async(
        cls,
        url: str,
        session_factory: Callable[..., httpx.AsyncClient] = httpx.AsyncClient,
        loader: Optional[Loader] = None,
        plugins: Optional[List[Plugin]] = None,
        use_operation_tags: bool = False,
    ) -> "OpenAPI":
        """
        Create an asynchronous OpenAPI object from a description document.

        :param url: the url of the description document
        :param session_factory: used to create the session for http/s io
        :param loader: the backend to access referenced description documents
        :param plugins: potions to cure defects in the description document or requests/responses
        :param use_operation_tags: honor tags
        """
        async with session_factory() as client:
            resp = await client.get(url)
        return cls._load_response(url, resp, session_factory, loader, plugins, use_operation_tags)

    @classmethod
    def _load_response(cls, url, resp, session_factory, loader, plugins, tags):
        if resp.is_redirect:
            raise ValueError(f'Redirect to {resp.headers.get("Location","")}')
        return cls.loads(url, resp.text, session_factory, loader, plugins, tags)

    @classmethod
    def load_file(
        cls,
        url: str,
        path: Union[str, pathlib.Path, yarl.URL],
        session_factory: Callable[..., Union[httpx.AsyncClient, httpx.Client]] = httpx.AsyncClient,
        loader: Optional[Loader] = None,
        plugins: Optional[List[Plugin]] = None,
        use_operation_tags: bool = False,
    ) -> "OpenAPI":
        """
        Create an OpenAPI object from a description document file.


        :param url: the fictive url of the description document
        :param path: description document location
        :param session_factory: used to create the session for http/s io, defaults to use an AsyncClient
        :param loader: the backend to access referenced description documents
        :param plugins: potions to cure defects in the description document or requests/responses
        :param use_operation_tags: honor tags
        """
        assert loader
        if not isinstance(path, yarl.URL):
            path = yarl.URL(str(path))
        data = loader.load(Plugins(plugins or []), path)
        return cls.loads(url, data, session_factory, loader, plugins, use_operation_tags)

    @classmethod
    def loads(
        cls,
        url: str,
        data: str,
        session_factory: Callable[..., Union[httpx.AsyncClient, httpx.Client]] = httpx.AsyncClient,
        loader: Optional[Loader] = None,
        plugins: Optional[List[Plugin]] = None,
        use_operation_tags: bool = False,
    ) -> "OpenAPI":
        """

        :param url: the url of the description document
        :param data: description document
        :param session_factory: used to create the session for http/s io, defaults to use an AsyncClient
        :param loader: the backend to access referenced description documents
        :param plugins: potions to cure defects in the description document or requests/responses
        :param use_operation_tags: honor tags
        """
        if loader is None:
            loader = NullLoader()
        data = loader.parse(Plugins(plugins or []), yarl.URL(url), data)
        return cls(url, data, session_factory, loader, plugins, use_operation_tags)

    @classmethod
    def _parse_obj(cls, document: "JSON") -> "RootType":
        document = cast(Dict[str, Any], document)
        if (version := document.get("openapi", None)) is not None:
            v = list(map(int, version.split(".")))
            if v[0] == 3:
                if v[1] == 0:
                    return v30.Root.model_validate(document)
                elif v[1] == 1:
                    return v31.Root.model_validate(document)
                else:
                    raise ValueError(f"openapi version 3.{v[1]} not supported")
            else:
                raise ValueError(f"openapi major version {version} not supported")

        if (version := document.get("swagger", None)) is not None:
            v = list(map(int, version.split(".")))
            if v[0] == 2 and v[1] == 0:
                return v20.Root.model_validate(document)
            else:
                raise ValueError(f"swagger version {version} not supported")
        else:
            raise ValueError("missing openapi/swagger field")

    def __init__(
        self,
        url: str,
        document: "JSON",
        session_factory: Callable[..., Union[httpx.Client, httpx.AsyncClient]] = httpx.AsyncClient,
        loader: Optional[Loader] = None,
        plugins: Optional[List[Plugin]] = None,
        use_operation_tags: bool = True,
    ) -> None:
        """
        Creates a new OpenAPI document from a loaded spec file.  This is
        overridden here because we need to specify the path in the parent
        class' constructor.

        :param url: the url of the description document
        :param document: The raw OpenAPI file loaded into python
        :param session_factory: default uses new session for each call, supply your own if required otherwise.
        :param loader: the Loader for the description document(s)
        :param plugins: list of plugins
        :param use_operation_tags: honor tags
        """
        self._base_url: yarl.URL = yarl.URL(url)

        self._session_factory: Callable[..., Union[httpx.Client, httpx.AsyncClient]] = session_factory

        self.loader: Optional[Loader] = loader
        """
        Loader - loading referenced documents
        """

        self._createRequest: Callable[
            ["OpenAPI", str, str, "OperationType", Optional[List["ServerType"]]], "RequestBase"
        ]
        """
        creates the Async/Request for the protocol required
        """

        self._max_response_content_length = 8 * (1024**2)
        """
        Maximum Content-Length in Responses - default to 8 MBytes
        """

        self._security: Dict[str, Tuple[str]] = dict()
        """
        authorization informations
        e.g. {"BasicAuth": ("user","secret")}
        """

        self._documents: Dict[yarl.URL, "RootType"] = dict()
        """
        the related documents
        """

        self._server_variables: Dict[str, str] = dict()
        """
        server variable mapping
        """

        self._server_select: Callable[[List["ServerType"]], "ServerType"] = random.choice

        self._init_plugins(plugins)
        """
        the plugin interface allows taking care of defects in description documents and implementations
        """

        log.init()
        self.log = logging.getLogger("aiopenapi3.OpenAPI")

        """
        Document Plugins get called via OpenAPI.load… - this is processed already
        """
        self._root = self._parse_obj(document)

        self._documents[self._base_url] = self._root

        self._init_session_factory(session_factory)
        self._init_references()
        only_required = self._init_operationindex(use_operation_tags)
        self._init_schema_types(only_required)

        self.plugins.init.initialized(initialized=self._root)

    def _init_plugins(self, plugins):
        for i in plugins or []:
            i.api = self
        self.plugins = Plugins(plugins or [])

    def _init_session_factory(self, session_factory):
        if issubclass(getattr(session_factory, "__annotations__", {}).get("return", None.__class__), httpx.Client) or (
            type(session_factory) == type and issubclass(session_factory, httpx.Client)
        ):
            if isinstance(self._root, v20.Root):
                self._createRequest = v20.Request
            elif isinstance(self._root, (v30.Root, v31.Root)):
                self._createRequest = v30.Request
            else:
                raise ValueError(self._root)
        elif issubclass(
            getattr(session_factory, "__annotations__", {}).get("return", None.__class__), httpx.AsyncClient
        ) or (type(session_factory) == type and issubclass(session_factory, httpx.AsyncClient)):
            if isinstance(self._root, v20.Root):
                self._createRequest = v20.AsyncRequest
            elif isinstance(self._root, (v30.Root, v31.Root)):
                self._createRequest = v30.AsyncRequest
            else:
                raise ValueError(self._root)
        else:
            raise ValueError("invalid return value annotation for session_factory")

    def _init_references(self):
        self._root._resolve_references(self)

        processed = set()
        while True:
            values = {id(x): x for x in self._documents.values()}
            names = {id(v): k for k, v in self._documents.items()}
            todo = set(values.keys()) - processed
            if not todo:
                break
            for i in todo:
                #                print(names[i])
                try:
                    values[i]._resolve_references(self)
                except ReferenceResolutionError as e:
                    e.document = names[i]
                    raise
            processed = set(values.keys())
        return

    #        for i in self._documents.values():
    #            i._resolve_references(self)

    def _init_operationindex(self, use_operation_tags: bool) -> bool:
        if (p := self.plugins.init.paths(initialized=self._root, paths=self.paths).paths) is not None:
            self._root.paths = p

        if isinstance(self._root, v20.Root):
            if self.paths:
                obj: "PathItemType"
                for path, obj in self.paths.items():
                    for m in obj.model_fields_set & HTTP_METHODS:
                        op: "Operation" = getattr(obj, m)
                        op._validate_path_parameters(obj, path, (m, cast(str, op.operationId)))
                        if op.operationId is None:
                            continue
                        for r, response in op.responses.items():
                            if isinstance(response, Reference):
                                continue
                            if response.headers:
                                for h in response.headers.values():
                                    h = cast(v20.Header, h)
                                    items = v20.Schema(type=h.items.type) if h.items else None
                                    h._schema = v20.Schema(type=h.type, items=items)

                            if isinstance(response.schema_, (v20.Schema,)):
                                response.schema_._get_identity("OP", f"{path}.{m}.{r}")

        elif isinstance(self._root, (v30.Root, v31.Root)):
            allschemas = [
                x.components.schemas
                for x in filter(has_components, self._documents.values())
                if x.components is not None and isinstance(x.components.schemas, SchemaBase)
            ]

            for schemas in allschemas:
                name: str
                schema: "SchemaType"
                for name, schema in filter(is_schema, schemas.items()):
                    schema._get_identity(name=name, prefix="OP")

            if self.paths:
                for path, obj in self.paths.items():
                    if obj.ref:
                        obj = cast("PathItemType", cast(ReferenceBase, obj.ref)._target)
                    for m in obj.model_fields_set & HTTP_METHODS:
                        op = getattr(obj, m)
                        op._validate_path_parameters(obj, path, (m, typing.cast(str, op.operationId)))
                        if op.operationId is None:
                            continue
                        for r, response in op.responses.items():
                            if isinstance(response, Reference):
                                continue
                            assert response.content is not None
                            for c, content in response.content.items():
                                if content.schema_ is None:
                                    continue
                                if isinstance(content.schema_, (v30.Schema, v31.Schema)):
                                    content.schema_._get_identity("OP", f"{path}.{m}.{r}.{c}")
            else:
                if isinstance(self._root, v30.Root):
                    self._root.paths = v30.Paths(paths={}, extensions={})
                elif isinstance(self._root, v31.Root):
                    self._root.paths = v31.Paths(paths={}, extensions={})
                else:
                    raise ValueError(self._root)
        else:
            raise ValueError(self._root)

        self._operationindex = OperationIndex(self, use_operation_tags)
        return p is None

    @staticmethod
    def _get_combined_attributes(schema):
        """Combine attributes from the schema."""
        return (
            getattr(schema, "oneOf", [])  # Swagger compat
            + (
                list(getattr(schema, "discriminator").mapping.values())
                if isinstance(getattr(schema, "discriminator", {}), DiscriminatorBase)
                else []
            )
            + getattr(schema, "anyOf", [])  # Swagger compat
            + schema.allOf
            + list(schema.properties.values())
            + ([schema.items] if schema.type == "array" and schema.items and not isinstance(schema, list) else [])
            + (schema.items if schema.type == "array" and schema.items and isinstance(schema, list) else [])
        )

    @classmethod
    def _process_schema_attributes(cls, schema: "SchemaType", processed: Set[int]) -> Dict[int, "SchemaType"]:
        """Process attributes of a schema and filter out the processed ones."""
        combined_attributes = cls._get_combined_attributes(schema)
        return {
            id(item._target)
            if isinstance(item, ReferenceBase)
            else id(item): item._target
            if isinstance(item, ReferenceBase)
            else item
            for item in combined_attributes
            if isinstance(item, (ReferenceBase, SchemaBase)) and id(item) not in processed
        }

    @classmethod
    def _iterate_schemas(cls, schemas: Dict[int, "SchemaType"], next_set: Set[int], processed: Set[int]) -> Set[int]:
        """Iteratively collect all schemas related to the starting set."""
        while next_set:
            processed.update(next_set)
            # Using dictionary comprehension to combine the results,
            # which seems more efficient than ChainMap
            new = {k: v for i in next_set for k, v in cls._process_schema_attributes(schemas[i], processed).items()}
            next_set = set(new.keys()) - processed
            schemas.update(new)
            processed.update(next_set)
        return processed

    def _init_schema_types_collect(self, only_required: bool) -> Dict[str, "SchemaType"]:
        byname: Dict[str, "SchemaType"] = dict()

        def is_schema(v: Tuple[str, "SchemaType"]) -> bool:
            return isinstance(v[1], (v20.Schema, v30.Schema, v31.Schema))

        if isinstance(self._root, v20.Root):
            documents = cast(List[v20.Root], self._documents.values())
            # Schema
            if only_required is False:
                for byid in map(lambda x: x.definitions, documents):
                    assert byid is not None and isinstance(byid, dict)
                    for name, schema in filter(is_schema, byid.items()):
                        byname[schema._get_identity(name=name)] = schema

                # PathItems
                for path, obj in (self.paths or dict()).items():
                    for m in obj.model_fields_set & HTTP_METHODS:
                        op: Operation = getattr(obj, m)

                        for r, response in op.responses.items():
                            if isinstance(response, ReferenceBase):
                                response = response._target
                            if isinstance(response, (v20.paths.Response)):
                                if isinstance(response.schema_, (v20.Schema, v31.Schema)):
                                    name = response.schema_._get_identity("PI", f"{path}.{m}.{r}")
                                    byname[name] = response.schema_
                            else:
                                raise TypeError(f"{type(response)} at {path}")

            # Response
            for byid in map(lambda x: x.responses, documents):
                assert byid is not None and isinstance(byid, dict)
                for name, response in filter(is_schema, byid.items()):
                    assert response.schema_
                    byname[response.schema_._get_identity(name=name)] = response.schema_

        elif isinstance(self._root, (v30.Root, v31.Root)):
            # Schema
            documents = cast(Union[List[v30.Root], List[v31.Root]], self._documents.values())
            components = [x.components for x in filter(has_components, documents) if x.components is not None]
            assert components is not None
            if only_required is False:
                for byid in map(lambda x: x.schemas, components):
                    assert byid is not None and isinstance(byid, dict)
                    for name, schema in filter(is_schema, byid.items()):
                        byname[schema._get_identity(name=name)] = schema

            # PathItems
            for path, obj in (self.paths or dict()).items():
                for m in obj.model_fields_set & HTTP_METHODS:
                    op: Operation = getattr(obj, m)

                    for parameter in op.parameters + obj.parameters:
                        if parameter.schema_:
                            if isinstance(parameter.schema_, ReferenceBase):
                                schema = parameter.schema_._target
                            else:
                                schema = parameter.schema_
                            assert schema is not None
                            name = schema._get_identity("I2", f"{path}.{m}.{parameter.name}")
                            byname[name] = schema
                        else:
                            for key, mto in parameter.content.items():
                                if isinstance(mto.schema_, ReferenceBase):
                                    schema = mto.schema_._target
                                else:
                                    schema = mto.schema_
                                assert schema is not None
                                name = schema._get_identity("I2", f"{path}.{m}.{parameter.name}.{key}")
                                byname[name] = schema

                    if op.requestBody:
                        for mt, mto in op.requestBody.content.items():
                            if mto.schema_ is None:
                                continue
                            byname[mto.schema_._get_identity("B")] = mto.schema_

                    for r, response in op.responses.items():
                        if isinstance(response, ReferenceBase):
                            response = response._target
                        if isinstance(response, (v30.paths.Response, v31.paths.Response)):
                            assert response.content is not None
                            for mt, mto in response.content.items():
                                if mto.schema_ is None:
                                    continue
                                name = mto.schema_._get_identity("I2", f"{path}.{m}.{r}.{mt}")
                                byname[name] = mto.schema_
                        else:
                            raise TypeError(f"{type(response)} at {path}")

            # Response
            if only_required is False:
                for responses in map(lambda x: x.responses, components):
                    assert responses is not None
                    for rname, response in responses.items():
                        for mt, mto in response.content.items():
                            if mto.schema_ is None:
                                continue
                            byname[mto.schema_._get_identity("R")] = mto.schema_

        byname = self.plugins.init.schemas(initialized=self._root, schemas=byname).schemas
        return byname

    def _init_schema_types(self, only_required: bool) -> None:
        byname: Dict[str, "SchemaType"] = self._init_schema_types_collect(only_required)
        byid: Dict[int, "SchemaType"] = {id(i): i for i in byname.values()}
        data: Set[int] = set(byid.keys())
        todo: Set[int] = self._iterate_schemas(byid, data, set())
        types: Dict[str, Union[ForwardRef, Type[BaseModel], Type[int], Type[str], Type[float], Type[bool]]] = dict()

        """
        Due to Plugins (e.g. Cull/Reduce) byname may be incomplete
        """
        resolved: List["SchemaType"] = list(
            map(lambda x: byid[x]._target if isinstance(byid[x], ReferenceBase) else byid[x], todo | data)
        )
        self.plugins.init.resolved(initialized=self._root, resolved=resolved)

        # print(f"{len(todo | data)} {only_required=}")
        for i in todo | data:
            b = byid[i]
            name = b._get_identity("X")
            types[name] = b.get_type()
            for idx, j in enumerate(b._model_types):
                types[f"{name}.c{idx}"] = j

        # print(f"{len(types)}")
        for name, schema in types.items():
            if not (inspect.isclass(schema) and issubclass(schema, BaseModel)):
                # primitive types: str, int …
                continue
            try:
                schema.model_rebuild(_types_namespace={"__types": types})
                thes = byname.get(name, None)
                if thes is not None:
                    for v in byid[id(thes)]._model_types:
                        v.model_rebuild(_types_namespace={"__types": types})
            except Exception as e:
                raise e

    @property
    def url(self) -> yarl.URL:
        if isinstance(self._root, v20.Root):
            base = yarl.URL(self._base_url)
            scheme = host = port = path = None

            for i in ["https", "http"]:
                if not self._root.schemes or i not in self._root.schemes:
                    continue
                scheme = i
                break
            else:
                scheme = base.scheme

            if self._root.host:
                v = yarl.URL(f"{scheme}://{self._root.host}")
                host, port = v.host, v.explicit_port
            else:
                host, port = base.host, base.port

            path = self._root.basePath or base.path

            r = yarl.URL.build(scheme=scheme, host=host, port=port, path=path)
            return r
        elif isinstance(self._root, (v30.Root, v31.Root)):
            server: "ServerType" = self._server_select(self._root.servers)
            return self._base_url.join(yarl.URL(server.createUrl(self._server_variables)))

    def authenticate(self, *args, **kwargs):
        """
        authenticate, multiple authentication schemes can be used simultaneously serving "or" or "and"
        authentication schemes

        :param args: None to remove all credentials / reset the authorizations
        :param kwargs: scheme=value
        """
        if len(args) == 1 and args[0] == None:
            self._security = dict()

        schemes = frozenset(kwargs.keys())

        if isinstance(self._root, v20.Root):
            v = schemes - frozenset(SecuritySchemes := self._root.securityDefinitions)
        elif isinstance(self._root, (v30.Root, v31.Root)):
            v = schemes - frozenset(SecuritySchemes := self._root.components.securitySchemes)
        else:
            raise TypeError(self._root)  # noqa

        if v:
            raise ValueError("{} does not accept security schemes {}".format(self.info.title, sorted(v)))

        for security_scheme, value in kwargs.items():
            if value is None:
                continue
            ss = SecuritySchemes[security_scheme].root
            try:
                ss.validate_authentication_value(value)
            except Exception as e:
                raise ValueError(f"Invalid parameter for SecurityScheme {security_scheme} {ss.type}") from e

        for security_scheme, value in kwargs.items():
            if value is None:
                del self._security[security_scheme]
            else:
                self._security[security_scheme] = value

    def _load(self, url: yarl.URL):
        self.log.debug(f"Downloading Description Document {url} using {self.loader} …")
        assert self.loader
        data = self.loader.get(self.plugins, url)
        return self._parse_obj(data)

    @property
    def _(self) -> OperationIndex:
        """
        the sad smiley interface
        access operations by operationId
        """
        return self._operationindex

    def createRequest(self, operationId: Union[str, Tuple[str, "HTTPMethodType"]]) -> "RequestType":
        """
        create a Request

        lookup the Operation by operationId or path,method

        the type of Request returned depends on the session_factory of the OpenAPI object and OpenAPI/Swagger version

        :param operationId: the operationId or tuple(path,method)
        :return: the returned Request is either :class:`aiopenapi3.request.RequestBase` or -
            in case of a httpx.AsyncClient session_factory - :class:`aiopenapi3.request.AsyncRequestBase`
        """
        operation: Optional["OperationType"] = None
        request: Optional["RequestType"] = None
        try:
            if isinstance(operationId, str):
                *tags, opn = operationId.split(".")
                opi: OperationIndex = self._operationindex
                for i in tags:
                    opi = getattr(opi, i)
                _, _, operation, _ = opi._operations[opn]
                request = getattr(opi, opn)
                assert isinstance(request, aiopenapi3.request.RequestBase)
            else:
                path, method = operationId
                pathitem = self._root.paths[path]
                if pathitem.ref:
                    pathitem = pathitem.ref._target

                operation = getattr(pathitem, method)
                assert operation is not None
                if isinstance(self._root, v20.Root):
                    servers = None
                elif isinstance(self._root, (v30.Root, v31.Root)):
                    servers = operation.servers or pathitem.servers or self.servers
                else:
                    raise TypeError(self._root)
                request = self._createRequest(self, method, path, operation, servers)
            assert request is not None
            return request
        except Exception as e:
            raise aiopenapi3.errors.RequestError(operation, request, None, {}) from e

    def resolve_jr(self, root: RootBase, obj, value: Reference):
        """
        Resolve a `JSON Reference<https://datatracker.ietf.org/doc/html/draft-pbryan-zyp-json-ref-03>`_ in our documents

        :param root:
        :param obj:
        :param value:
        :return:
        """
        urlstr, jp = JSONReference.split(value.ref)
        if urlstr != "":
            url: yarl.URL = yarl.URL(urlstr)
            if url not in self._documents:
                self.log.debug(f"Resolving {value.ref} - Description Document {url} unknown …")
                try:
                    self._documents[url] = self._load(url)
                except FileNotFoundError:
                    err = ReferenceResolutionError(f"not found {url}")
                    for k, v in self._documents.items():
                        if v == root:
                            err.document = k
                            break
                    raise err

            root = self._documents[url]

        try:
            while True:
                r = root.resolve_jp(jp)
                if isinstance(r, ReferenceBase):
                    """
                    returned node is a unresolved reference
                    resolve & retry
                    """
                    v = root.resolve_jp(r.ref)
                    if not isinstance(v, ReferenceBase) or v.ref == r.ref:
                        return r
                    continue
                return r
        except ReferenceResolutionError as e:
            # add metadata to the error
            e.element = obj
            for k, v in self._documents.items():
                if v == root:
                    e.document = k
                    break
            raise

    def __copy__(self) -> "OpenAPI":
        """
        shallow copy of an API object allows for a quick & low resource way to interface multiple
        services using the same api instad of creating a new OpenAPI object from the description document for each

        after setting the _base_url & .authenticate() it is ready to use
        :return: aiopenapi3.OpenAPI
        """
        api = OpenAPI("/test.yaml", {"openapi": "3.0.0", "info": {"title": "", "version": ""}})
        api._root = self._root
        api.plugins = self.plugins
        api._documents = self._documents
        api._security = copy.deepcopy(self._security)
        api._createRequest = self._createRequest
        api._session_factory = self._session_factory
        api.loader = self.loader
        return api

    def clone(self, baseurl: Optional[yarl.URL] = None) -> "OpenAPI":
        """
        shallwo copy the api object
        optional set a base url

        :param baseurl:
        """
        api = copy.copy(self)
        if baseurl:
            api._base_url = baseurl
        return api

    @staticmethod
    def cache_load(path: pathlib.Path, plugins: Optional[List[Plugin]] = None, session_factory=None) -> "OpenAPI":
        """
        read a pickle api object from path and init the schema types

        :param path: cache path
        """
        with path.open("rb") as f:
            api = pickle.load(f)

        api._init_plugins(plugins)

        api._init_schema_types(only_required=False)

        if session_factory is not None:
            api._session_factory = session_factory

        api.plugins.init.initialized(initialized=api._root)

        return api

    def cache_store(self, path: pathlib.Path) -> None:
        """
        write the pickled api object to Path
        to dismiss potentially local defined objects loader, plugins and the session_factory are dropped

        :param path: cache path
        """

        restore = (self.loader, self.plugins, self._session_factory)
        self.loader = self._session_factory = self.plugins = None  # type: ignore[assignment]
        with path.open("wb") as f:
            pickle.dump(self, f)
        self.loader, self.plugins, self._session_factory = restore
