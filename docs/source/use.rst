.. include:: links.rst

Using aiopenapi3
----------------

As a client
^^^^^^^^^^^

Creating a client from a description document
"""""""""""""""""""""""""""""""""""""""""""""

|aiopenapi3| can ingest description documents from different sources.

-   :meth:`aiopenapi3.OpenAPI.loads` - from string
-   :meth:`aiopenapi3.OpenAPI.load_file` - from a local file
-   :meth:`aiopenapi3.OpenAPI.load_sync` - from the web/syncronous
-   :meth:`aiopenapi3.OpenAPI.load_async` - from the web/asynchronous

|aiopenapi3| can interface services in synchronous as well as asynchronous.
To create a traditional/blocking api client, provide a `session_factory` which return value annotation matches httpx_.Client,
httpx.AsyncClient for asynchronous clients.


After ingesting the description document, the api client object returned can be used to interface the service.
In case the services requires authentication, use :meth:`aiopenapi3.OpenAPI.authenticate`.

.. code:: python

    from aiopenapi3 import OpenAPI
    TOKEN=""
    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")


Creating a request
""""""""""""""""""
The service `operations <https://try.gitea.io/api/swagger>`_ can be accessed via the sad smiley interface.

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

In case the PathItem does not have an operationId, it is possible to create a request via
:meth:`aiopenapi3.OpenAPI.createRequest`.

.. code:: python

    req = api.createRequest(("/user", "get"))
    m = req()
    m.id == user.id
    # True

Using Operation Tags
""""""""""""""""""""

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
""""""""""""""""""""

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
^^^^^
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


As validator
^^^^^^^^^^^^
|aiopenapi3| can be used to validate description documents.

.. code::

    aiopenapi3 tests/fixtures/with-broken-links.yaml

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