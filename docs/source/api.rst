.. include:: links.rst

***
API
***

General
=======
.. autoclass:: aiopenapi3.OpenAPI
    :members: authenticate, createRequest, load_async, load_file, load_sync, loads, clone, cache_load, cache_store, _


Requests
========

.. inheritance-diagram:: aiopenapi3.v20.glue.Request aiopenapi3.v30.glue.Request aiopenapi3.v20.glue.AsyncRequest aiopenapi3.v30.glue.AsyncRequest
    :top-classes: aiopenapi3.request.RequestBase
    :parts: -1

Requests encapsulate the required information to call an operation.
They

    - compile the actual HTTP request to be sent, including authentication information, path, headers, parameters and the body.
    - send it
    - receive the result
    - process it
    - and return the model of the data

.. currentmodule:: aiopenapi3.request
.. autoclass:: RequestBase
    :members: data, parameters, request, stream, __call__, operation, root

.. currentmodule:: aiopenapi3.request
.. autoclass:: AsyncRequestBase
    :members: data, parameters, request, stream, __call__, operation, root


The different major versions of the OpenAPI protocol require their own Request/AsyncRequest.

.. autoclass:: aiopenapi3.v20.glue.Request

.. autoclass:: aiopenapi3.v20.glue.AsyncRequest

.. autoclass:: aiopenapi3.v30.glue.Request

.. autoclass:: aiopenapi3.v30.glue.AsyncRequest


OperationIndex
==============
.. currentmodule:: aiopenapi3.request
.. autoclass:: OperationIndex
    :members: __getattr__, __getitem__


Parameters
==========

Parameters are part of the operation specification and can be in

* path e.g. `/users/{name}`
* query e.g. `/users?limit=50`
* header
* cookie

Used to compile a :class:`aiopenapi3.request.RequestBase`, not meant to be dealt with besides debugging.

.. inheritance-diagram:: aiopenapi3.v20.parameter.Parameter aiopenapi3.v30.parameter.Parameter aiopenapi3.v31.parameter.Parameter aiopenapi3.v30.parameter.Header aiopenapi3.v31.parameter.Header
    :top-classes: aiopenapi3.v20.parameter._ParameterCodec, aiopenapi3.v30.parameter._ParameterCodec, aiopenapi3.base.ParameterBase, aiopenapi3.base.ObjectExtended
    :private-bases:
    :parts: -1

Parameter
---------
.. autoclass:: aiopenapi3.base.ParameterBase
    :noindex:

.. autoclass:: aiopenapi3.v20.parameter.Parameter
    :members:
    :undoc-members:
    :exclude-members: model_fields, model_config, SEPERATOR_VALUES, validate_ObjectExtended_extensions
    :inherited-members: BaseModel
    :noindex:

.. autoclass:: aiopenapi3.v30.parameter.Parameter
    :members:
    :undoc-members:
    :exclude-members: model_fields, model_config, validate_Parameter, validate_ObjectExtended_extensions
    :inherited-members: BaseModel
    :noindex:

.. autoclass:: aiopenapi3.v31.parameter.Parameter
    :members:
    :undoc-members:
    :exclude-members: model_fields, model_config, validate_Parameter, validate_ObjectExtended_extensions
    :inherited-members: BaseModel
    :noindex:

Header
------

.. autoclass:: aiopenapi3.v30.parameter.Header
    :members:
    :undoc-members:
    :exclude-members: model_fields, model_config, validate_Parameter, validate_ObjectExtended_extensions
    :inherited-members: BaseModel
    :noindex:

.. autoclass:: aiopenapi3.v31.parameter.Header
    :members:
    :undoc-members:
    :exclude-members: model_fields, model_config, validate_Parameter, validate_ObjectExtended_extensions
    :inherited-members: BaseModel
    :noindex:


Parameter Encoding
------------------

Each of those Parameters has a different encoding strategy for different argument types. e.g. encoding a `List[str]`
as query parameter or object in a header.
Additionally Swagger 2.0 has a different encoding strategy to OpenAPI 3.x.

.. autoclass:: aiopenapi3.v20.parameter._ParameterCodec
    :members:
    :exclude-members: SEPERATOR_VALUES
    :undoc-members:
    :private-members: _encode, _decode
    :noindex:

.. autoclass:: aiopenapi3.v30.parameter._ParameterCodec
    :members:
    :exclude-members: SEPERATOR_VALUES
    :undoc-members:
    :private-members: _encode, _decode
    :noindex:

Plugin Interface
================

.. inheritance-diagram:: aiopenapi3.plugin.Init aiopenapi3.plugin.Document aiopenapi3.plugin.Message
   :top-classes: aiopenapi3.plugin.Plugin
   :parts: -2

Init Plugins
------------

Init plugins are used during initialization, they can be used to modify PathItems or Schemas before generating the OperationIndex/Models.

:ref:`Examples <plugin:Init>`

.. currentmodule:: aiopenapi3.plugin
.. autoclass:: aiopenapi3.plugin::Init.Context
    :members: schemas, paths, initialized

.. autoclass:: Init
    :members: schemas, paths, initialized

Document Plugins
----------------

Document plugins are used to mangle description documents.

:ref:`Examples <plugin:Document>`

.. autoclass:: aiopenapi3.plugin::Document.Context
    :members: url, document

.. autoclass:: Document
    :members: loaded, parsed


Message Plugins
---------------

Message plugins are used to mangle message.

:ref:`Examples <plugin:Message>`

.. autoclass:: aiopenapi3.plugin::Message.Context
    :members: operationId, marshalled, sending, received, headers, status_code, content_type, parsed, expected_type, unmarshalled

.. autoclass:: Message
    :members: marshalled, sending, received, parsed, unmarshalled

Loader
======

The loader is used to access description documents.

:class:`aiopenapi3.loader.Loader` is the base class, providing flexibility to load description documents.

.. inheritance-diagram:: aiopenapi3.loader.FileSystemLoader aiopenapi3.loader.WebLoader aiopenapi3.loader.ChainLoader aiopenapi3.loader.RedirectLoader aiopenapi3.loader.ChainLoader
   :top-classes: aiopenapi3.loader.Loader
   :parts: -2


loading operation
-----------------

The order of operation for the loader is:

* :meth:`aiopenapi3.loader.Loader.get`

  * :meth:`aiopenapi3.loader.Loader.load`

    * :meth:`aiopenapi3.loader.Loader.decode`

      * :meth:`aiopenapi3.plugin.Document.loaded`

  * :meth:`aiopenapi3.loader.Loader.parse`

    * yaml?

      * yaml.load(yload)

    * json?

      * json.loads

  * :meth:`aiopenapi3.plugin.Document.parsed`

Loaders
-------

.. currentmodule:: aiopenapi3.loader
.. autoclass:: Loader
    :members:

.. autoclass:: FileSystemLoader

.. autoclass:: WebLoader

.. autoclass:: ChainLoader

The ChainLoader is useful when using multiple locations with description documents.
As an example, try to lookup the referenced description documents locally or from the web.

.. code:: python

        description_documents = Path("/data/description_documents")

        loader = ChainLoader(
                    RedirectLoader(description_documents / "dell"),
                    WebLoader(yarl.URL("https://redfish.dmtf.org/schemas/v1/")),
                    WebLoader(yarl.URL("http://redfish.dmtf.org/schemas/swordfish/v1/")),
        )

        api = OpenAPI.load_file(
            target, yarl.URL("openapi.yaml"), loader=loader
        )


.. autoclass:: RedirectLoader

The RedirectLoader allows redirecting to local resources. A description documents URI is stripped to the file name
of the document, and loaded relative to the basedir of the RedirectLoader.

.. code:: python

    RedirectLoader("description_documents/dell")


Exceptions
==========

There is different types of Exceptions used depending on the subsystem/failure.

.. inheritance-diagram:: aiopenapi3.errors.SpecError aiopenapi3.errors.ReferenceResolutionError aiopenapi3.errors.OperationParameterValidationError aiopenapi3.errors.ParameterFormatError aiopenapi3.errors.HTTPError aiopenapi3.errors.RequestError aiopenapi3.errors.ResponseError aiopenapi3.errors.ContentTypeError aiopenapi3.errors.HTTPStatusError aiopenapi3.errors.ResponseDecodingError aiopenapi3.errors.ResponseSchemaError aiopenapi3.errors.ContentLengthExceededError aiopenapi3.errors.HeadersMissingError
    :top-classes: aiopenapi3.errors.BaseError
    :parts: -2




Description Document Validation
-------------------------------

.. currentmodule:: aiopenapi3.errors
.. autoclass:: SpecError
    :members:
    :undoc-members:

.. autoclass:: ReferenceResolutionError
    :members:
    :undoc-members:

.. autoclass:: ParameterFormatError
    :members:
    :undoc-members:

.. autoclass:: OperationParameterValidationError
    :members:
    :undoc-members:




Message
-------

.. autoexception:: HTTPError
    :members:
    :undoc-members:

HTTPError is the base class for all request/response related errors.

.. inheritance-diagram:: aiopenapi3.errors.RequestError aiopenapi3.errors.ResponseError
   :top-classes: aiopenapi3.errors.HTTPError
   :parts: -2

.. autoexception:: RequestError
    :members:
    :undoc-members:

A RequestError typically wraps an `error <https://www.python-httpx.org/exceptions/>`_ of the underlying httpx_ library.

.. autoexception:: ResponseError
    :members:
    :undoc-members:

ResponseErrors indicate the response does not match the expectation/definition in the description document.
Most ResponseErrors can be mitigated around using :doc:`plugins </plugin>` to match the protocol to the description
document.

.. inheritance-diagram:: aiopenapi3.errors.ContentTypeError aiopenapi3.errors.ContentLengthExceededError  aiopenapi3.errors.HTTPStatusError aiopenapi3.errors.ResponseDecodingError aiopenapi3.errors.ResponseSchemaError aiopenapi3.errors.HeadersMissingError
   :top-classes: aiopenapi3.errors.ResponseError
   :parts: -2

.. autoexception:: ContentTypeError
    :members:
    :undoc-members:

.. autoexception:: ContentLengthExceededError
    :members:
    :undoc-members:

.. autoexception:: HTTPStatusError
    :members:
    :undoc-members:

.. autoexception:: ResponseDecodingError
    :members:
    :undoc-members:

.. autoexception:: ResponseSchemaError
    :members:
    :undoc-members:

.. autoexception:: HeadersMissingError
    :members:
    :undoc-members:

Extra
=====

Cull & Reduce
-------------

Reduce & Cull are Plugins limiting the models built to the minimum required to match the requirements of the supplied Operations
Code below will eleminate all schemas not required to serve the operations identified by the pattern/string match and http methods associated.

.. code:: python

    api = OpenAPI.load_sync(
        "http://127.0.0.1/api.yaml",
        plugins=[
            Cull(
                "getPetById",
                re.compile(r".*Pet.*"),
                ("/logout", ["get"]),
                (re.compile(r"^/user.*"), ["post"]),
            )
        ],
    )

.. currentmodule:: aiopenapi3.extra
.. autoclass:: Reduce
    :members: __init__
.. autoclass:: Cull
