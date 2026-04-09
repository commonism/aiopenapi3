import abc
import collections
import contextlib
import typing
import json
import logging
from contextlib import closing
from typing import Any, NamedTuple, Optional, Union, cast, override
from collections.abc import AsyncIterator, AsyncGenerator, Generator
from collections.abc import Iterator
from contextlib import aclosing

import httpx
import pydantic
import yarl

from aiopenapi3.errors import ContentLengthExceededError


from .base import HTTP_METHODS, ReferenceBase
from .version import __version__
from .errors import RequestError, OperationIdDuplicationError

if typing.TYPE_CHECKING:
    from ._types import (
        RequestParameters,
        RequestData,
        RequestFiles,
        RequestContent,
        RequestType,
        AuthTypes,
        SchemaType,
        ParameterType,
        PathItemType,
        OperationType,
        JSON,
        RootType,
        ServerType,
        ResponseDataType,
        ResponseHeadersType,
        HTTPMethodType,
    )
    from aiopenapi3 import OpenAPI

log = logging.getLogger("aiopenapi3.request")


class RequestParameter:
    def __init__(self, url: yarl.URL | str):
        self.url: str = str(url)
        self.auth: Optional["AuthTypes"] = None
        self.cookies: dict[str, str] = {}
        #        self.path = {}
        self.params: dict[str, str] = {}
        self.content: Optional["RequestContent"] = None
        self.headers: dict[str, str] = {}
        self.data: dict[str, str] = {}  # form-data
        self.files: Optional["RequestFiles"] = {}  # form-data files
        self.cert: Any = None


class RequestBase:
    class StreamResponse(NamedTuple):
        headers: "ResponseHeadersType"
        schema: Optional["SchemaType"]
        session: httpx.Client
        result: httpx.Response

    class Sequencer:
        def __init__(self, headers: "ResponseHeadersType", stream: Iterator["JSON"], model: pydantic.BaseModel) -> None:
            self.headers: ResponseHeadersType = headers
            self.stream: Iterator["JSON"] = stream
            self.model = model

        def __iter__(self) -> Iterator:
            return self

        def __next__(self) -> pydantic.BaseModel:
            data: JSON
            for data in self.stream:
                obj = self.model.model_validate(data)
                return obj
            raise StopIteration

    class Response(NamedTuple):
        headers: "ResponseHeadersType"
        data: Any
        result: httpx.Response

    class Vars(NamedTuple):
        parameters: dict[str, str] | None
        data: Any | None
        context: Any | None
        """
        call provided context data for use in :func:`aiopenapi3.plugin.Message`
        """

    """
    A Request compiles all required information to call an Operation

    Created by :meth:`aiopenapi3.OpenAPI.createRequest`.

    Run a Request via

        - :meth:`~aiopenapi3.request.RequestBase.__call__`
        - :meth:`~aiopenapi3.request.RequestBase.request`
    """

    def __init__(
        self,
        api: "OpenAPI",
        method: "HTTPMethodType",
        path: str,
        operation: "OperationType",
        servers: list["ServerType"] | None,
    ):
        self.api: "OpenAPI" = api
        """
        OpenAPI object
        """

        self.root = api._root  # pylint: disable=W0212
        """
        API document root
        """

        self.method: "HTTPMethodType" = method
        """
        HTTP method
        """

        self.path: str = path
        """
        HTTP path
        """

        self.vars: Optional["RequestBase.Vars"] = None
        """
        Parameter & Data
        """

        self.operation: "OperationType" = operation
        """
        associated OpenAPI Operation
        """

        self.req: RequestParameter = RequestParameter(self.path)
        """
        RequestParameter
        """

        self.servers: list["ServerType"] | None = servers
        """
        Servers to use for this request
        """

    def __call__(
        self, *args, return_headers: bool = False, context=None, **kwargs
    ) -> Union["JSON", tuple["ResponseHeadersType", "JSON"]]:
        """
        :param args:
        :param return_headers:  if set return a tuple (header, body)
        :param kwargs:
        :return: body or (header, body)
        """
        headers, data, result = self.request(*args, context=context, **kwargs)  # type: ignore[misc]
        if return_headers:
            return headers, data
        return data

    @property
    def _session_factory_default_args(self) -> dict[str, Any]:
        """
        this is the session factory default arguments,
        the arguments passed to httpx.Async/Client()

        if you need to pass your own parameters to httpx.Async/Client use a session factory
        and pass your pararmters to the constructor in addition to these default arguments
        """
        return {"cert": self.req.cert, "auth": self.req.auth, "headers": {"user-agent": f"aiopenapi3/{__version__}"}}

    def _send(
        self, session: httpx.Client, data: Optional["RequestData"], parameters: Optional["RequestParameters"]
    ) -> httpx.Response:
        req = self._build_req(session)
        try:
            result = session.send(req, stream=True)
        except Exception as e:
            raise RequestError(self.operation, self, data, parameters) from e
        return result

    @abc.abstractmethod
    def _process_stream(self, result: httpx.Response) -> tuple["ResponseHeadersType", Optional["SchemaType"]]:
        """
        process response headers
        lookup the schema for the stream
        """
        ...

    @abc.abstractmethod
    def _process_request(self, result: httpx.Response) -> tuple["ResponseHeadersType", "ResponseDataType"]:
        """
        process response headers
        lookup Model
        """
        ...

    @abc.abstractmethod
    def _process_sequence(self, result: httpx.Response) -> tuple["ResponseHeadersType", "ResponseDataType", Any]:
        """
        process response headers
        lookup Model
        """
        ...

    @abc.abstractmethod
    def _prepare(self, data: Optional["RequestData"], parameters: Optional["RequestParameters"]) -> None: ...

    def _build_req(self, session: httpx.Client | httpx.AsyncClient) -> httpx.Request:
        url: yarl.URL = self.api.url

        if self.servers:
            server: "ServerType" = self.api._server_select(self.servers)
            url = self.api._base_url.join(yarl.URL(server.createUrl(self.api._server_variables)))

        req = session.build_request(
            self.method,
            str(url / self.req.url[1:]),
            headers=self.req.headers,
            cookies=self.req.cookies,
            params=self.req.params,
            content=self.req.content,
            data=self.req.data,
            files=self.req.files,
        )
        return req

    def _raise_on_http_status(self, status_code: int, headers: dict[str, str], data: pydantic.BaseModel | bytes):
        for exc, (start, end) in self.api.raise_on_http_status:
            if start <= status_code <= end:
                raise exc(status_code, headers, data)

    def request(
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
        context: Any = None,
    ) -> "RequestBase.Response":
        """
        Sends an HTTP request as described by this Path

        :param data: The request body to send.
        :type data: any, should match content/type
        :param parameters: The path/header/query/cookie parameters required for the operation
        :type parameters: dict{str: str}
        :param context: The request context for use in aiopenapi3.plugin.Message
        :type context: Any
        :return: headers, data, response
        """
        self.vars = RequestBase.Vars(parameters, data, context)
        self._prepare(data, parameters)
        with closing(self.api._session_factory(**self._session_factory_default_args)) as session:
            result = self._send(session, data, parameters)

            if (cl := int(result.headers.get("Content-Length", 0))) > (m := self.api._max_response_content_length):
                raise ContentLengthExceededError(
                    self.operation, cl, f"Content-Length ({cl}) exceeds maximum ({m})", result
                )

            result.read()

        headers, data = self._process_request(result)
        return RequestBase.Response(headers, data, result)

    def stream(
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
        context: Any = None,
    ) -> "RequestBase.StreamResponse":
        """
        Sends an HTTP request as described by this Path - but do not process the result
          * returns a tuple of Schema, httpx.Client, httpx.Response
          * requires closing the Client when done processing the response
          * requires manual processing of the data
          * intended for use with of large results
          * httpx response streaming via Response.iter_bytes()
          * combine with ijson coroutines

        :param data: The request body to send.
        :type data: any, should match content/type
        :param parameters: The path/header/query/cookie parameters required for the operation
        :type parameters: dict{str: str}
        :return: schema, session, response
        """

        self.vars = RequestBase.Vars(parameters, data, context)
        self._prepare(data, parameters)
        session = self.api._session_factory(**self._session_factory_default_args)
        result = self._send(session, data, parameters)
        headers, schema_ = self._process_stream(result)
        return RequestBase.StreamResponse(headers, schema_, session, result)

    @contextlib.contextmanager
    def sequence(  # type: ignore[override]
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
        context: Any = None,
    ) -> Generator["RequestBase.Sequencer", None, None]:
        self.vars = RequestBase.Vars(parameters, data, context)
        self._prepare(data, parameters)
        session: httpx.Client = self.api._session_factory(**self._session_factory_default_args)
        result = self._send(session, data, parameters)
        headers, schema_, content_type = self._process_sequence(result)

        if content_type in ["application/jsonl", "application/x-ndjson"]:
            """
            https://jsonlines.org/
            https://github.com/ndjson/ndjson-spec
            """

            def iter_json(response: httpx.Response) -> Iterator["JSON"]:
                for i in response.iter_lines():
                    yield json.loads(i)

        elif content_type == "application/json-seq":
            """
            JSON Text Sequence
            https://datatracker.ietf.org/doc/html/rfc7464
            """

            import jsonseq.decode

            def iter_json(response: httpx.Response) -> Iterator["JSON"]:
                decoder = jsonseq.decode.JSONSeqDecoder()
                for text in response.iter_text():
                    yield from decoder.decode(text)

        elif content_type == "text/event-stream":
            """
            Server-Sent Events (SSE)
            https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
            """

            import ijson

            class ReadEventStream:
                """
                Using a AsyncIterator input to feed a coroutine
                """

                def __init__(self, response: httpx.Response) -> None:
                    self._iter_bytes = response.iter_bytes()

                def read(self, num_bytes: int) -> bytes:
                    if num_bytes == 0:
                        return b""

                    return next(self._iter_bytes)

            def iter_json(response: httpx.Response) -> Iterator["JSON"]:
                reader = ReadEventStream(response)
                yield from ijson.items(reader, "item")
        else:
            raise NotImplementedError(content_type)

        try:
            """__enter__"""
            stream = iter_json(result)
            yield RequestBase.Sequencer(headers, stream, schema_.get_type())
        finally:
            """__exit__"""
            if not result.is_closed:
                result.close()

    @property
    @abc.abstractmethod
    def data(self) -> Optional["SchemaType"]:
        """
        :return: the Schema for the body
        """
        ...

    @property
    @abc.abstractmethod
    def parameters(self) -> list["ParameterType"]:
        """
        :return: list of :class:`aiopenapi3.base.ParameterBase` which can be used to inspect the required/optional parameters of the requested Operation
        """
        ...


class AsyncRequestBase(RequestBase):
    class StreamResponse(NamedTuple):
        headers: "ResponseHeadersType"
        schema: Optional["SchemaType"]
        session: httpx.AsyncClient
        result: httpx.Response

    @override
    class Sequencer:
        def __init__(
            self, headers: "ResponseHeadersType", stream: AsyncIterator["JSON"], model: pydantic.BaseModel
        ) -> None:
            self.headers: "ResponseHeadersType" = headers
            self.stream: AsyncIterator["JSON"] = stream
            self.model = model

        def __aiter__(self) -> AsyncIterator:
            return self

        async def __anext__(self) -> pydantic.BaseModel:
            data: JSON
            async for data in self.stream:
                obj = self.model.model_validate(data)
                return obj
            raise StopAsyncIteration

    async def __call__(  # type: ignore[override]
        self, *args, return_headers: bool = False, context: Any = None, **kwargs
    ) -> Union["JSON", tuple[dict[str, str], "JSON"]]:
        headers, data, result = await self.request(*args, context=context, **kwargs)  # type: ignore [misc]
        if return_headers:
            return headers, data
        return data

    async def _send(
        self, session: httpx.AsyncClient, data: Optional["RequestData"], parameters: Optional["RequestParameters"]
    ) -> httpx.Response:  # type: ignore[override]
        req = self._build_req(session)
        try:
            result = await session.send(req, stream=True)
        except Exception as e:
            raise RequestError(self.operation, self, data, parameters or dict()) from e
        return result

    async def request(  # type: ignore[override]
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
        context: Any = None,
    ) -> "RequestBase.Response":
        self.vars = RequestBase.Vars(parameters, data, context)
        self._prepare(data, parameters)
        async with aclosing(self.api._session_factory(**self._session_factory_default_args)) as session:
            result = await self._send(session, data, parameters)

            if (cl := int(result.headers.get("Content-Length", 0))) > (m := self.api._max_response_content_length):
                raise ContentLengthExceededError(
                    self.operation, cl, f"Content-Length ({cl}) exceeds maximum ({m})", result
                )

            await result.aread()

        headers, data = self._process_request(result)
        return RequestBase.Response(headers, data, result)

    async def stream(  # type: ignore[override]
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
        context: Any = None,
    ) -> "AsyncRequestBase.StreamResponse":
        self.vars = RequestBase.Vars(parameters, data, context)
        self._prepare(data, parameters)
        session = self.api._session_factory(**self._session_factory_default_args)
        result = await self._send(session, data, parameters)
        headers, schema_ = self._process_stream(result)
        return AsyncRequestBase.StreamResponse(headers, schema_, session, result)

    @contextlib.asynccontextmanager
    async def sequence(  # type: ignore[override]
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
        context: Any = None,
    ) -> AsyncGenerator["AsyncRequestBase.Sequencer", None]:
        self.vars = RequestBase.Vars(parameters, data, context)
        self._prepare(data, parameters)
        session = self.api._session_factory(**self._session_factory_default_args)
        result = await self._send(session, data, parameters)
        headers, schema_, content_type = self._process_sequence(result)

        if content_type in ["application/jsonl", "application/x-ndjson"]:
            """
            https://jsonlines.org/
            https://github.com/ndjson/ndjson-spec
            """

            async def aiter_json(response: httpx.Response) -> AsyncIterator["JSON"]:
                async for i in response.aiter_lines():
                    yield json.loads(i)

        elif content_type == "application/json-seq":
            """
            JSON Text Sequence
            https://datatracker.ietf.org/doc/html/rfc7464
            """

            import jsonseq.decode

            async def aiter_json(response: httpx.Response) -> AsyncIterator["JSON"]:
                decoder = jsonseq.decode.JSONSeqDecoder()
                async for text in response.aiter_text():
                    for obj in decoder.decode(text):
                        yield obj

        elif content_type == "text/event-stream":
            """
            Server-Sent Events (SSE)
            https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
            """

            import ijson

            class ReadEventStream:
                """
                Using a AsyncIterator input to feed a coroutine
                """

                def __init__(self, response: httpx.Response) -> None:
                    self._aiter_bytes = response.aiter_bytes()

                async def read(self, num_bytes: int) -> bytes:
                    if num_bytes == 0:
                        return b""

                    return await anext(self._aiter_bytes)

            async def aiter_json(response: httpx.Response) -> AsyncIterator["JSON"]:
                reader = ReadEventStream(response)
                async for item in ijson.items(reader, "item"):
                    yield item
        else:
            raise NotImplementedError(content_type)

        try:
            """__aenter__"""
            stream = aiter_json(result)
            yield AsyncRequestBase.Sequencer(headers, stream, schema_.get_type())
        finally:
            """__aexit__"""
            if not result.is_closed:
                await result.aclose()


class OperationIndex:
    class OperationTag:
        def __init__(self, oi: "OperationIndex") -> None:
            self._oi = oi
            self._operations: dict[str, tuple["HTTPMethodType", str, "OperationType", list["ServerType"] | None]] = (
                dict()
            )

        def __getattr__(self, item) -> RequestBase:
            (method, path, op, servers) = self._operations[item]
            return self._oi._api._createRequest(self._oi._api, method, path, op, servers)

    class Iter:
        def __init__(self, spec: "OpenAPI", use_operation_tags: bool):
            self.operations = []
            self.r: Iterator[int]
            pi: "PathItemType"
            for path, pi in spec.paths.items():
                op: "OperationType"
                if pi.ref:
                    #                    pi = pi.ref._target
                    pi = cast("PathItemType", cast(ReferenceBase, pi.ref)._target)

                for method in pi.model_fields_set & HTTP_METHODS:
                    op = getattr(pi, method)
                    if op.operationId is None:
                        continue
                    if use_operation_tags and op.tags:
                        for tag in op.tags:
                            self.operations.append(f"{tag}.{op.operationId}")
                    else:
                        self.operations.append(op.operationId)

                if hasattr(pi, "additionalOperations"):  # v32
                    if pi.additionalOperations:
                        for method, op in pi.additionalOperations.items():
                            if use_operation_tags and op.tags:
                                for tag in op.tags:
                                    self.operations.append(f"{tag}.{op.operationId}")
                            else:
                                self.operations.append(op.operationId)

            self.r = iter(range(len(self.operations)))

        def __iter__(self):
            return self

        def __next__(self):
            return self.operations[next(self.r)]

    def __init__(self, api: "OpenAPI", use_operation_tags: bool):
        self._api: "OpenAPI" = api
        self._root: "RootType" = api._root

        self._operations: dict[str, tuple["HTTPMethodType", str, "OperationType", list["ServerType"] | None]] = dict()
        self._tags: dict[str, "OperationIndex.OperationTag"] = collections.defaultdict(
            lambda: OperationIndex.OperationTag(self)
        )
        pi: "PathItemType"
        for path, pi in self._root.paths.items():
            op: "OperationType"
            servers: list["ServerType"] | None
            if pi.ref:
                pi = pi.ref._target
            for method in pi.model_fields_set & HTTP_METHODS:
                op = getattr(pi, method)
                if op.operationId is None:
                    continue
                operationId = op.operationId.replace(" ", "_")
                # v20 does not have server
                if hasattr(op, "servers"):
                    servers = op.servers or pi.servers or None
                else:
                    servers = None
                item = (method, path, op, servers)
                if use_operation_tags and op.tags:
                    for tag in op.tags:
                        if (other := self._tags[tag]._operations.get(operationId, None)) is not None:
                            raise OperationIdDuplicationError(operationId, [item, other])
                        self._tags[tag]._operations[operationId] = item
                else:
                    if (other := self._operations.get(operationId, None)) is not None:
                        raise OperationIdDuplicationError(operationId, [item, other])
                    self._operations[operationId] = item

            if hasattr(pi, "additionalOperations"):  # v32
                if pi.additionalOperations:
                    for method, op in pi.additionalOperations.items():
                        if op.operationId is None:
                            continue
                        operationId = op.operationId.replace(" ", "_")
                        servers = op.servers or pi.servers or None
                        item = (method, path, op, servers)
                        if use_operation_tags and op.tags:
                            for tag in op.tags:
                                if (other := self._tags[tag]._operations.get(operationId, None)) is not None:
                                    raise OperationIdDuplicationError(operationId, [item, other])
                                self._tags[tag]._operations[operationId] = item
                        else:
                            if (other := self._operations.get(operationId, None)) is not None:
                                raise OperationIdDuplicationError(operationId, [item, other])
                            self._operations[operationId] = item

        # convert to dict as pickle does not like local functions
        self._tags = dict(self._tags)
        self._use_operation_tags = use_operation_tags

    def __getattr__(self, item: str) -> "RequestType":
        """
        the sad smiley interface

        :param item: the operationId
        :return:
        """
        if self._use_operation_tags and item in self._tags:
            return self._tags[item]
        elif item in self._operations:
            (method, path, op, servers) = self._operations[item]
            return self._api._createRequest(self._api, method, path, op, servers)
        else:
            raise KeyError(f"operationId {item} not found in tags or operations")

    def __getitem__(self, item: str | tuple[str, "HTTPMethodType"]) -> "RequestType":
        """
        index operator interface
        access operations by operationId or (path, method)

        :param item: operationId or tuple of path & method
        :return:
        """
        return getattr(self, item) if isinstance(item, str) else self._api.createRequest(item)

    def __iter__(self) -> Iter:
        return self.Iter(self._root, self._use_operation_tags)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, values):
        self.__dict__.update(values)
