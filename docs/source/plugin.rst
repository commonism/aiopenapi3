.. include:: links.rst

*******
Plugins
*******

To assist dealing with differences in the description document and the protocol, |aiopenapi3| provides a capable plugin
interface which allows mangling the description document and the messages sent/received to match.

Init
====

:class:`~aiopenapi3.plugin.Init` plugins are run at certain stages during the initialization of the OpenAPI object.
Available callbacks:

    * :meth:`~aiopenapi3.plugin.Init.schemas`
    * :meth:`~aiopenapi3.plugin.Init.paths`
    * :meth:`~aiopenapi3.plugin.Init.initialized`


Examples
--------

initialized
^^^^^^^^^^^

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

reducing initialization processing time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Large -multi megabyte- APIs have a significant processing time.

Reducing this processing time during development is possible by limiting the number of objects initialized.

The schemas callback limits initialization to the schemas returned and their dependencies.
The paths callback removes all PathItems.

.. code:: python

    """
    to speed up things, we use some aiopenapi3 plugins to limit the loading process to the schemas required
    removing all paths
    """
    from aiopenapi3.plugin import Init, Document

    class SchemaSelector(Init):
        """
        remove the schemas we do not need models for
        """

        def __init__(self, *schemas):
            super().__init__()
            self._schemas = schemas

        def schemas(self, ctx: "Init.Context") -> "Init.Context":
            ctx.schemas = {k: ctx.schemas[k] for k in (set(self._schemas) & set(ctx.schemas.keys()))}
            return ctx

    class RemovePaths(Document):
        def parsed(self, ctx: "Document.Context") -> "Document.Context":
            """
            emtpy the paths - not needed
            """
            ctx.document["paths"] = {}
            return ctx

    selector = SchemaSelector(*(list(names) + [f"{name}Request" for name in names]))
    api = OpenAPI.load_file(..., plugins=[selector, RemovePaths()])


Document
========

:class:`~aiopenapi3.plugin.Document` plugins allow modification of the description document.
Available callbacks:

    * :meth:`~aiopenapi3.plugin.Document.loaded`
    * :meth:`~aiopenapi3.plugin.Document.parsed`


Examples
--------

As an example, due to a `bug #21997 <https://github.com/go-gitea/gitea/issues/21997>`_ the response repoGetArchive operation of gitea does not match the content type of the description document:

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


Message
=======

:class:`~aiopenapi3.plugin.Message` plugins allow modification of the messages sent/received.

For messages sent, the available callbacks are:

    * :meth:`~aiopenapi3.plugin.Message.marshalled`
    * :meth:`~aiopenapi3.plugin.Message.sending`

Avaiable callbacks for messages received:

    * :meth:`~aiopenapi3.plugin.Message.received`
    * :meth:`~aiopenapi3.plugin.Message.parsed`
    * :meth:`~aiopenapi3.plugin.Message.unmarshalled`

Examples
--------

Signing the Body
^^^^^^^^^^^^^^^^

This example signs a message body by providing a HMAC512 signature in the http headers:

.. code:: python

    class XHookSignature(aiopenapi3.plugin.Message):
        def sending(self, ctx: "Message.Context") -> "Message.Context":
            ctx.headers["X-Hook-Signature"] = sign(ctx.sending)
            return ctx

    api = await aiopenapi3.OpenAPI.load_async(url, plugins=[XHookSignature()])


Correct an invalid Responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Aliasing a property
"""""""""""""""""""

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



Correcting Spelling for an enum
"""""""""""""""""""""""""""""""

… the `ConnectorType` is an enum value the services does not honor:

.. code:: python

    class SerialInterface(Message):
        def parsed(self, ctx):
            if "ConnectorType" in ctx.expected_type.get_type().__fields__ and ctx.parsed.get("ConnectorType", None) == 'DB9 Male.':
                ctx.parsed["ConnectorType"] = "DB9 Male"
            return ctx


Adding missing properties
"""""""""""""""""""""""""

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


Correcting an invalid datetime value
""""""""""""""""""""""""""""""""""""

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
