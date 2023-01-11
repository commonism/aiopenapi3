# aiopenapi3

A Python [OpenAPI 3 Specification](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md) client and validator for Python 3.

[![Test](https://github.com/commonism/aiopenapi3/workflows/Codecov/badge.svg?event=push&branch=master)](https://github.com/commonism/aiopenapi3/actions?query=workflow%3ACodecov+event%3Apush+branch%3Amaster)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/commonism/aiopenapi3/master.svg)](https://results.pre-commit.ci/latest/github/commonism/aiopenapi3/master)
[![Coverage](https://img.shields.io/codecov/c/github/commonism/aiopenapi3)](https://codecov.io/gh/commonism/aiopenapi3)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/aiopenapi3.svg)](https://pypi.org/project/aiopenapi3)
[![Documentation Status](https://readthedocs.org/projects/aiopenapi3/badge/?version=latest)](https://aiopenapi3.readthedocs.io/en/latest/?badge=latest)


This project is a fork of [Dorthu/openapi3](https://github.com/Dorthu/openapi3/).

## Features
  * implements …
    * Swagger 2.0
    * OpenAPI 3.0.3
    * OpenAPI 3.1.0
  * description document parsing via [pydantic](https://github.com/samuelcolvin/pydantic)
    * recursive schemas (A.a -> A)
  * request body model creation via pydantic
    * pydantic compatible "format"-type coercion (e.g. datetime.interval)
    * additionalProperties (limited to string-to-any dictionaries without properties)
  * response body & header parsing via pydantic
  * blocking and nonblocking (asyncio) interface via [httpx](https://www.python-httpx.org/)
    * SOCKS5 via httpx_socks
  * tests with pytest & [fastapi](https://fastapi.tiangolo.com/)
  * providing access to methods and arguments via the sad smiley ._. interface
  * Plugin Interface/api to modify description documents/requests/responses to adapt to non compliant services
  * YAML type coercion hints for not well formatted description documents
  * Description Document dependency downloads (using the WebLoader)
    * logging
      * `export AIOPENAPI3_LOGGING_HANDLERS=debug` to get /tmp/aiopenapi3-debug.log


## Documentation
[API Documentation](https://aiopenapi3.readthedocs.io/en/latest/)


## Running Tests

This project includes a test suite, run via ``pytest``.  To run the test suite,
ensure that you've installed the dependencies and then run ``pytest`` in the root
of this project.

```shell
PYTHONPATH=. pytest --cov=./ --cov-report=xml .
```
