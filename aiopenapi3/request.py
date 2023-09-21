import abc
import collections
import typing
from contextlib import closing
from typing import Dict, Tuple, Any, List, NamedTuple, Optional, Iterator, Union, cast

import httpx
import pydantic
import yarl

from aiopenapi3.errors import ContentLengthExceededError


try:
    from contextlib import aclosing
except:  # <= Python 3.10
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def aclosing(thing):
        try:
            yield thing
        finally:
            await thing.aclose()


from .base import HTTP_METHODS, ReferenceBase
from .version import __version__
from .errors import RequestError, OperationIdDuplicationError


if typing.TYPE_CHECKING:
    from ._types import (
        RequestParameters,
        RequestData,
        RequestFiles,
        RequestContent,
        AuthTypes,
        SchemaType,
        ParameterType,
        PathItemType,
        OperationType,
        JSON,
        RootType,
        ResponseDataType,
        ResponseHeadersType,
    )
    from aiopenapi3 import OpenAPI


class RequestParameter:
    def __init__(self, url: Union[yarl.URL, str]):
        self.url: str = str(url)
        self.auth: Optional["AuthTypes"] = None
        self.cookies: Dict[str, str] = {}
        #        self.path = {}
        self.params: Dict[str, str] = {}
        self.content: Optional["RequestContent"] = None
        self.headers: Dict[str, str] = {}
        self.data: Dict[str, str] = {}  # form-data
        self.files: Optional["RequestFiles"] = {}  # form-data files
        self.cert: Any = None


class RequestBase:
    class StreamResponse(NamedTuple):
        headers: Dict[str, str]
        schema: "SchemaType"
        session: httpx.Client
        result: httpx.Response

    class Response(NamedTuple):
        headers: Dict[str, str]
        data: Any
        result: httpx.Response

    """
    A Request compiles all required information to call an Operation

    Created by :meth:`aiopenapi3.OpenAPI.createRequest`.

    Run a Request via

        - :meth:`~aiopenapi3.request.RequestBase.__call__`
        - :meth:`~aiopenapi3.request.RequestBase.request`
    """

    def __init__(self, api: "OpenAPI", method: str, path: str, operation: "OperationType"):
        self.api: "OpenAPI" = api
        self.root = api._root  # pylint: disable=W0212
        self.method: str = method
        self.path: str = path
        self.operation: "OperationType" = operation
        self.req: RequestParameter = RequestParameter(self.path)

    def __call__(self, *args, return_headers: bool = False, **kwargs) -> Union["JSON", Tuple[Dict[str, str], "JSON"]]:
        """
        :param args:
        :param return_headers:  if set return a tuple (header, body)
        :param kwargs:
        :return: body or (header, body)
        """
        headers, data, result = self.request(*args, **kwargs)
        if return_headers:
            return headers, data
        return data

    @property
    def _session_factory_default_args(self) -> Dict[str, Any]:
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
            raise RequestError(self.operation, req, data, parameters) from e
        return result

    @abc.abstractmethod
    def _process_stream(self, result: httpx.Response) -> Tuple["ResponseHeadersType", Optional["SchemaType"]]:
        """
        process response headers
        lookup the schema for the stream
        """
        ...

    @abc.abstractmethod
    def _process_request(self, result: httpx.Response) -> Tuple["ResponseHeadersType", "ResponseDataType"]:
        """
        process response headers
        lookup Model
        """
        ...

    @abc.abstractmethod
    def _prepare(self, data: Optional["RequestData"], parameters: Optional["RequestParameters"]) -> None:
        ...

    def _build_req(self, session: Union[httpx.Client, httpx.AsyncClient]) -> httpx.Request:
        req = session.build_request(
            self.method,
            str(self.api.url / self.req.url[1:]),
            headers=self.req.headers,
            cookies=self.req.cookies,
            params=self.req.params,
            content=self.req.content,
            data=self.req.data,
            files=self.req.files,
        )
        return req

    def request(
        self,
        data: Optional["RequestData"] = None,
        parameters: Optional["RequestParameters"] = None,
    ) -> "RequestBase.Response":
        """
        Sends an HTTP request as described by this Path

        :param data: The request body to send.
        :type data: any, should match content/type
        :param parameters: The path/header/query/cookie parameters required for the operation
        :type parameters: dict{str: str}
        :return: headers, data, response
        """
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

        self._prepare(data, parameters)
        session = self.api._session_factory(**self._session_factory_default_args)
        result = self._send(session, data, parameters)
        headers, schema_ = self._process_stream(result)
        return RequestBase.StreamResponse(headers, schema_, session, result)

    @property
    @abc.abstractmethod
    def data(self) -> Optional["SchemaType"]:
        """
        :return: the Schema for the body
        """
        ...

    @property
    @abc.abstractmethod
    def parameters(self) -> List["ParameterType"]:
        """
        :return: list of :class:`aiopenapi3.base.ParameterBase` which can be used to inspect the required/optional parameters of the requested Operation
        """
        ...


class AsyncRequestBase(RequestBase):
    class StreamResponse(NamedTuple):
        headers: Dict[str, str]
        schema: "SchemaType"
        session: httpx.AsyncClient
        result: httpx.Response

    async def __call__(  # type: ignore[override]
        self, *args, return_headers: bool = False, **kwargs
    ) -> Union["JSON", Tuple[Dict[str, str], "JSON"]]:
        headers, data, result = await self.request(*args, **kwargs)
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
            raise RequestError(self.operation, req, data, parameters or dict()) from e
        return result

    async def request(  # type: ignore[override]
        self, data: Optional["RequestData"] = None, parameters: Optional["RequestParameters"] = None
    ) -> "RequestBase.Response":
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
        self, data: Optional["RequestData"] = None, parameters: Optional["RequestParameters"] = None
    ) -> "AsyncRequestBase.StreamResponse":
        self._prepare(data, parameters)
        session = self.api._session_factory(**self._session_factory_default_args)
        result = await self._send(session, data, parameters)
        headers, schema_ = self._process_stream(result)
        return AsyncRequestBase.StreamResponse(headers, schema_, session, result)


class OperationIndex:
    class OperationTag:
        def __init__(self, oi: "OperationIndex") -> None:
            self._oi = oi
            self._operations: Dict[str, Tuple[str, str, "OperationType"]] = dict()

        def __getattr__(self, item) -> RequestBase:
            (method, path, op) = self._operations[item]
            return self._oi._api._createRequest(self._oi._api, method, path, op)

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
            self.r = iter(range(len(self.operations)))

        def __iter__(self):
            return self

        def __next__(self):
            return self.operations[next(self.r)]

    def __init__(self, api: "OpenAPI", use_operation_tags: bool):
        self._api: "OpenAPI" = api
        self._root: "RootType" = api._root

        self._operations: Dict[str, Tuple[str, str, "OperationType"]] = dict()
        self._tags: Dict[str, "OperationIndex.OperationTag"] = collections.defaultdict(
            lambda: OperationIndex.OperationTag(self)
        )
        for path, pi in self._root.paths.items():
            op: "OperationType"
            if pi.ref:
                pi = pi.ref._target
            for method in pi.model_fields_set & HTTP_METHODS:
                op = getattr(pi, method)
                if op.operationId is None:
                    continue
                operationId = op.operationId.replace(" ", "_")
                item = (method, path, op)
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

    def __getattr__(self, item):
        if self._use_operation_tags and item in self._tags:
            return self._tags[item]
        elif item in self._operations:
            (method, path, op) = self._operations[item]
            return self._api._createRequest(self._api, method, path, op)
        else:
            raise KeyError(f"operationId {item} not found in tags or operations")

    def __getitem__(self, item: Union[str, Tuple[str, str]]):
        """
        index operator interface
        access operations by operationId or (path, method)
        """
        return getattr(self, item) if isinstance(item, str) else self._api.createRequest(item)

    def __iter__(self):
        return self.Iter(self._root, self._use_operation_tags)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, values):
        self.__dict__.update(values)
