.. include:: links.rst

****************
Using aiopenapi3
****************

As a client
===========

Creating a client from a description document
---------------------------------------------

|aiopenapi3| can ingest description documents from different sources.

- :meth:`aiopenapi3.OpenAPI.loads` - from string
- :meth:`aiopenapi3.OpenAPI.load_file` - from a local file
- :meth:`aiopenapi3.OpenAPI.load_sync` - from the web/syncronous
- :meth:`aiopenapi3.OpenAPI.load_async` - from the web/asynchronous

The `url` parameter describes the path of the description document.
The url of a request is created by combining the

#. description documents url
#. the location from the description url

  * OpenAPI 3.x: servers[*].url

  * Swagger 2.0: basePath

#. path from the PathItem

e.g.:

#. `http://localhost/api/openapi.yaml`
#. `servers[0].url = '/api/v1'`
#. `'/users/login'`

will result in

`http://localhost` `/api/v1` `/users/login`

Refer to :ref:`advanced:ServerVariables` for advanced use of the url definition.

For :meth:`aiopenapi3.OpenAPI.load_file` the url parameter does not specify the location of the description document, a
url which can be used to construct the proper operations path is required nevertheless.

|aiopenapi3| can interface services in synchronous as well as asynchronous.
To create a traditional/blocking api client, provide a `session_factory` which return value annotation matches httpx_.Client,
httpx.AsyncClient for asynchronous clients.


After ingesting the description document, the api client object returned can be used to interface the service.
In case the services requires authentication, use :meth:`aiopenapi3.OpenAPI.authenticate` and
refer to :ref:`advanced:Authentication` for details.

.. code:: python

    from aiopenapi3 import OpenAPI
    TOKEN=""
    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")



Creating a request
------------------
While there is multiple ways to access a service `operations <https://try.gitea.io/api/swagger>`_, all return a Request which can be called.

The sad smiley interface :meth:`aiopenapi3.request.OperationIndex.__getattr__`.

.. code:: python

    req = api._.getUser
    m = req()
    m.id == user.id
    # True


or, in case the PathItem does not have an operationId, it is possible to create a request via :meth:`aiopenapi3.request.OperationIndex.__getitem__`

.. code:: python

    req = api._[("/user", "get")]
    m = req()
    m.id == user.id
    # True

or :meth:`aiopenapi3.OpenAPI.createRequest`.

.. code:: python

    req = api.createRequest(("/user", "get"))
    m = req()
    m.id == user.id
    # True


A list of all operations with operationIds exported by the service is available via the Iter.

.. code:: python

    operationIds = list(api._.Iter(api, False))
    print(operationIds)
    # ['activitypubPerson', 'activitypubPersonInbox', 'adminCronList' …

Creating a request to the service and inspecting the result:

.. code:: python

    user = api._.userGetCurrent()
    type(user)
    # <class 'aiopenapi3.me.User'>
    print(user.last_login)
    # "2022-12-07 16:50:07+00:00"
    type(user.created)



For more information of mentioned return valuew of type :meth:`aiopenapi3.request.RequestBase` refer to :ref:`api:Requests`.

Using Operation Tags
--------------------

In case the description document makes use of operation tags, the sad smiley can make use of them as well,
scoping the access to the methods.

.. code:: python

    t = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json", use_operation_tags=True)
    t.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")

    sorted(filter(lambda x: x.partition(".")[0] == "user", t._.Iter(api, True)))
    # ['user.createCurrentUserRepo', 'user.getUserSettings' …

    n = t._.user.userGetCurrent()
    n.id == user.id
    # True

Operation Parameters
--------------------

Operations may require Parameters or a Body.

To create a body which does validates according to the description document, the Requests :obj:`aiopenapi3.v30.glue.Request.data` property can be used.
Client side validation of the body is not required but very helpful in case the service does not accept the request.

.. code:: python

    bt = api._.createCurrentUserRepo.data.get_type()
    bt
    # <class 'aiopenapi3.me.CreateRepoOption'>
    body = bt.parse_obj({"name":"rtd", "default_branch":"main", "description":"Read The Docs Example Repository"})
    repo = api._.createCurrentUserRepo(data=body.dict(exclude_defaults=True))

|aiopenapi3| takes care of Parameters in path, query or header.
The parameters of a request can be inspected via :obj:`aiopenapi3.v30.glue.Request.parameters`.

.. code:: python

    api._.repoGet()
    # Traceback (most recent call last):
    # …
    # ValueError: Required Parameter ['owner', 'repo'] missing (provided [])

    api._.repoGet.parameters
    # [Parameter(extensions=None, name='owner', in_=<_In.path: 'path'>, description='owner of the repo', required=True, schema_=None, type='string', format=None, allowEmptyValue=None, items=None, collectionFormat=None, default=None, maximum=None, exclusiveMaximum=None, minimum=None, exclusiveMinimum=None, maxLength=None, minLength=None, pattern=None, maxItems=None, minItems=None, uniqueItems=None, enum=None, multipleOf=None), Parameter(extensions=None, name='repo', in_=<_In.path: 'path'>, description='name of the repo', required=True, schema_=None, type='string', format=None, allowEmptyValue=None, items=None, collectionFormat=None, default=None, maximum=None, exclusiveMaximum=None, minimum=None, exclusiveMinimum=None, maxLength=None, minLength=None, pattern=None, maxItems=None, minItems=None, uniqueItems=None, enum=None, multipleOf=None)]

    list(map(lambda y: y.name, filter(lambda x: x.required==True, api._.repoGet.parameters)))
    # ['owner', 'repo']

    r = api._.repoGet(parameters={"owner":user.login, "repo":"rtd"})

Using body and parameters does not surprise:

.. code:: python

    import codecs
    body = api._.repoCreateFile.data.get_type().parse_obj({'name':'README.md', "contents":codecs.encode(b"# everything starts somewhere", "base64")})
    commit = api._.repoCreateFile(parameters={"owner":user.login, "repo":"rtd", "filepath":"README.md"}, data=body)

    commit.commit.sha
    # 'b128a6f7b1927d5be78861717cf505fc095befb9'


And …

.. code:: python

    api._.repoDelete(parameters={"owner":user.login, "repo":"rtd"})

async
=====
Difference when using asyncio - await.

.. code:: python

    import asyncio
    from aiopenapi3 import OpenAPI
    TOKEN=""

    REPO = "rtd-asyncio"

    async def example():
        api = await OpenAPI.load_async("https://try.gitea.io/swagger.v1.json")
        api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")


        operationIds = list(api._.Iter(api, False))
        print(operationIds)
        # ['activitypubPerson', 'activitypubPersonInbox', 'adminCronList' …

        user = await api._.userGetCurrent()
        req = api.createRequest(("/user", "get"))

        m = await req()
        assert m.id == user.id

        t = await OpenAPI.load_async("https://try.gitea.io/swagger.v1.json", use_operation_tags=True)
        t.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")

        sorted(filter(lambda x: x.partition(".")[0] == "user", t._.Iter(api, True)))
        # ['user.createCurrentUserRepo', 'user.getUserSettings' …

        n = await t._.user.userGetCurrent()
        assert n.id == user.id


        bt = api._.createCurrentUserRepo.data.get_type()
        body = bt.parse_obj({"name":REPO, "default_branch":"main", "description":"Read The Docs Example Repository"})
        repo = await api._.createCurrentUserRepo(data=body.dict(exclude_defaults=True))

        r = await api._.repoGet(parameters={"owner":user.login, "repo":REPO})

        import codecs
        body = api._.repoCreateFile.data.get_type().parse_obj({'name':'README.md', "contents":codecs.encode(b"# everything starts somewhere", "base64")})
        commit = await api._.repoCreateFile(parameters={"owner":user.login, "repo":REPO, "filepath":"README.md"}, data=body)

        commit.commit.sha
        # 'b128a6f7b1927d5be78861717cf505fc095befb9'


        await api._.repoDelete(parameters={"owner":user.login, "repo":REPO})

    asyncio.run(example())


Command line
============
The aiopenapi3 cli provides commands to

* `convert` (compatibility loaded) yaml -> json
* `validate` description documents
* `call` operations

Some parameters are shared with all sub-commands:

* `--location` - redirect description documents loads to these local path, stripping the dd path to the name. Multiple locations are possible, the loader will try.
* `--cache` - use a serialized/pickled version / serialize/pickle after parsing
* `--plugins` - import a python document and load classes of it to use as plugins
* `--verbose`
* `--profile` - cProfile the command execution
* `--tracemalloc` - tracemalloc the execution

global parameters
-----------------

tracemalloc
^^^^^^^^^^^

tracemalloc provides information about memory usage:

.. code::

    Top 25 lines
    #1: HERE/aiopenapi3/openapi.py:631: 34836.6 KiB
        api = pickle.load(f)
    #2: HERE/pydantic/pydantic/fields.py:302: 13978.3 KiB
        field_info = FieldInfo(
    #3: HERE/aiopenapi3/model.py:206: 3816.2 KiB
        class Config:
    #4: /usr/lib/python3.10/abc.py:106: 3652.2 KiB
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
    #5: /usr/lib/python3.10/abc.py:123: 3640.0 KiB
        return _abc_subclasscheck(cls, subclass)
    …
    1065 other: 5515.0 KiB
    Total allocated size: 84830.4 KiB


profile
^^^^^^^

profiling provides information about function execution speed/ncalls:

.. code::

            6409418 function calls (6246933 primitive calls) in 19.742 seconds

       Ordered by: cumulative time

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            1    0.000    0.000   19.753   19.753 HERE/openapi3/aiopenapi3/cli.py:232(cmd_call)
            1    0.000    0.000   19.228   19.228 HERE/openapi3/aiopenapi3/openapi.py:623(cache_load)
            1    0.784    0.784   18.892   18.892 HERE/openapi3/aiopenapi3/openapi.py:395(_init_schema_types)
    8380/5724    0.032    0.000   16.059    0.003 HERE/openapi3/aiopenapi3/base.py:290(get_type)
    5910/5709    0.060    0.000   16.037    0.003 HERE/openapi3/aiopenapi3/base.py:274(set_type)
    5910/5709    0.051    0.000   15.928    0.003 HERE/openapi3/aiopenapi3/model.py:74(from_schema)
         2083    0.021    0.000   12.627    0.006 /usr/lib/python3.10/types.py:69(new_class)
         2083    0.445    0.000   12.549    0.006 HERE/pydantic/pydantic/main.py:123(__new__)
        10726    0.107    0.000    8.882    0.001 HERE/pydantic/pydantic/fields.py:485(infer)
    …

commands
--------

validate
^^^^^^^^

.. code::

    aiopenapi3 validate tests/fixtures/with-broken-links.yaml

    6 validation errors for OpenAPISpec
    paths -> /with-links -> get -> responses -> 200 -> links -> exampleWithBoth -> __root__
     operationId and operationRef are mutually exclusive, only one of them is allowed (type=value_error.spec; message=operationId and operationRef are mutually exclusive, only one of them is allowed; element=None)
    paths -> /with-links -> get -> responses -> 200 -> links -> exampleWithBoth -> $ref
     field required (type=value_error.missing)
    paths -> /with-links -> get -> responses -> 200 -> $ref
     field required (type=value_error.missing)
    paths -> /with-links-two -> get -> responses -> 200 -> links -> exampleWithNeither -> __root__
     operationId and operationRef are mutually exclusive, one of them must be specified (type=value_error.spec; message=operationId and operationRef are mutually exclusive, one of them must be specified; element=None)
    paths -> /with-links-two -> get -> responses -> 200 -> links -> exampleWithNeither -> $ref
     field required (type=value_error.missing)
    paths -> /with-links-two -> get -> responses -> 200 -> $ref
     field required (type=value_error.missing)


For valid description documents, it is possible to see some basic statistics about the documents structure, the number of operations and components.schemas/definitions, not including implicit/PathItem defined schemas.

.. code::

    aiopenapi3 -v validate tests/fixtures/petstore-expanded.yaml
    …  0:00:00.018789 (processing time)
    … 4 #operations
    … 4 #operations (with operationId)
    … 0 tests/fixtures/petstore-expanded.yaml: 3
    … 3 schemas total
    OK


call
^^^^

While  `restish <https://github.com/danielgtaylor/restish>`_ will be the better choice calling API from the cli - it is possible with aiopenapi3 as well.

plugins
"""""""

Description document mangling may be required, therefore plugins can be used.

.. code::

    aiopenapi3 -P tests/petstore_test.py:OnDocument \
    call https://petstore.swagger.io/v2/swagger.json createUser \
    --authenticate '{"api_key":"special-key"}'  \
    --data '{"id":1, "username": "bozo", "firstName": "Bozo", "lastName": "Smith", "email": "bozo@email.com", "password": "letmemin", "phone": "111-222-333", "userStatus": 3 }'

.. code:: json

    {
      "code": 200,
      "message": "1",
      "type": "unknown"
    }


filter
""""""

jmespath expressions can be used to massage the result via ``--format``

.. code::

    aiopenapi3 -P tests/petstore_test.py:OnDocument \
    call https://petstore.swagger.io/v2/swagger.json findPetsByStatus \
    --parameters '{"status": ["available", "pending"]}' \
    --authenticate '{"petstore_auth":"test"}' \
    --format "[0]"

.. code:: json

    {
      "category": {
        "id": 0,
        "name": "string"
      },
      "id": 9223372036854589760,
      "name": "doggie",
      "photoUrls": [
        "string"
      ],
      "status": "available",
      "tags": [
        {
          "id": 0,
          "name": "string"
        }
      ]
    }


.. code::

    …
    --format "[? name=='doggie' && status == 'available'].{name:name, photo:photoUrls} | [0:2]"

.. code:: json

    [
      {
        "name": "doggie",
        "photo": [
          "non eu",
          "Duis Lorem"
        ]
      },
      {
        "name": "doggie",
        "photo": [
          "string"
        ]
      }
    ]
