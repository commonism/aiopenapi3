.. aiopenapi3 documentation master file, created by
   sphinx-quickstart on Sun Dec 25 15:28:14 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: links.rst

############
|aiopenapi3|
############

    *If you can't make it perfect, make it adjustable.*

|aiopenapi3| is a client library to interface RESTful services using OpenAPI_/Swagger description documents,
built upon pydantic_ for data validation/coercion and httpx_ for transport.
Located on `github <https://github.com/commonism/aiopenapi3>`_.


.. rubric:: No code generation

Suits the code-first pattern for REST services used by major frameworks
(`FastAPI <https://github.com/tiangolo/fastapi>`_, `Django REST framework <https://www.django-rest-framework.org/>`_) as well as
design first APIs.

.. rubric:: Features & Limitations

While aiopenapi3 supports some of the more exotic features of the Swagger/OpenAPI specification, e.g.:

* multilingual

  * Swagger 2.0
  * OpenAPI 3.0
  * OpenAPI 3.1

* multi file description documents
* recursive schemas
* additionalProperties mixed with properties
* `additionalProperties <https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#model-with-mapdictionary-properties>`_
* `Discriminator/Polymorphism <https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#models-with-polymorphism-support>`_
* :doc:`plugin interface </plugin>` to mangle description documents and messages
* :ref:`api:Parameter Encoding`
* :ref:`advanced:Forms`
* :ref:`advanced:mutualTLS` authentication
* :ref:`Request <advanced:Request Streaming>` and :ref:`Response <advanced:Response Streaming>` streaming to reduce memory usage
* Culling :ref:`extra:Large Description Documents`

some aspects of the specifications are implemented loose

* `Schema Composition <http://json-schema.org/understanding-json-schema/reference/combining.html>`_

  * oneOf - validation does not care if more than one matches
  * anyOf - implemented as oneOf
  * allOf - merging Schemas is limited wrt. to merge conflicts

and other aspects of the specification are not implemented at all

* `Conditional Subschemas <http://json-schema.org/understanding-json-schema/reference/conditionals.html>`_

  * dependentRequired
  * dependentSchemas
  * If-Then-Else
  * Implication

* non-unique parameter names in an operations headers/path/query
