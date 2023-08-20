import copy
import sys

if sys.version_info >= (3, 9):
    import pathlib
else:
    import pathlib3x as pathlib

from typing import List, Dict, Set, Union, Callable, Tuple, Any
import collections
import inspect
import logging
import copy
import pickle

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
from .base import RootBase, ReferenceBase, SchemaBase
from .v30.paths import Operation


class OpenAPI:
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
        session_factory: Callable[[], httpx.Client] = httpx.Client,
        loader=None,
        plugins: List[Plugin] = None,
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
        session_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
        loader: Loader = None,
        plugins: List[Plugin] = None,
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
        session_factory: Callable[[], Union[httpx.AsyncClient, httpx.Client]] = httpx.AsyncClient,
        loader: Loader = None,
        plugins: List[Plugin] = None,
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
        session_factory: Callable[[], Union[httpx.AsyncClient, httpx.Client]] = httpx.AsyncClient,
        loader=None,
        plugins: List[Plugin] = None,
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

    def _parse_obj(self, document: Dict[str, Any]) -> RootBase:
        v = document.get("openapi", None)
        if v:
            v = list(map(int, v.split(".")))
            if v[0] == 3:
                if v[1] == 0:
                    return v30.Root.model_validate(document)
                elif v[1] == 1:
                    return v31.Root.model_validate(document)
                else:
                    raise ValueError(f"openapi version 3.{v[1]} not supported")
            else:
                raise ValueError(f"openapi major version {v[0]} not supported")
            return

        v = document.get("swagger", None)
        if v:
            v = list(map(int, v.split(".")))
            if v[0] == 2 and v[1] == 0:
                return v20.Root.model_validate(document)
            else:
                raise ValueError(f"swagger version {'.'.join(v)} not supported")
        else:
            raise ValueError("missing openapi/swagger field")

    def __init__(
        self,
        url: str,
        document: Dict[str, Any],
        session_factory: Callable[[], Union[httpx.Client, httpx.AsyncClient]] = httpx.AsyncClient,
        loader: Loader = None,
        plugins: List[Plugin] = None,
        use_operation_tags: bool = True,
    ) -> "OpenAPI":
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

        self._session_factory: Callable[[], Union[httpx.Client, httpx.AsyncClient]] = session_factory

        self.loader: Loader = loader
        """
        Loader - loading referenced documents
        """

        self._createRequest: Callable[["OpenAPI", str, str, "Operation"], "RequestBase"] = None
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

        self._documents: Dict[yarl.URL, RootBase] = dict()
        """
        the related documents
        """

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
        self._init_operationindex(use_operation_tags)
        self._init_schema_types()

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

    def _init_operationindex(self, use_operation_tags: bool):
        self._root.paths = self.plugins.init.paths(initialized=self._root, paths=self.paths).paths

        if isinstance(self._root, v20.Root):
            if self.paths:
                for path, obj in self.paths.items():
                    for m in obj.model_fields_set & HTTP_METHODS:
                        op = getattr(obj, m)
                        op._validate_path_parameters(obj, path, (m, op.operationId))
                        if op.operationId is None:
                            continue
                        for r, response in op.responses.items():
                            if isinstance(response, Reference):
                                continue
                            if response.headers:
                                for h in response.headers.values():
                                    items = v20.Schema(type=h.items.type) if h.items else None
                                    h._schema = v20.Schema(type=h.type, items=items)

                            if isinstance(response.schema_, (v20.Schema,)):
                                response.schema_._get_identity("OP", f"{path}.{m}.{r}")

        elif isinstance(self._root, (v30.Root, v31.Root)):
            allschemas = [
                x.components.schemas for x in filter(lambda y: all([y, y.components]), self._documents.values())
            ]
            for schemas in allschemas:
                for name, schema in filter(lambda v: isinstance(v[1], SchemaBase), schemas.items()):
                    schema._get_identity(name=name, prefix="OP")

            if self.paths:
                for path, obj in self.paths.items():
                    if obj.ref:
                        obj = obj.ref._target
                    for m in obj.model_fields_set & HTTP_METHODS:
                        op = getattr(obj, m)
                        op._validate_path_parameters(obj, path, (m, op.operationId))
                        if op.operationId is None:
                            continue
                        for r, response in op.responses.items():
                            if isinstance(response, Reference):
                                continue
                            for c, content in response.content.items():
                                if content.schema_ is None:
                                    continue
                                if isinstance(content.schema_, (v30.Schema, v31.Schema)):
                                    content.schema_._get_identity("OP", f"{path}.{m}.{r}.{c}")
            else:
                self._root.paths = dict()

        else:
            raise ValueError(self._root)

        self._operationindex = OperationIndex(self, use_operation_tags)

    @staticmethod
    def _iterate_schemas(schemas: Dict[int, SchemaBase], next: Set[int], processed: Set[int]):
        """
        recursively collect all schemas related to the starting set
        """
        if not next:
            return processed

        processed.update(next)

        new = collections.ChainMap(
            *[
                dict(
                    filter(
                        lambda z: z[0] not in processed,
                        map(
                            lambda y: (id(y._target), y._target) if isinstance(y, ReferenceBase) else (id(y), y),
                            filter(
                                lambda x: isinstance(x, (ReferenceBase, SchemaBase)),
                                getattr(schemas[i], "oneOf", [])  # Swagger compat
                                + getattr(schemas[i], "anyOf", [])  # Swagger compat
                                + schemas[i].allOf
                                + list(schemas[i].properties.values())
                                + (
                                    [schemas[i].items]
                                    if schemas[i].type == "array"
                                    and schemas[i].items
                                    and not isinstance(schemas[i], list)
                                    else []
                                )
                                + (
                                    schemas[i].items
                                    if schemas[i].type == "array" and schemas[i].items and isinstance(schemas[i], list)
                                    else []
                                ),
                            ),
                        ),
                    )
                )
                for i in next
            ]
        )

        sets = new.keys()
        schemas.update(new)
        processed.update(sets)

        return OpenAPI._iterate_schemas(schemas, sets, processed)

    def _init_schema_types_collect(self):
        byname: Dict[str, SchemaBase] = dict()

        if isinstance(self._root, v20.Root):
            # Schema
            for byid in map(lambda x: x.definitions, self._documents.values()):
                for name, schema in filter(lambda v: isinstance(v[1], SchemaBase), byid.items()):
                    byname[schema._get_identity(name=name)] = schema
            # Request

            # Response
            for byid in map(lambda x: x.responses, self._documents.values()):
                for name, response in filter(lambda v: isinstance(v[1].schema_, SchemaBase), byid.items()):
                    byname[response.schema_._get_identity(name=name)] = response.schema_

        elif isinstance(self._root, (v30.Root, v31.Root)):
            # Schema
            components = [x.components for x in filter(lambda y: all([y, y.components]), self._documents.values())]
            for byid in map(lambda x: x.schemas, components):
                for name, schema in filter(lambda v: isinstance(v[1], SchemaBase), byid.items()):
                    byname[schema._get_identity(name=name)] = schema

            # Request
            for path, obj in (self.paths or dict()).items():
                for m in obj.model_fields_set & HTTP_METHODS:
                    op = getattr(obj, m)

                    if op.requestBody:
                        for content_type, request in op.requestBody.content.items():
                            if request.schema_ is None:
                                continue
                            byname[request.schema_._get_identity("B")] = request.schema_

                    for r, response in op.responses.items():
                        if isinstance(response, ReferenceBase):
                            response = response._target
                        if isinstance(response, (v30.paths.Response, v31.paths.Response)):
                            for c, content in response.content.items():
                                if content.schema_ is None:
                                    continue
                                if isinstance(content.schema_, (v30.Schema, v31.Schema)):
                                    name = content.schema_._get_identity("I2", f"{path}.{m}.{r}.{c}")
                                    byname[name] = content.schema_
                        else:
                            raise TypeError(f"{type(response)} at {path}")

            # Response
            for responses in map(lambda x: x.responses, components):
                for rname, response in responses.items():
                    for content_type, media_type in response.content.items():
                        if media_type.schema_ is None:
                            continue
                        byname[media_type.schema_._get_identity("R")] = media_type.schema_

        byname = self.plugins.init.schemas(initialized=self._root, schemas=byname).schemas
        return byname

    def _init_schema_types(self):
        byname: Dict[str, SchemaBase] = self._init_schema_types_collect()
        byid: Dict[int, SchemaBase] = {id(i): i for i in byname.values()}
        data: Set[int] = set(byid.keys())
        todo: Set[int] = self._iterate_schemas(byid, data, set())

        types: Dict[int, "BaseModel"] = dict()
        for i in todo | data:
            b = byid[i]
            name = b._get_identity("X")
            types[name] = b.get_type()
            for idx, i in enumerate(b._model_types):
                types[f"{name}.c{idx}"] = i

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
    def url(self):
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
                host, _, port = self._root.host.partition(":")
                port = None if port == "" else port
            else:
                host, port = base.host, base.port

            path = self._root.basePath or base.path

            r = yarl.URL.build(scheme=scheme, host=host, port=port, path=path)
            return r
        elif isinstance(self._root, (v30.Root, v31.Root)):
            return self._base_url.join(yarl.URL(self._root.servers[0].url))

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
        data = self.loader.get(self.plugins, url)
        return self._parse_obj(data)

    @property
    def _(self) -> OperationIndex:
        """
        the sad smiley interface
        access operations by operationId
        """
        return self._operationindex

    def createRequest(self, operationId: Union[str, Tuple[str, str]]) -> aiopenapi3.request.RequestBase:
        """
        create a Request

        lookup the Operation by operationId or path,method

        the type of Request returned depends on the session_factory of the OpenAPI object and OpenAPI/Swagger version

        :param operationId: the operationId or tuple(path,method)
        :return: the returned Request is either :class:`aiopenapi3.request.RequestBase` or -
            in case of a httpx.AsyncClient session_factory - :class:`aiopenapi3.request.AsyncRequestBase`
        """
        try:
            if isinstance(operationId, str):
                p = operationId.split(".")
                req = self._operationindex
                for i in p:
                    req = getattr(req, i)
                assert isinstance(req, aiopenapi3.request.RequestBase)
            else:
                path, method = operationId
                pathitem = self._root.paths[path]
                if pathitem.ref:
                    pathitem = pathitem.ref._target
                op = getattr(pathitem, method)
                req = self._createRequest(self, method, path, op)
            return req
        except Exception as e:
            raise aiopenapi3.errors.RequestError(None, None, None, None) from e

    def resolve_jr(self, root: RootBase, obj, value: Reference):
        """
        Resolve a `JSON Reference<https://datatracker.ietf.org/doc/html/draft-pbryan-zyp-json-ref-03>`_ in our documents

        :param root:
        :param obj:
        :param value:
        :return:
        """
        url, jp = JSONReference.split(value.ref)
        if url != "":
            url = yarl.URL(url)
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
            return root.resolve_jp(jp)
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

    def clone(self, baseurl: yarl.URL = None) -> "OpenAPI":
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
    def cache_load(path: pathlib.Path, plugins: List[Plugin] = None, session_factory=None) -> "OpenAPI":
        """
        read a pickle api object from path and init the schema types

        :param path: cache path
        """
        with path.open("rb") as f:
            api = pickle.load(f)

        api._init_plugins(plugins)

        api._init_schema_types()

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
        self.loader = self._session_factory = self.plugins = None
        with path.open("wb") as f:
            pickle.dump(self, f)
        self.loader, self.plugins, self._session_factory = restore
