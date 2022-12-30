.. include:: links.rst

API
===

General
"""""""
.. autoclass:: aiopenapi3.OpenAPI
    :members: authenticate, createRequest, load_async, load_file, load_sync, loads, copy, cache_load, cache_store, _


Requests
""""""""

Requests encapsulate the required information to call an operation, they compile the actual HTTP request sent, including authentication information, headers, parameters and the body.
In case of async usage, using AsyncRequest is transparent.

.. currentmodule:: aiopenapi3.request
.. autoclass:: RequestBase
    :members: data, parameters, request, __call__


.. inheritance-diagram:: aiopenapi3.v20.glue.Request aiopenapi3.v30.glue.Request aiopenapi3.v20.glue.AsyncRequest aiopenapi3.v30.glue.AsyncRequest
    :top-classes: aiopenapi3.request.RequestBase
    :parts: -1

.. autoclass:: aiopenapi3.v20.glue.Request

.. autoclass:: aiopenapi3.v20.glue.AsyncRequest

.. autoclass:: aiopenapi3.v30.glue.Request

.. autoclass:: aiopenapi3.v30.glue.AsyncRequest


Parameters
""""""""""

Parameters are part of the operation specification and can be in

* path e.g. `/users/{name}`

* query e.g. `/users?limit=50`

* header

.. inheritance-diagram:: aiopenapi3.v20.parameter.Parameter aiopenapi3.v30.parameter.Parameter
    :top-classes: aiopenapi3.base.ParameterBase, aiopenapi3.base.ObjectExtended
    :parts: -1

.. autoclass:: aiopenapi3.v20.parameter.Parameter
    :members:
    :noindex:

.. autoclass:: aiopenapi3.v30.parameter.Parameter
    :members:
    :noindex:

Parameter Encoding
^^^^^^^^^^^^^^^^^^

Each of those Parameters has a different encoding strategy for different argument types. e.g. encoding a `List[str]`
as query parameter or object in a header.
Additionally Swagger 2.0 has a different encoding strategy to OpenAPI 3.x.

.. autoclass:: aiopenapi3.v20.parameter._ParameterCodec
    :members:
    :noindex:

.. autoclass:: aiopenapi3.v30.parameter._ParameterCodec
    :members:


Plugin Interface
""""""""""""""""

Init Plugins
^^^^^^^^^^^^

Init plugins are used to signal the setup is done.

.. currentmodule:: aiopenapi3.plugin
.. autoclass:: aiopenapi3.plugin::Init.Context
    :members:

.. autoclass:: Init

Document Plugins
^^^^^^^^^^^^^^^^

Document plugins are used to mangle description documents.

.. autoclass:: aiopenapi3.plugin::Document.Context
    :members:

.. autoclass:: Document
    :members: loaded, parsed


Message Plugins
^^^^^^^^^^^^^^^

Message plugins are used to mangle message.

.. autoclass:: aiopenapi3.plugin::Message.Context
    :members:

.. autoclass:: Message
    :members: marshalled, parsed, received, sending, unmarshalled

Loader
""""""

The loader is used to access description documents.
Changing a Loaders YAML Loader may be required to parse description documents with improper tags,
e.g. values getting decoded as dates in a text.
The :class:`aiopenapi3.loader.YAMLCompatibilityLoader` provided removes decoding of
* timestamp
* value
* int
* book

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

.. currentmodule:: aiopenapi3.loader
.. autoclass:: Loader
    :members:


Exceptions
""""""""""

Description Document Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


Message
^^^^^^^

.. autoclass:: HTTPError
    :members:
    :undoc-members:

HTTPError is the base class for all request/response related errors.

.. inheritance-diagram:: aiopenapi3.errors.RequestError aiopenapi3.errors.ResponseError
   :top-classes: aiopenapi3.errors.HTTPError
   :parts: -2

.. autoclass:: RequestError
    :members:
    :undoc-members:

A RequestError typically wraps an `error <https://www.python-httpx.org/exceptions/>`_ of the underlying httpx_ library.

.. autoclass:: ResponseError
    :members:
    :undoc-members:

ReponseErrors indicate the response does not match the expectation/definition in the description document.
Most ReponseErrors can be mitigated around using :doc:`plugins </plugin>` to match the protocol to the description
document.

.. inheritance-diagram:: aiopenapi3.errors.ContentTypeError aiopenapi3.errors.HTTPStatusError aiopenapi3.errors.ResponseDecodingError aiopenapi3.errors.ResponseSchemaError
   :top-classes: aiopenapi3.errors.ResponseError
   :parts: -2

.. autoclass:: ContentTypeError
    :members:
    :undoc-members:

.. autoclass:: HTTPStatusError
    :members:
    :undoc-members:

.. autoclass:: ResponseDecodingError
    :members:
    :undoc-members:

.. autoclass:: ResponseSchemaError
    :members:
    :undoc-members:
