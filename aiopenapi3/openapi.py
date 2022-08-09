import sys

if sys.version_info >= (3, 9):
    import pathlib
else:
    import pathlib3x as pathlib

from typing import List, Dict, Union, Callable, Tuple
import inspect
import logging

import httpx
import yarl
from pydantic import BaseModel

from aiopenapi3.v30.general import Reference
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
    ):
        resp = session_factory().get(url)
        return cls._load_response(url, resp, session_factory, loader, plugins, use_operation_tags)

    @classmethod
    async def load_async(
        cls,
        url,
        session_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
        loader=None,
        plugins: List[Plugin] = None,
        use_operation_tags: bool = False,
    ):
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
        url,
        path: Union[str, pathlib.Path, yarl.URL],
        session_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
        loader: Loader = None,
        plugins: List[Plugin] = None,
        use_operation_tags: bool = False,
    ):
        assert loader
        if not isinstance(path, yarl.URL):
            path = yarl.URL(str(path))
        data = loader.load(Plugins(plugins or []), path)
        return cls.loads(url, data, session_factory, loader, plugins, use_operation_tags)

    @classmethod
    def loads(
        cls,
        url: str,
        data,
        session_factory: Callable[[], httpx.AsyncClient] = httpx.AsyncClient,
        loader=None,
        plugins: List[Plugin] = None,
        use_operation_tags: bool = False,
    ):
        if loader is None:
            loader = NullLoader()
        data = loader.parse(Plugins(plugins or []), yarl.URL(url), data)
        return cls(url, data, session_factory, loader, plugins, use_operation_tags)

    def _parse_obj(self, raw_document):
        v = raw_document.get("openapi", None)
        if v:
            v = list(map(int, v.split(".")))
            if v[0] == 3:
                if v[1] == 0:
                    return v30.Root.parse_obj(raw_document)
                elif v[1] == 1:
                    return v31.Root.parse_obj(raw_document)
                else:
                    raise ValueError(f"openapi version 3.{v[1]} not supported")
            else:
                raise ValueError(f"openapi major version {v[0]} not supported")
            return

        v = raw_document.get("swagger", None)
        if v:
            v = list(map(int, v.split(".")))
            if v[0] == 2 and v[1] == 0:
                return v20.Root.parse_obj(raw_document)
            else:
                raise ValueError(f"swagger version {'.'.join(v)} not supported")
        else:
            raise ValueError("missing openapi/swagger field")

    def __init__(
        self,
        url,
        document,
        session_factory: Callable[[], Union[httpx.Client, httpx.AsyncClient]] = httpx.AsyncClient,
        loader=None,
        plugins: List[Plugin] = None,
        use_operation_tags: bool = True,
    ):
        """
        Creates a new OpenAPI document from a loaded spec file.  This is
        overridden here because we need to specify the path in the parent
        class' constructor.

        :param document: The raw OpenAPI file loaded into python
        :type document: dct
        :param session_factory: default uses new session for each call, supply your own if required otherwise.
        :type session_factory: returns httpx.AsyncClient or http.Client
        :param use_operation_tags: honor tags
        :type use_operation_tags: bool

        """

        self._base_url: yarl.URL = yarl.URL(url)

        self._session_factory: Callable[[], Union[httpx.Client, httpx.AsyncClient]] = session_factory

        """
        Loader - loading referenced documents
        """
        self.loader: Loader = loader

        """
        creates the Async/Request for the protocol required
        """
        self._createRequest: Callable[["OpenAPI", str, str, "Operation"], "RequestBase"] = None

        """
        authorization informations
        e.g. {"BasicAuth": ("user","secret")}
        """
        self._security: Dict[str, Tuple[str]] = dict()

        """
        the related documents
        """
        self._documents: Dict[yarl.URL, RootBase] = dict()

        """
        the plugin interface allows taking care of defects in description documents and implementations
        """
        self._init_plugins(plugins)

        log.init()
        self.log = logging.getLogger("aiopenapi3.OpenAPI")

        document = self.plugins.document.parsed(url=self._base_url, document=document).document

        self._root = self._parse_obj(document)

        self._documents[yarl.URL(url)] = self._root

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
            todo = set(values.keys()) - processed
            if not todo:
                break
            for i in todo:
                values[i]._resolve_references(self)
            processed = set(values.keys())

    #        for i in self._documents.values():
    #            i._resolve_references(self)

    def _init_operationindex(self, use_operation_tags: bool):
        if isinstance(self._root, v20.Root):
            if self.paths:
                for path, obj in self.paths.items():
                    for m in obj.__fields_set__ & HTTP_METHODS:
                        op = getattr(obj, m)
                        op._validate_path_parameters(obj, path)
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
                    for m in obj.__fields_set__ & HTTP_METHODS:
                        op = getattr(obj, m)
                        op._validate_path_parameters(obj, path)
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
    def _iterate_schemas(schemas, d, r):
        if not d:
            return r

        r.update(d)

        import collections

        new = collections.ChainMap(
            *[
                dict(
                    filter(
                        lambda z: z[0] not in r,
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
                for i in d
            ]
        )

        sets = new.keys()
        schemas.update(new)
        r.update(sets)

        return OpenAPI._iterate_schemas(schemas, sets, r)

    def _init_schema_types(self):
        byname = dict()
        data = set()
        if isinstance(self._root, v20.Root):
            # Schema
            for byid in map(lambda x: x.definitions, self._documents.values()):
                for name, schema in filter(lambda v: isinstance(v[1], SchemaBase), byid.items()):
                    byname[schema._get_identity(name=name)] = schema
                    data.add(id(schema))
            # Request

            # Response

        elif isinstance(self._root, (v30.Root, v31.Root)):
            # Schema
            components = [x.components for x in filter(lambda y: all([y, y.components]), self._documents.values())]
            for byid in map(lambda x: x.schemas, components):
                for name, schema in filter(lambda v: isinstance(v[1], SchemaBase), byid.items()):
                    byname[schema._get_identity(name=name)] = schema
                    data.add(id(schema))

            # Request
            for path, obj in (self.paths or dict()).items():
                for m in obj.__fields_set__ & HTTP_METHODS:
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
                        data.add(id(media_type.schema_))

        byid = {id(i): i for i in byname.values()}
        data = set(byid.keys())
        todo = self._iterate_schemas(byid, data, set())

        types = dict()
        for i in todo | data:
            b = byid[i]
            types[b._get_identity("X")] = b.get_type()

        for name, schema in types.items():
            if not (inspect.isclass(schema) and issubclass(schema, BaseModel)):
                continue
            try:
                schema.update_forward_refs(**types)
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
            else:
                host, port = base.host, base.port

            path = self._root.basePath or base.path

            r = yarl.URL.build(scheme=scheme, host=host, port=port, path=path)
            return r
        elif isinstance(self._root, (v30.Root, v31.Root)):
            return self._base_url.join(yarl.URL(self._root.servers[0].url))

    # public methods
    def authenticate(self, *args, **kwargs):
        """

        :param args: None to remove all credentials / reset the authorizations
        :param kwargs: scheme=value
        """
        if len(args) == 1 and args[0] == None:
            self._security = dict()

        schemes = frozenset(kwargs.keys())
        if isinstance(self._root, v20.Root):
            v = schemes - frozenset(self._root.securityDefinitions)
        elif isinstance(self._root, (v30.Root, v31.Root)):
            v = schemes - frozenset(self._root.components.securitySchemes)

        if v:
            raise ValueError("{} does not accept security schemes {}".format(self.info.title, sorted(v)))

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
    def _(self):
        return self._operationindex

    def resolve_jr(self, root: RootBase, obj, value: Reference):
        url, jp = JSONReference.split(value.ref)
        if url != "":
            url = yarl.URL(url)
            if url not in self._documents:
                self.log.debug(f"Resolving {value.ref} - Description Document {url} unknown …")
                self._documents[url] = self._load(url)
            root = self._documents[url]

        try:
            return root.resolve_jp(jp)
        except ReferenceResolutionError as e:
            # add metadata to the error
            e.element = obj
            raise
