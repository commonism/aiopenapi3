"""
This file tests that paths are parsed and populated correctly
"""
import base64
import uuid
import pathlib

import pytest
import httpx
import yarl

from aiopenapi3 import OpenAPI
from aiopenapi3.errors import OperationParameterValidationError

URLBASE = "/"


def test_paths_exist(petstore_expanded):
    """
    Tests that paths are parsed correctly
    """
    petstore_expanded_spec = OpenAPI(URLBASE, petstore_expanded)

    assert "/pets" in petstore_expanded_spec.paths._paths
    assert "/pets/{id}" in petstore_expanded_spec.paths._paths
    assert len(petstore_expanded_spec.paths._paths) == 2


def test_operations_exist(petstore_expanded):
    """
    Tests that methods are populated as expected in paths
    """

    petstore_expanded_spec = OpenAPI(URLBASE, petstore_expanded)

    pets_path = petstore_expanded_spec.paths["/pets"]
    assert pets_path.get is not None
    assert pets_path.post is not None
    assert pets_path.put is None
    assert pets_path.delete is None

    pets_id_path = petstore_expanded_spec.paths["/pets/{id}"]
    assert pets_id_path.get is not None
    assert pets_id_path.post is None
    assert pets_id_path.put is None
    assert pets_id_path.delete is not None

    for operation in petstore_expanded_spec._:
        continue


def test_operation_populated(openapi_version, petstore_expanded):
    """
    Tests that operations are populated as expected
    """
    petstore_expanded_spec = OpenAPI(URLBASE, petstore_expanded)

    op = petstore_expanded_spec.paths["/pets"].get

    # check description and metadata populated correctly
    assert op.operationId == "findPets"
    assert op.description.startswith("Returns all pets from the system")
    assert op.summary is None

    # check parameters populated correctly
    assert len(op.parameters) == 2

    param1 = op.parameters[0]
    assert param1.name == "tags"
    assert param1.in_ == "query"
    assert param1.description == "tags to filter by"
    assert param1.required == False
    assert param1.style == "form"
    assert param1.schema_ is not None
    assert param1.schema_.type == "array"
    assert param1.schema_.items.type == "string"

    param2 = op.parameters[1]
    assert param2.name == "limit"
    assert param2.in_ == "query"
    assert param2.description == "maximum number of results to return"
    assert param2.required == False
    assert param2.schema_ is not None
    assert param2.schema_.type == "integer"
    assert param2.schema_.format == "int32"

    # check that responses populated correctly
    assert "200" in op.responses
    assert "default" in op.responses
    assert len(op.responses) == 2

    resp1 = op.responses["200"]
    assert resp1.description == "pet response"
    assert len(resp1.content) == 1
    assert "application/json" in resp1.content
    con1 = resp1.content["application/json"]
    assert con1.schema_ is not None
    assert con1.schema_.type == "array"
    # we're not going to test that the ref resolved correctly here - that's a separate test
    assert type(con1.schema_.items._target) == openapi_version.schema

    resp2 = op.responses["default"]
    assert resp2.description == "unexpected error"
    assert len(resp2.content) == 1
    assert "application/json" in resp2.content
    con2 = resp2.content["application/json"]
    assert con2.schema_ is not None
    # again, test ref resolution elsewhere
    assert type(con2.schema_._target) == openapi_version.schema


def test_paths_security(httpx_mock, with_paths_security):
    api = OpenAPI(URLBASE, with_paths_security, session_factory=httpx.Client, use_operation_tags=False)
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")

    auth = str(uuid.uuid4())

    for i in api.paths.values():
        if not i.post or not i.post.security:
            continue
        s = i.post.security[0]
        #        assert type(s.name) == str
        #        assert type(s.types) == list
        break
    else:
        assert False

    with pytest.raises(ValueError, match=r"does not accept security schemes \['xAuth'\]"):
        api.authenticate(xAuth=auth)
        api._.api_v1_auth_login_info(data={}, parameters={})

    # global security
    api.authenticate(None, cookieAuth=auth)
    api._.api_v1_auth_login_info(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]

    # path
    api.authenticate(None, tokenAuth=auth)
    api._.api_v1_auth_login_create(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert request.headers["Authorization"] == auth

    api.authenticate(None, paramAuth=auth)
    api._.api_v1_auth_login_create(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert yarl.URL(str(request.url)).query["auth"] == auth

    api.authenticate(None, cookieAuth=auth)
    api._.api_v1_auth_login_create(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert request.headers["Cookie"] == "Session=%s" % (auth,)

    api.authenticate(None, basicAuth=(auth, auth))
    api._.api_v1_auth_login_create(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert request.headers["Authorization"].split(" ")[1] == base64.b64encode((auth + ":" + auth).encode()).decode()

    api.authenticate(None, digestAuth=(auth, auth))
    api._.api_v1_auth_login_create(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    # can't test?

    api.authenticate(None, bearerAuth=auth)
    api._.api_v1_auth_login_create(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert request.headers["Authorization"] == "Bearer %s" % (auth,)

    # null session
    api.authenticate(None)
    api._.api_v1_auth_login_info(data={}, parameters={})


def test_paths_security_combined(httpx_mock, with_paths_security):
    api = OpenAPI(URLBASE, with_paths_security, session_factory=httpx.Client, use_operation_tags=False)
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")

    auth = str(uuid.uuid4())

    # combined
    api.authenticate(user="test")
    with pytest.raises(ValueError, match="No security requirement satisfied"):
        r = api._.api_v1_auth_login_combined(data={}, parameters={})

    api.authenticate(**{"user": "theuser", "token": "thetoken"})
    r = api._.api_v1_auth_login_combined(data={}, parameters={})

    api.authenticate(None)
    with pytest.raises(ValueError, match="No security requirement satisfied"):
        r = api._.api_v1_auth_login_combined(data={}, parameters={})


def test_paths_parameters(httpx_mock, with_paths_parameters):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")
    api = OpenAPI(URLBASE, with_paths_parameters, session_factory=httpx.Client)

    with pytest.raises(
        ValueError, match=r"Required Parameter \['Cookie', 'Header', 'Path', 'Query'\] missing \(provided \[\]\)"
    ):
        api._.getTest(data={}, parameters={})

    Header = [i**i for i in range(3)]
    api._.getTest(data={}, parameters={"Cookie": "Cookie", "Path": "Path", "Header": Header, "Query": "Query"})
    request = httpx_mock.get_requests()[-1]

    assert request.headers["Header"] == ",".join(map(str, Header))
    assert request.headers["Cookie"] == "Cookie=Cookie"
    assert pathlib.Path(request.url.path).name == "Path"
    assert yarl.URL(str(request.url)).query["Query"] == "Query"

    with pytest.raises(
        ValueError, match=r"Parameter \['Invalid'\] unknown \(accepted \['Cookie', 'Header', 'Path', 'Query'\]\)"
    ):
        api._.getTest(
            data={},
            parameters={"Cookie": "Cookie", "Path": "Path", "Header": Header, "Query": "Query", "Invalid": "yes"},
        )


def test_paths_parameters_invalid(with_paths_parameters_invalid):
    with pytest.raises(OperationParameterValidationError, match=r"Parameter names are invalid: \[\'\', \'Path:\'\]"):
        OpenAPI(URLBASE, with_paths_parameters_invalid, session_factory=httpx.Client)


def test_paths_parameter_missing(with_paths_parameter_missing):
    with pytest.raises(OperationParameterValidationError, match="Parameter name not found in parameters: missing"):
        OpenAPI(URLBASE, with_paths_parameter_missing, session_factory=httpx.Client)


def test_paths_parameter_default(httpx_mock, with_paths_parameter_default):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")
    api = OpenAPI(URLBASE, with_paths_parameter_default, session_factory=httpx.Client)
    api._.default()
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.parts[2] == "op"
    assert u.parts[3] == "path"


def test_paths_parameter_format(httpx_mock, with_paths_parameter_format):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")
    api = OpenAPI(URLBASE, with_paths_parameter_format, session_factory=httpx.Client)

    # using values from
    # https://spec.openapis.org/oas/v3.1.0#style-examples
    parameters = {
        "array": ["blue", "black", "brown"],
        "string": "blue",
        "empty": None,
        "object": {"R": 100, "G": 200, "B": 150},
    }
    ne = parameters.copy()
    del ne["empty"]
    r = api._.FormQuery(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.query["string"] == "blue"
    assert u.query["array"] == ",".join(parameters["array"])
    assert u.query["object"] == "R,100,G,200,B,150"
    assert u.query["empty"] == ""

    r = api._.FormExplodeQuery(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.query["string"] == "blue"
    assert u.query.getall("array") == parameters["array"]
    assert u.query["R"] == "100" and u.query["G"] == "200" and u.query["B"] == "150"

    r = api._.LabelPath(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.parts[4] == ".blue"
    assert u.parts[5] == ".blue.black.brown"
    assert u.parts[6] == ".R.100.G.200.B.150"
    assert u.parts[7] == ""  # . is scrubbed as path self

    r = api._.LabelExplodePath(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.parts[4] == ".blue"
    assert u.parts[5] == ".blue.black.brown"
    assert u.parts[6] == ".R=100.G=200.B=150"
    assert u.parts[7] == ""

    r = api._.deepObjectExplodeQuery(parameters={"object": parameters["object"]})
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.query["object[R]"] == "100" and u.query["object[G]"] == "200" and u.query["object[B]"] == "150"

    r = api._.DelimitedQuery(parameters={"pipe": ["a", "b"], "space": ["1", "2"], "object": parameters["object"]})
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.query["pipe"] == "a|b"
    assert u.query["space"] == "1 2"
    assert u.query["object"] == "R 100 G 200 B 150"

    r = api._.matrixPath(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))

    assert u.parts[4] == ";string=blue"
    assert u.parts[5] == ";array=blue,black,brown"
    assert u.parts[6] == ";object=R,100,G,200,B,150"
    assert u.parts[7] == ";empty"

    r = api._.simpleHeader(parameters=ne)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))

    assert request.headers.get("string") == "blue"
    assert request.headers.get("array") == "blue,black,brown"
    assert request.headers.get("object") == "R,100,G,200,B,150"

    r = api._.simpleExplodePath(parameters=ne)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))

    assert u.parts[5] == "blue"
    assert u.parts[6] == "blue,black,brown"
    assert u.parts[7] == "R=100,G=200,B=150"

    return


def test_paths_response_header(httpx_mock, with_paths_response_header):
    httpx_mock.add_response(
        headers={"Content-Type": "application/json", "X-required": "1", "X-optional": "1,2,3"}, content=b"[]"
    )

    api = OpenAPI(URLBASE, with_paths_response_header, session_factory=httpx.Client)
    h, b = api._.get(return_headers=True)
    request = httpx_mock.get_requests()[-1]

    assert isinstance(h["X-required"], str)
    o = h["X-optional"]
    assert isinstance(o, list) and len(o) == 3 and isinstance(o[0], str) and o[-1] == "3"

    with pytest.raises(ValueError, match=r"missing Header \['x-required'\]"):
        httpx_mock.add_response(headers={"Content-Type": "application/json", "X-optional": "1,2,3"}, content=b"[]")
        h, b = api._.get(return_headers=True)

    httpx_mock.add_response(headers={"Content-Type": "application/json", "X-object": "A,1,B,2,C,3"}, content=b"[]")
    h, b = api._.types(return_headers=True)
    assert h["X-object"].A == 1
    assert h["X-object"].B == "2"
    return


def test_paths_tags(httpx_mock, with_paths_tags):
    import copy

    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")
    api = OpenAPI(URLBASE, with_paths_tags, session_factory=httpx.Client, use_operation_tags=True)
    b = api._.users.list()
    r = frozenset(api._)
    assert frozenset(["items.list", "objects.list", "users.list"]) == r

    from aiopenapi3.errors import SpecError

    with pytest.raises(SpecError, match=f"Duplicate operationId list"):
        OpenAPI(URLBASE, with_paths_tags, session_factory=httpx.Client, use_operation_tags=False)

    spec = copy.deepcopy(with_paths_tags)
    for k in {"/user/", "/item/"}:
        spec["paths"][k]["get"]["operationId"] = f"list{k[1:-1]}"

    api = OpenAPI(URLBASE, spec, session_factory=httpx.Client, use_operation_tags=False)
    api._.listuser()
    r = frozenset(api._)
    assert frozenset(["listuser", "listitem"]) == r
