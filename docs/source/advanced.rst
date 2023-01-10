.. include:: links.rst

**************
Advanced usage
**************


Authentication
==============
The authentication requirements are part of the definition of an operation, either global or - it it exists - operation scope.
Authentication can combine/require multiple identifiert as well as providing a choice of a set.

Given the following section of a description document:

.. code:: yaml

    components:
      securitySchemes:
        tokenAuth:
          type: apiKey
          in: header
        basicAuth:
          type: http
          scheme: basic
        bearerAuth:
          type: http
          scheme: bearer
        user:
          type: apiKey
          in: header
          name: x-user
        password:
          type: apiKey
          in: header
          name: x-password

single identifier
-----------------

.. code:: yaml

    security:
      - basicAuth:[]


.. code:: python

    api.authenticate( basicAuth=(user,password) )

"or" - having a choice
----------------------
Having a choice allows authentication using one valid identifier

.. code:: yaml

    security:
      - basicAuth:[]
      - tokenAuth:[]

.. code:: python

    api.authenticate( basicAuth=(user,password) )
    # or
    api.authenticate( tokenAuth="aeBah3tu8tho" )


"and" - combining identifiers
-----------------------------

.. code:: yaml

    security:
    -  user:[]
       password:[]

.. code:: python

    api.authenticate( user="theuser", password="thepassword" )
    # same as
    api.authenticate( user="theuser" )
    api.authenticate( password="thepassword" )

reset authentication identifiers
--------------------------------

.. code:: python

    api.authenticate( None )


Manual Requests
===============

Creating a request manually allows accessing the httpx.Response as part of the :meth:`aiopenapi3.request.Request.request` return value.

.. code:: python

    from aiopenapi3 import OpenAPI
    TOKEN=""
    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")

    req = api.createRequest("userGetCurrent")
    headers, data, response = req.request(parameters={}, data=None)


This can be used to provide certain header values (ETag), which are not parameters but required.

.. code:: python

    req = api.createRequest("user.update")
    req.req.headers["If-Match"] = etag
    r = await req(parameters=parameters, data=kwargs)


Session Factory
===============

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

Logging
=======

.. code::

    export AIOPENAPI3_LOGGING_HANDLERS=debug

will force writing to `/tmp/aiopenapi3-debug.log`.

It can be used to inspect Description Document downloads …

.. code::

    aiopenapi3.OpenAPI DEBUG Downloading Description Document TS29122_CommonData.yaml using WebLoader(baseurl=https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS24558_Eecs_ServiceProvisioning.yaml) …
    httpx._client DEBUG HTTP Request: GET https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS29122_CommonData.yaml "HTTP/1.1 200 OK"
    aiopenapi3.OpenAPI DEBUG Resolving TS29571_CommonData.yaml#/components/schemas/Gpsi - Description Document TS29571_CommonData.yaml unknown …
    aiopenapi3.OpenAPI DEBUG Downloading Description Document TS29571_CommonData.yaml using WebLoader(baseurl=https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS24558_Eecs_ServiceProvisioning.yaml) …
    httpx._client DEBUG HTTP Request: GET https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS29571_CommonData.yaml "HTTP/1.1 200 OK"
    aiopenapi3.OpenAPI DEBUG Resolving TS29122_MonitoringEvent.yaml#/components/schemas/LocationInfo - Description Document TS29122_MonitoringEvent.yaml unknown …
    aiopenapi3.OpenAPI DEBUG Downloading Description Document TS29122_MonitoringEvent.yaml using WebLoader(baseurl=https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS24558_Eecs_ServiceProvisioning.yaml) …


and general httpx requests

.. code::

    httpx._client DEBUG HTTP Request: DELETE http://localhost:51965/v2/pets/e7e979fb-bf53-4a89-9475-da9369cb4dbc "HTTP/1.1 422 "
    httpx._client DEBUG HTTP Request: GET http://localhost:54045/v2/openapi.json "HTTP/1.1 200 "
    httpx._client DEBUG HTTP Request: POST http://localhost:54045/v2/pet "HTTP/1.1 201 "


Loader
======

The :class:`aiopenapi3.loader.Loader` is used to access the description document, providing a custom loader allows adjustments to the loading process of description documents.
A common adjustment is using a customized YAML loader to disable decoding of certain tags/values.

.. code:: python

    yaml.safe_load(str(datetime.datetime.now().date()))
    # datetime.date(2022, 1, 12)

    yaml.safe_load("name: on")
    # {'name': True}

    yaml.safe_load('12_24: "test"')
    # {1224: 'test'}

In case the yaml not well formed, there are options to disable certain tags:

.. code::

    python -m aiopenapi3 -D tag:yaml.org,2002:timestamp -l -v linode.yaml
    removing tag:yaml.org,2002:timestamp
    tags:
        tag:yaml.org,2002:bool
        tag:yaml.org,2002:float
        tag:yaml.org,2002:int
        tag:yaml.org,2002:merge
        tag:yaml.org,2002:null
        tag:yaml.org,2002:value
        tag:yaml.org,2002:yaml

    OK

Those can be turned of using the yload yaml.Loader argument to the Loader.

Using the YAMLCompatibilityLoader all but these get disabled:

.. code::

    python -m aiopenapi3 -C -l -v linode.yaml
    tags:
        tag:yaml.org,2002:float
        tag:yaml.org,2002:merge
        tag:yaml.org,2002:null
        tag:yaml.org,2002:yaml


.. code:: python

    from aiopenapi3 import OpenAPI, FileSystemLoader
    import aiopenapi3.loader

    OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json",
        loader=FileSystemLoader(pathlib.Path(dir), yload = aiopenapi3.loader.YAMLCompatibilityLoader))


Serialization
=============

:class:`aiopenapi3.OpenAPI` objects can be serialized using pickle. Storing serialized clients allows re-use and improves
start up time for large service description documents.
The dynamic generated pydantic_ models can not be serialized though and have to be created after loading the object.
:meth:`aiopenapi3.OpenAPI.cache_store` writes a pickled api object to a path, :meth:`aiopenapi3.OpenAPI.cache_load` reads
an pickled OpenAPI object from Path and initializes the dynamic models.

.. code:: python

    from pathlib import Path
    import pickle

    from aiopenapi3 import OpenAPI

    def from_cache(target, cache):
        api = None
        try:
            api = OpenAPI.cache_load(Path(cache))
        except FileNotFoundError:
            api = OpenAPI.load_sync(target)
            api.cache_store(Path(cache))
        return api

    api = from_cache("https://try.gitea.io/swagger.v1.json", "/tmp/gitea-client.pickle")

Cloning
=======

:class:`aiopenapi3.OpenAPI` objects can be cloned using :meth:`aiopenapi3.OpenAPI.clone` - create multiple clients from
the same description document.

.. code:: python

    import copy
    import yarl

    from aiopenapi3 import OpenAPI

    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api2 = api.clone(baseurl=yarl.URL("https://gitea.localhost.localnet/"))


Using clones, running multiple asyncio clients simultanously is easy.
Limiting the concurrency to a certain number of clients:

.. code:: python

        # clients is a list of api instances with different base urls
        clients = [Client(api.clone(url)) for url in urls]

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
