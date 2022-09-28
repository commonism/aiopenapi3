import collections
import io
from contextlib import closing
from typing import Dict, Tuple, Union, Any, Optional

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
from .errors import SpecError


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
    def __init__(self, api: "OpenAPI", method: str, path: str, operation: "Operation"):
        self.api = api
        self.root = api._root
        self.method = method
        self.path = path
        self.operation = operation
        self.req: RequestParameter = RequestParameter(self.path)

    def __call__(self, *args, **kwargs):
        return self.request(*args, **kwargs)

    def _factory_args(self):
        return {"auth": self.req.auth, "headers": {"user-agent": f"aiopenapi3/{__version__}"}}

    def request(
        self, data=None, parameters=None, return_headers: bool = False
    ) -> Union[Any, Tuple[Dict[str, Any], Any]]:
        """
        Sends an HTTP request as described by this Path

        :param data: The request body to send.
        :type data: any, should match content/type
        :param parameters: The parameters used to create the path
        :type parameters: dict{str: str}
        :param return_headers: if set return a tuple (header, body)
        :return: body or (header, body)
        """
        self._prepare(data, parameters)
        with closing(self.api._session_factory(**self._factory_args())) as session:
            req = self._build_req(session)
            result = session.send(req)
        headers, data = self._process(result)
        if return_headers is True:
            return headers, data
        else:
            return data


class AsyncRequestBase(RequestBase):
    async def __call__(self, *args, **kwargs):
        return await self.request(*args, **kwargs)

    async def request(
        self, data=None, parameters=None, return_headers: bool = False
    ) -> Union[Any, Tuple[Dict[str, Any], Any]]:
        self._prepare(data, parameters)
        async with aclosing(self.api._session_factory(**self._factory_args())) as session:
            req = self._build_req(session)
            result = await session.send(req)

        headers, data = self._process(result)
        if return_headers is True:
            return headers, data
        else:
            return data


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
                for method in pi.__fields_set__ & HTTP_METHODS:
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
            for method in pi.__fields_set__ & HTTP_METHODS:
                op = getattr(pi, method)
                if op.operationId is None:
                    continue
                operationId = op.operationId.replace(" ", "_")
                if use_operation_tags and op.tags:
                    for tag in op.tags:
                        if operationId in self._tags[tag]._operations:
                            raise SpecError(f"Duplicate operationId {operationId}")
                        self._tags[tag]._operations[operationId] = (method, path, op)
                else:
                    if operationId in self._operations:
                        raise SpecError(f"Duplicate operationId {operationId}")
                    self._operations[operationId] = (method, path, op)
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
            raise SpecError(f"element {item} not found in tags or operations")

    def __iter__(self):
        return self.Iter(self._root, self._use_operation_tags)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, values):
        self.__dict__.update(values)
