.. include:: links.rst

*******
Plugins
*******

To assist dealing with differences in the description document and the protocol, |aiopenapi3| provides a capable plugin
interface which allows mangling the description document and the messages sent/received to match.

Init
====

Init plugins are run after the initialization of the OpenAPI object.
The following examples modifies specific pydantic models to allow unknown properties.

.. code:: python

    class DellInit(aiopenapi3.plugin.Init):
        def initialized(self, ctx):
            """
            Resource_Oem & Attributes are objects with additionalProperties
            the default will ignore unknown properties
            """

            def schemas(name, fn):
                for doc in self.api._documents.values():
                    schema = doc.components.schemas.get(name, None)
                    if not schema:
                        continue
                    fn(doc, schema)

            schemas("Resource_Oem", lambda doc, schema:
                setattr(schema.get_type().Config, "extra", pydantic.Extra.allow))
            schemas("DellAttributes_v1_0_0_DellAttributes",
                    lambda doc, schema: setattr(
                        doc.components.schemas["DellAttributes_v1_0_0_Attributes"].get_type().Config,
                        "extra",
                        pydantic.Extra.allow)
                    )
            return ctx

Document
========

As an example, due to a `bug #21997 <https://github.com/go-gitea/gitea/issues/21997>`_ the response repoGetArchive operation of gitea does not match the content type of the description document:

.. code:: python

    from aiopenapi3 import OpenAPI
    import codecs

    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json")
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")

    user = api._.userGetCurrent()
    repo = api._.createCurrentUserRepo(data={"name":"rtd"})

    body = api._.repoCreateFile.data.get_type().parse_obj({'name':'README.md', "contents":codecs.encode(b"# everything starts somewhere", "base64")})
    commit = api._.repoCreateFile(parameters={"owner":user.login, "repo":"rtd", "filepath":"README.md"}, data=body)

    api._.repoGetArchive(parameters={"owner":user.login, "repo":"rtd", "archive":"main.tar.gz"})
    # Traceback (most recent call last):
    # aiopenapi3.errors.ContentTypeError: (… 'Unexpected Content-Type application/octet-stream returned for operation repoGetArchive (expected application/json)' …


Using a Document plugin to modify the parsed description document to state the content type "application/octet-stream" for the repoGetArchive operation.

.. code:: python

    import tarfile
    import io

    class ContentType(aiopenapi3.plugin.Document):
        def parsed(self, ctx):
            try:
                ctx.document["paths"]["/repos/{owner}/{repo}/archive/{archive}"]["get"]["produces"] = ["application/octet-stream"]
            except Exception as e:
                print(e)
            return ctx

    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json", plugins=[ContentType()])
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")
    user = api._.userGetCurrent()
    data = api._.repoGetArchive(parameters={"owner":user.login, "repo":"rtd", "archive":"main.tar.gz"})

    tarfile.open(mode="r:gz", fileobj=io.BytesIO(data)).getmembers()
    # [<TarInfo 'rtd' at 0x7fe92cdd0580>, <TarInfo 'rtd/README.md' at 0x7fe92cdd01c0>]

Message
=======

For messages sent, the Plugin callback order is:
    marshalled -> sending

For messages received:
    received -> parsed -> unmarshalled

This treatment is about a `bug #22048 <https://github.com/go-gitea/gitea/issues/22048>`_ in the
`repoGetPullRequestCommits <https://try.gitea.io/api/swagger#/repository/repoGetPullRequestCommits>`_ operation.
The returned parameter `X-Total` is not set, `X-Total-Count` is set instead. To mitigate we provide a message plugin
which copies the value to `X-Total` in the :meth:`aiopenapi3.plugin.Message.received` callback.

.. code:: python

    class repoGetPullRequestCommitsMessage(aiopenapi3.plugin.Message):
        def received(self, ctx: "Message.Context") -> "Message.Context":
            if ctx.operationId != "repoGetPullRequestCommits":
                return ctx
            try:
                if ctx.headers.get("X-Total", None) is None:
                    ctx.headers["X-Total"] = ctx.headers.get("X-Total-Count", 0)
            except Exception as e:
                print(e)
            return ctx

    api = OpenAPI.load_sync("https://try.gitea.io/swagger.v1.json", plugins=[repoGetPullRequestCommitsMessage()])
    api.authenticate(AuthorizationHeaderToken=f"token {TOKEN}")

    now = datetime.datetime.now()
    user = api._.userGetCurrent()
    repo = "".join(random.choice(string.ascii_lowercase) for i in range(6))

    DEFAULTS = {"repo":repo, "owner":user.login}

    body = api._.createCurrentUserRepo.data.get_type().construct(name=repo, private=True, default_branch="main")
    repo = api._.createCurrentUserRepo(data=body)

    body = api._.repoCreateFile.data.get_type().construct(content=codecs.encode(b"# README", "base64"))
    f = api._.repoCreateFile(parameters={**DEFAULTS, "filepath":"README.md"}, data=body)

    branch = f"next-{now.timestamp():.0f}"
    body = api._.repoCreateBranch.data.get_type().construct(new_branch_name=branch, old_branch_name="main")
    data = api._.repoCreateBranch(parameters=DEFAULTS, data=body)

    body = api._.repoCreatePullRequest.data.get_type().construct(base=repo.default_branch, head=branch, title=f"WIP: doing {now.timestamp():.0f}")
    pr = api._.repoCreatePullRequest(parameters=DEFAULTS, data=body)

    #
    filepath = "README.md"
    content = f"# README {now.timestamp():.0f}"
    content = codecs.encode(content.encode(), "base64")

    g = api._.repoGetContents(parameters={**DEFAULTS, "filepath": filepath, "ref": branch})
    body = api._.repoUpdateFile.data.get_type().from_obj(
        dict(content=content, message=f"update {filepath}", sha=f.content.sha, branch=branch))
    api._.repoUpdateFile(parameters={**DEFAULTS, "filepath": filepath}, data=body)

    headers, commits = api._.repoGetPullRequestCommits(parameters={**DEFAULTS, "index":pr.number}, return_headers=True)

    assert ["X-Total"] in headers

    api._.repoDelete(parameters=DEFAULTS)



Other examples for Message plugins:

… the `ConnectorType` is an enum value the services does not honor:

.. code:: python

    class SerialInterface(Message):
        def parsed(self, ctx):
            if "ConnectorType" in ctx.expected_type.get_type().__fields__ and ctx.parsed.get("ConnectorType", None) == 'DB9 Male.':
                ctx.parsed["ConnectorType"] = "DB9 Male"
            return ctx

… the service is missing required Fields:

.. code:: python

    class IdMissingMessage(Message):
        def parsed(self, ctx):
            rq = set(map(lambda x: x.alias, filter(lambda x: x.required == True, ctx.expected_type.get_type().__fields__.values())))
            av = set(ctx.parsed.keys())
            m = rq - av
            if m:
                print(f"missing {m} at {ctx.parsed}")
            for k in m:
                ctx.parsed[k] = ""


… the service uses invalid datetime values (month & day == 0):

.. code:: python

    class DateError(Message):
        def __init__(self, key):
            super().__init__()
            self.key = key

        def parsed(self, ctx):
            if self.key in ctx.expected_type.get_type().__fields__:
                v = ctx.parsed.get(self.key, None)
                if v in ['0000-00-00T00:00:00+00:00',"00:00:00Z"]:
                    # '0000-00-00T00:00:00+00:00'
                    del ctx.parsed[self.key]
            return ctx
