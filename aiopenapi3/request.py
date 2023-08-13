import abc
import collections
import io
from contextlib import closing
from typing import Dict, Tuple, Union, Any, Optional, List

import httpx
import yarl

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


from .base import HTTP_METHODS
from .version import __version__
from .errors import RequestError, OperationIdDuplicationError


class RequestParameter:
    def __init__(self, url: yarl.URL):
        self.url: str = str(url)
        self.auth: Optional[Union["BasicAuth", "DigestAuth"]] = None
        self.cookies: Dict[str, str] = {}
        #        self.path = {}
        self.params: Dict[str, str] = {}
        self.content = None
        self.headers: Dict[str, str] = {}
        self.data: Dict[str, str] = {}  # form-data
        self.files: Dict[str, Tuple[str, io.BaseIO, str]] = {}  # form-data files
        self.cert: Any = None


class RequestBase:
    """
    A Request compiles all required information to call an Operation

    Created by :meth:`aiopenapi3.OpenAPI.createRequest`.

    Run a Request via

        - :meth:`~aiopenapi3.request.RequestBase.__call__`
        - :meth:`~aiopenapi3.request.RequestBase.request`
    """

    def __init__(self, api: "OpenAPI", method: str, path: str, operation: "Operation"):
        self.api = api
        self.root = api._root
        self.method = method
        self.path = path
        self.operation = operation
        self.req: RequestParameter = RequestParameter(self.path)

    def __call__(self, *args, return_headers: bool = False, **kwargs) -> Union[Any, Tuple[Dict[str, str], Any]]:
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

    def _factory_args(self):
        return {"auth": self.req.auth, "headers": {"user-agent": f"aiopenapi3/{__version__}"}}

    def request(self, data=None, parameters=None) -> Tuple[Dict[str, Any], Any, httpx.Response]:
        """
        Sends an HTTP request as described by this Path

        :param data: The request body to send.
        :type data: any, should match content/type
        :param parameters: The path/header/query/cookie parameters required for the operation
        :type parameters: dict{str: str}
        :return: headers, data, response
        """
        self._prepare(data, parameters)
        with closing(self.api._session_factory(cert=self.req.cert, **self._factory_args())) as session:
            req = self._build_req(session)
            try:
                result = session.send(req)
            except Exception as e:
                raise RequestError(self.operation, req, data, parameters) from e
        headers, data = self._process(result)

        return headers, data, result

    @property
    @abc.abstractmethod
    def data(self) -> "SchemaBase":
        """
        :return: the Schema for the body
        """
        pass

    @property
    @abc.abstractmethod
    def parameters(self) -> List["ParameterBase"]:
        """
        :return: list of :class:`aiopenapi3.base.ParameterBase` which can be used to inspect the required/optional parameters of the requested Operation
        """
        pass


class AsyncRequestBase(RequestBase):
    async def __call__(self, *args, return_headers: bool = False, **kwargs):
        headers, data, result = await self.request(*args, **kwargs)
        if return_headers:
            return headers, data
        return data

    async def request(self, data=None, parameters=None) -> Tuple[Dict[str, Any], Any, httpx.Response]:
        self._prepare(data, parameters)
        async with aclosing(self.api._session_factory(cert=self.req.cert, **self._factory_args())) as session:
            req = self._build_req(session)
            try:
                result = await session.send(req)
            except Exception as e:
                raise RequestError(self.operation, req, data, parameters) from e

        headers, data = self._process(result)
        return headers, data, result


class OperationIndex:
    class OperationTag:
        def __init__(self, oi):
            self._oi = oi
            self._operations: Dict[str, "Operation"] = dict()

        def __getattr__(self, item):
            (method, path, op) = self._operations[item]
            return self._oi._api._createRequest(self._oi._api, method, path, op)

    class Iter:
        def __init__(self, spec: "OpenAPI", use_operation_tags: bool):
            self.operations = []
            self.r = 0
            pi: "PathItem"
            for path, pi in spec.paths.items():
                op: "Operation"
                if pi.ref:
                    pi = pi.ref._target

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
        self._root: "RootBase" = api._root

        self._operations: Dict[str, "Operation"] = dict()
        self._tags: Dict[str, "OperationTag"] = collections.defaultdict(lambda: OperationIndex.OperationTag(self))
        for path, pi in self._root.paths.items():
            op: "Operation"
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

    def __iter__(self):
        return self.Iter(self._root, self._use_operation_tags)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, values):
        self.__dict__.update(values)
