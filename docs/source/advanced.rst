.. include:: links.rst

Advanced usage
--------------

Manual Requests
^^^^^^^^^^^^^^^

Creating a request manually allows accessing the httpx.Response as part of the :meth:`aiopenapi3.request.Request.request` return value.

.. code:: python

    from aiopenapi3 import OpenAPI
    TOKEN=""
    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")

    req = api.createRequest("userGetCurrent")
    headers, data, response = req.request(parameters={}, data=None)



Session Factory
^^^^^^^^^^^^^^^

The session_factory argument of the |aiopenapi3| initializers allow setting httpx_ options to the transport.

E.g. setting `httpx Event Hooks <https://www.python-httpx.org/advanced/#event-hooks>`_:

.. code:: python

    def log_request(request):
        print(f"Request event hook: {request.method} {request.url} - Waiting for response")

    def log_response(response):
        request = response.request
        print(f"Response event hook: {request.method} {request.url} - Status {response.status_code}")

    def session_factory(*args, **kwargs) -> httpx.AsyncClient:
        kwargs["event_hooks"] = {"request": [log_request], "response": [log_response]}
        return httpx.AsyncClient(*args, verify=False, timeout=60.0, **kwargs)

Or adding a SOCKS5 proxy via httpx_socks:

.. code:: python

    import httpx
    import httpx_socks

    def session_factory(*args, **kwargs) -> httpx.AsyncClient:
        kwargs["transport"] = httpx_socks.AsyncProxyTransport.from_url("socks5://127.0.0.1:8080", verify=False)
        return httpx.AsyncClient(*args, verify=False, timeout=60.0, **kwargs)

.. _Advandeced Loader:

Loader
^^^^^^

The :class:`aiopenapi3.loader.Loader` is used to access the description document, providing a custom loader allows adjustments to the loading process of description documents.
A common adjustment is using a customized YAML loader to disable decoding of certain tags/values.

.. code:: python

    from aiopenapi3 import OpenAPI, FileSystemLoader
    import aiopenapi3.loader

    OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json", loader=FileSystemLoader(pathlib.Path(dir), yload = aiopenapi3.loader.YAMLCompatibilityLoader))


Serialization
^^^^^^^^^^^^^

:class:`aiopenapi3.OpenAPI` objects can be serialized using pickle. Storing serialized clients allows re-use and improves
start up time for large service description documents.
The dynamic generated pydantic_ models can not be serialized though and have to be created after loading the object.

.. code:: python

    from pathlib import Path
    import pickle

    from aiopenapi3 import OpenAPI

    def from_cache(target, cache=None):
        api = None
        try:
            if cache:
                with Path(cache).open("rb") as f:
                    api = pickle.load(f)
                    api._init_schema_types()
        except FileNotFoundError:
            api = OpenAPI.load_sync(target)
            if cache:
                with Path(cache).open("wb") as f:
                    pickle.dump(api, f)
        return api

    api = from_cache("https://try.gitea.io/swagger.v1.json", "/tmp/gitea-client.pickle")

Cloning
^^^^^^^
:class:`aiopenapi3.OpenAPI` objects can be cloned - create multiple clients from the same description document.

.. code:: python

    import copy
    import yarl

    from aiopenapi3 import OpenAPI

    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api2 = copy.copy(api)
    api2._base_url = yarl.URL("https://gitea..localhost.localnet/")


Using clones, running multiple asyncio clients simultanously is easy.
Limiting the concurrency to a certain number of clients:

.. code:: python

        # clients is a list of api instances with different base urls
        clients = [Client(copy.copy(api)).with_base_url(url) for url in urls]

        qlen = 32
        pending = set()
        offset = 0
        while True:
            lower = offset
            upper = min(offset + qlen - len(pending), len(clients))
            for o in range(lower, upper):
                t = asyncio.create_task(clients[o].run("/redfish/v1/Systems"))
                pending.add(t)
            offset = upper

            if offset == len(clients):
                done, pending = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
                break
            else:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
