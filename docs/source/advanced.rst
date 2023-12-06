.. include:: links.rst

**************
Advanced usage
**************


Authentication
==============

The authentication requirements are part of the definition of an operation, either global or - it it exists - operation scope.
Authentication can combine/require multiple identifiers as well as providing a choice of a set.

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
        tls:
          type: mutualTLS

Authentication Conditions
-------------------------

single identifier
^^^^^^^^^^^^^^^^^

.. code:: yaml

    security:
      - basicAuth:[]


.. code:: python

    api.authenticate( basicAuth=(user,password) )

"or" - having a choice
^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    api.authenticate( None )


Authentication Methods
----------------------

apiKey
^^^^^^
In case you fail to authenticate using apiKey, it may be required to prefix the apiKey with a keyword which is not documented within the description document.

e.g.:

.. code:: python

    api.authenticate(tokenAuth=f"Token {key}")

mutualTLS
^^^^^^^^^
MutualTLS authentication requires

    * certificate file
    * key file
    * (optional) password to keyfile

to authenticate to the remote server, c.f. :ref:`httpx.Client.cert <https://www.python-httpx.org/api/#client>`_.

.. code:: python

    api.authenticate(tls=("cert.pem","key.pem"))


when using mutualTLS with self-signed certificates, it is required to add the self-signed CA to the SSLContext of the httpx session by providing a :ref:`Session Factory <advanced:Session Factory>`.


Forms
=====

Posting data to Forms using multipart/form-data or application/x-www-form-urlencoded.

OpenAPI 3.x
-----------

Refer to the unit tests how to
`describe form fields <https://github.com/commonism/aiopenapi3/blob/master/tests/fixtures/paths-requestbody-formdata-wtforms.yaml>`_
in the description document and how to post data:

  * :aioai3:ref:`tests.forms_test.test_String`
  * :aioai3:ref:`tests.forms_test.test_DateTime`
  * :aioai3:ref:`tests.forms_test.test_Numbers`
  * :aioai3:ref:`tests.forms_test.test_File`
  * :aioai3:ref:`tests.forms_test.test_Select`
  * :aioai3:ref:`tests.forms_test.test_Control`
  * :aioai3:ref:`tests.forms_test.test_Header`
  * :aioai3:ref:`tests.forms_test.test_Graph`


Swagger 2.0
-----------

The
`description document <https://github.com/commonism/aiopenapi3/blob/master/tests/fixtures/paths-parameter-format-v20.yaml>`_
and
:aioai3:ref:`the unit tests <tests.pathv20_test.test_paths_parameter_format_v20>`.


ServerVariables
===============

An example build upon the `Swagger example <https://swagger.io/docs/specification/api-host-and-base-path/>`_.

.. code:: yaml

    openapi: 3.0.4
    servers:
      - url: 'https://{host}.example.org/petstore/
          host:
            enum:
              - sandbox
              - api
            default: sandbox


Currently there is not public API except accessing OpenAPi._server_variables directly.


.. code:: python

    api._server_variables = {"host":"api"}
    api._.createPet(pet)



Manual Requests
===============

Creating a request manually allows accessing the httpx.Response as part of the :meth:`aiopenapi3.request.RequestBase.request` return value.

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

Request Streaming
-----------------
File uploads via "multipart/form-data" as mentioned in the httpx documentation
(Multipart file `uploads <https://www.python-httpx.org/quickstart/#sending-multipart-file-uploads>`_ &
`encoding <https://www.python-httpx.org/advanced/#multipart-file-encoding>`_)
do not require the content of the request to be in memory but work with file-like-objects instead.

httpx request streaming using file-like objects is limited to "multipart/form-data" and "application/octet-stream".
Additionally it does not support choice of encoding (such as base16, base64url or quoted-printable) as possible with OpenAPI v3.1 contentEncoding, which should not be a limitation.
It can not be used with "application/json".


Use via `Manual Requests`_ using the :meth:`~aiopenapi3.request.RequestBase.request` API.

multipart/form-data
^^^^^^^^^^^^^^^^^^^

Pass the form fields as a list of tuples.

.. code:: python

    data = [
        ("name",('form-data:name', file-like-object, content_type, headers))
    ]


.. code::

    Content-Type: multipart/form-data; boundary=2a8ae6ad-f4ad-4d9a-a92c-6d217011fe0f
    Content-Length: …

    --2a8ae6ad-f4ad-4d9a-a92c-6d217011fe0f
    Content-Disposition: form-data; name="datafile"; filename="r.gif"
    Content-Type: image/gif

    …

would have to be created such as

.. code:: python

    data = [
        ("datafile",('r.gif', Path('r.gif').open('rb'), "image/gif", {})
    ]

    req.request(data=data)

Mixing file-like-objects and other form data fields is possible.

.. code:: python

    data = [
        ("datafile",('r.gif', Path('r.gif').open('rb'), "image/gif", {}),
        ("path", "media/images/r.gif"),
    ]

    req.request(data=data)


See :aioai3:ref:`tests.stream_test.test_request`.


application/octet-stream
^^^^^^^^^^^^^^^^^^^^^^^^

Pass the data as file-like-object or tuple where the second entry is a file-like-object as with multipart/form-data.

.. code:: python

    data = Path("/data/file").open("rb")

    data = ("name", Path("/data/file").open("rb"))


Response Streaming
------------------

Responses exceeding the defined maximum content-length raise :class:`aiopenapi3.errors.ContentLengthExceededError` to prevent memory exhaustion.
Though it is possible to increase the defined maximum content-length, it is preferable to use streaming for large responses, limiting the amount of memory required.

:meth:`~aiopenapi3.request.RequestBase.stream` is similar to :meth:`~aiopenapi3.request.RequestBase.request` as used in `Manual Requests`_ , but does not consume the stream,
and returns the schema instead of the Model and the session which has to be closed when done.

    * :class:`aiopenapi3.request.AsyncRequestBase.stream`
    * :class:`aiopenapi3.request.RequestBase.stream`


The main difference in the async use of the streaming is await & async for.

.. rubric:: asyncio

.. code:: python

    req = api.createRequest("largeResponse")
    headers, schema, session, response = await req.stream(parameters={}, data=None)

    async for i in result.aiter_bytes():
        continue
    await session.aclose()


.. rubric:: sync

.. code:: python

    req = api.createRequest("largeResponse")
    headers, schema, session, response = req.stream(parameters={}, data=None)

    for i in result.iter_bytes():
        continue
    session.close()


Non-JSON Content
^^^^^^^^^^^^^^^^
In case the content is not a model (application/octet-stream), the data can be read iteratively and written/processed.

See :aioai3:ref:`tests.stream_test.test_stream_data`.

JSON/Arrays of Models
^^^^^^^^^^^^^^^^^^^^^
In case the large response is an array of models, iterative JSON parsing libraries can be used to process the data.

See :aioai3:ref:`tests.stream_test.test_stream_array`.


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

Or adding a SOCKS5 proxy via httpx_socks and a custom timeout value:

.. code:: python

    import httpx
    import httpx_socks

    def session_factory(*args, **kwargs) -> httpx.AsyncClient:
        kwargs["transport"] = httpx_socks.AsyncProxyTransport.from_url("socks5://127.0.0.1:8080", verify=False)
        return httpx.AsyncClient(*args, verify=False, timeout=60.0, **kwargs)


Or using a self-signed CA with certificate validation and possibly mutualTLS authentication:

.. code:: python

    def self_signed(*args, **kwargs) -> httpx.AsyncClient:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile="/etc/ssl/my-ca.pem")
        if (cert:=kwargs.get("cert", None)) is not None:
            """required for mutualTLS / client certificate authentication"""
            ctx.load_cert_chain(certfile=cert[0], keyfile=cert[1])
        return httpx.AsyncClient(*args, verify=ctx, **kwargs)


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
It is possible to redirect access to description documents to a local copy to safe some round trip times using a combination different :ref:`api:Loaders`



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
