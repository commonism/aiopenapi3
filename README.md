# aiopenapi3

A Python [OpenAPI 3 Specification](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md) client and validator for Python 3.

[![Test](https://github.com/commonism/aiopenapi3/workflows/Codecov/badge.svg?event=push&branch=master)](https://github.com/commonism/aiopenapi3/actions?query=workflow%3ACodecov+event%3Apush+branch%3Amaster)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/commonism/aiopenapi3/master.svg)](https://results.pre-commit.ci/latest/github/commonism/aiopenapi3/master)
[![Coverage](https://img.shields.io/codecov/c/github/commonism/aiopenapi3)](https://codecov.io/gh/commonism/aiopenapi3)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/aiopenapi3.svg)](https://pypi.org/project/aiopenapi3)


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


## Usage as a Client

This library also functions as an interactive client for arbitrary OpenAPI 3
specs. For example, using `Linode's OpenAPI 3 Specification`_ for reference:

*Unfortunately I do not have access to the Linode API to validate object creation*

### asyncio
```python
from aiopenapi3 import OpenAPI
url = "https://www.linode.com/docs/api/openapi.yaml"

api = await OpenAPI.load_async(url)

# call operations and receive result models
regions = await api._.getRegions()
```

### blocking io
```python
from aiopenapi3 import OpenAPI
url = "https://www.linode.com/docs/api/openapi.yaml"
my_token = "Gae6aikaegainoor"
api = OpenAPI.load_sync(url)

# call operations and receive result models
regions = api._.getRegions()


```

### objects
pydantic is used for the models.
https://pydantic-docs.helpmanual.io/usage/exporting_models/

```python
from aiopenapi3 import OpenAPI
url = "https://www.linode.com/docs/api/openapi.yaml"

api = await OpenAPI.load_sync(url)

# call operations and receive result models
regions = await api._.getRegions()

regions.__fields_set__
{'results', 'page', 'pages', 'data'}

import json
print(json.dumps((list(filter(lambda x: 'eu-west' in x.id, regions.data))[0]).dict(), indent=2))
{
  "id": "eu-west",
  "country": "uk",
  "capabilities": [
    "Linodes",
    "NodeBalancers",
    "Block Storage",
    "Kubernetes",
    "Cloud Firewall"
  ],
  "status": "ok",
  "resolvers": {
    "ipv4": "178.79.182.5,176.58.107.5,176.58.116.5,176.58.121.5,151.236.220.5,212.71.252.5,212.71.253.5,109.74.192.20,109.74.193.20,109.74.194.20",
    "ipv6": "2a01:7e00::9,2a01:7e00::3,2a01:7e00::c,2a01:7e00::5,2a01:7e00::6,2a01:7e00::8,2a01:7e00::b,2a01:7e00::4,2a01:7e00::7,2a01:7e00::2"
  }
}
```

#### discriminators
discriminators are supported as well, but the linode api can't be used to show how to use them.
look at [aiopenapi3/tests/model_test.py](https://github.com/commonism/aiopenapi3/blob/master/tests/model_test.py) test_model.

### authentication
```python
my_token = "Gae6aikaegainoor"
api.authenticate(personalAccessToken=my_token)

# call an operation that requires authentication
linodes  = api._.getLinodeInstances()
```

HTTP basic authentication and HTTP digest authentication works like this:
```python
# authenticate using a securityScheme defined in the spec's components.securitySchemes
# Tuple with (username, password) as second argument
api.authenticate(basicAuth=('username', 'password'))
```

Resetting authentication tokens:
```python
api.authenticate(None)
```

### parameters

```python
# call an opertaion with parameters
linode = api._.getLinodeInstance(parameters={"linodeId": 123})
```

### body
```python
body = api._.createLinodeInstance.args()["data"].model({"region":"us-east", "type":"g6-standard-2"})
print(json.dumps(body.dict(), indent=2))
{
  "image": null,
  "root_pass": null,
  "authorized_keys": null,
  "authorized_users": null,
  "stackscript_id": null,
  "stackscript_data": null,
  "booted": null,
  "backup_id": null,
  "backups_enabled": null,
  "swap_size": null,
  "type": "g6-standard-2",
  "region": "us-east",
  "label": null,
  "tags": null,
  "group": null,
  "private_ip": null,
  "interfaces": null
}

print(json.dumps(body.dict(exclude_unset=True), indent=2))
{
  "type": "g6-standard-2",
  "region": "us-east"
}


>>>
new_linode = api._.createLinodeInstance(data=body)
```

## Validation Mode

Installing with the extra [cli] or running thodule allows to validate specs:

```
aiopenapi3 -h
usage: aiopenapi3 [-h] [-C] [-D [YAML_DISABLE_TAG]] [-l] [-v] name

Swagger 2.0, OpenAPI 3.0, OpenAPI 3.1 validator

positional arguments:
  name

optional arguments:
  -h, --help            show this help message and exit
  -C, --yaml-compatibility
                        disables type coercion for yaml types such as datetime, bool …
  -D [YAML_DISABLE_TAG], --yaml-disable-tag [YAML_DISABLE_TAG]
                        disable this tag from the YAML loader
  -l, --yaml-list-tags  list tags
  -v, --verbose         be verbose

```

The module can be run against a spec file to validate it like so::

```
python3 -m aiopenapi3 tests/fixtures/with-broken-links.yaml

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
```

In case the yaml not well formed, there are options to disable certain tags:

```
python -m aiopenapi3 -D tag:yaml.org,2002:timestamp -l -v linode.yaml
removing tag:yaml.org,2002:timestamp
tags:
	tag:yaml.org,2002:bool
	tag:yaml.org,2002:float
	tag:yaml.org,2002:int
	tag:yaml.org,2002:merge
	tag:yaml.org,2002:null
	tag:yaml.org,2002:value
	tag:yaml.org,2002:yaml

OK
```



## Real World issues
### YAML
The description document may no be valid yaml.
YAML type coercion can cause this.
```python
>>> yaml.safe_load(str(datetime.datetime.now().date()))
datetime.date(2022, 1, 12)

>>> yaml.safe_load("name: on")
{'name': True}

>>> yaml.safe_load('12_24: "test"')
{1224: 'test'}
```
Those can be turned of using the yload yaml.Loader argument to the Loader.

```python
import aiopenapi3.loader

OpenAPI.load…(…, loader=FileSystemLoader(pathlib.Path(dir), yload = aiopenapi3.loader.YAMLCompatibilityLoader))

```

All but these get disabled:

```
python -m aiopenapi3 -C -l -v linode.yaml
tags:
	tag:yaml.org,2002:float
	tag:yaml.org,2002:merge
	tag:yaml.org,2002:null
	tag:yaml.org,2002:yaml

```

### description document mismatch
In case the description document does not match the protocol, it may be required to alter the description, objects or data sent/received.
The [Plugin interface](https://github.com/commonism/aiopenapi3/blob/master/tests/plugin_test.py) can be used to alter any of those.
It can even be used to alter an invalid description document to be usable.


### the petstore.swagger.io
The [Swagger Petstore Examples API](https://petstore.swagger.io) is a good [example](https://github.com/commonism/aiopenapi3/tests/petstore_test.py) of an API with incomplete Description Document and invalid API responses.



## Logging
### HTTP Requests

```
export AIOPENAPI3_LOGGING_HANDLERS=debug
```

will force writing to `/tmp/aiopenapi3-debug.log`.\
It can be used to inspect Description Document downloads …
```
aiopenapi3.OpenAPI DEBUG Downloading Description Document TS29122_CommonData.yaml using WebLoader(baseurl=https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS24558_Eecs_ServiceProvisioning.yaml) …
httpx._client DEBUG HTTP Request: GET https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS29122_CommonData.yaml "HTTP/1.1 200 OK"
aiopenapi3.OpenAPI DEBUG Resolving TS29571_CommonData.yaml#/components/schemas/Gpsi - Description Document TS29571_CommonData.yaml unknown …
aiopenapi3.OpenAPI DEBUG Downloading Description Document TS29571_CommonData.yaml using WebLoader(baseurl=https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS24558_Eecs_ServiceProvisioning.yaml) …
httpx._client DEBUG HTTP Request: GET https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS29571_CommonData.yaml "HTTP/1.1 200 OK"
aiopenapi3.OpenAPI DEBUG Resolving TS29122_MonitoringEvent.yaml#/components/schemas/LocationInfo - Description Document TS29122_MonitoringEvent.yaml unknown …
aiopenapi3.OpenAPI DEBUG Downloading Description Document TS29122_MonitoringEvent.yaml using WebLoader(baseurl=https://raw.githubusercontent.com/jdegre/5GC_APIs/master/TS24558_Eecs_ServiceProvisioning.yaml) …
```

and general httpx requests
```
httpx._client DEBUG HTTP Request: DELETE http://localhost:51965/v2/pets/e7e979fb-bf53-4a89-9475-da9369cb4dbc "HTTP/1.1 422 "
httpx._client DEBUG HTTP Request: GET http://localhost:54045/v2/openapi.json "HTTP/1.1 200 "
httpx._client DEBUG HTTP Request: POST http://localhost:54045/v2/pet "HTTP/1.1 201 "
```

## Running Tests

This project includes a test suite, run via ``pytest``.  To run the test suite,
ensure that you've installed the dependencies and then run ``pytest`` in the root
of this project.

```shell
PYTHONPATH=. pytest --cov=./ --cov-report=xml .
```
