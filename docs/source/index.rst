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
It's located on `github <https://github.com/commonism/aiopenapi3>`_.

**********************
Features & Limitations
**********************

While aiopenapi3 supports some of the more exotic features of the Swagger/OpenAPI specification, e.g.:

* multilingual

  * Swagger 2.0
  * OpenAPI 3.0
  * OpenAPI 3.1

* multi file description documents
* recursive schemas
* `additionalProperties <https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#model-with-mapdictionary-properties>`_
* `Discriminator/Polymorphism <https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#models-with-polymorphism-support>`_
* :doc:`plugin interface </plugin>` to mangle description documents and messages
* :ref:`api:Parameter Encoding`

some aspects of the specifications can not be supported.

* `Schema Composition <http://json-schema.org/understanding-json-schema/reference/combining.html>`_

  * oneOf - validation does not care if more than one matches
  * anyOf - implemented as oneOf
  * allOf - merging Schemas is limited wrt. to merge conflicts

* additionalProperties mixed with properties
* non-unique parameter names in an operations headers/path/query

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   install
   use
   advanced
   plugin
   api

.. toctree::
   :hidden:


.. comment out
   Indices and tables
   ==================

   * :ref:`genindex`
   * :ref:`modindex`
   * :ref:`search`
