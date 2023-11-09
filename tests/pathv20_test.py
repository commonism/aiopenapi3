import io
import uuid
import urllib

import yarl
import httpx
import pytest

from aiopenapi3 import OpenAPI

URLBASE = "/"


def test_paths_security_v20_parse(with_paths_security_v20):
    api = OpenAPI(URLBASE, with_paths_security_v20)


def test_paths_security_v20_url(with_paths_security_v20):
    api = OpenAPI(URLBASE, with_paths_security_v20)
    assert str(api.url) == "https://api.example.com/v1"


def test_paths_security_v20_securityparameters(httpx_mock, with_paths_security_v20):
    api = OpenAPI(URLBASE, with_paths_security_v20, session_factory=httpx.Client)
    user = api._.createUser.return_value().get_type().model_construct(name="test", id=1)
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json=user.model_dump())

    auth = str(uuid.uuid4())

    with pytest.raises(ValueError, match=r"does not accept security schemes \['xAuth'\]"):
        api.authenticate(xAuth=auth)
        api._.createUser(data=user, parameters={})

    # global security
    api.authenticate(None, BasicAuth=(auth, auth))
    api._.getUser(data={}, parameters={"userId": 1})
    request = httpx_mock.get_requests()[-1]

    # path
    api.authenticate(None, QueryAuth=auth)
    api._.createUser(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert request.url.params["auth"] == auth

    # header
    api.authenticate(None, HeaderAuth="Bearer %s" % (auth,))
    api._.createUser(data={}, parameters={})
    request = httpx_mock.get_requests()[-1]
    assert request.headers["Authorization"] == "Bearer %s" % (auth,)

    # null session
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json=[user.model_dump()])
    api.authenticate(None)
    api._.listUsers(data={}, parameters={})


def test_paths_security_v20_combined_securityparameters(httpx_mock, with_paths_security_v20):
    api = OpenAPI(URLBASE, with_paths_security_v20, session_factory=httpx.Client)
    user = api._.createUser.return_value().get_type().model_construct(name="test", id=1)
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json="combined")

    api.authenticate(user="u")
    with pytest.raises(ValueError, match="No security requirement satisfied"):
        api._.combinedSecurity(data={}, parameters={})

    api.authenticate(**{"user": "u", "token": "t"})
    api._.combinedSecurity(data={}, parameters={})

    api.authenticate(None)
    with pytest.raises(ValueError, match=r"No security requirement provided \(accepts {token and user}\)"):
        api._.combinedSecurity(data={}, parameters={})


def test_paths_security_v20_alternate_securityparameters(httpx_mock, with_paths_security_v20):
    api = OpenAPI(URLBASE, with_paths_security_v20, session_factory=httpx.Client)
    user = api._.createUser.return_value().get_type().model_construct(name="test", id=1)
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json="alternate")

    api.authenticate(user="u")
    with pytest.raises(
        ValueError, match=r"No security requirement satisfied \(accepts {BasicAuth} or {token and user} given {user}\)"
    ):
        api._.alternateSecurity(data={}, parameters={})

    api.authenticate(**{"user": "u", "token": "t"})
    api._.alternateSecurity(data={}, parameters={})

    api.authenticate(None)
    with pytest.raises(
        ValueError, match=r"No security requirement provided \(accepts {BasicAuth} or {token and user}\)"
    ):
        api._.alternateSecurity(data={}, parameters={})


def test_paths_security_v20_post_body(httpx_mock, with_paths_security_v20):
    auth = str(uuid.uuid4())
    api = OpenAPI(URLBASE, with_paths_security_v20, session_factory=httpx.Client)
    user = api._.createUser.return_value().get_type().model_construct(name="test", id=1)
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json=user.model_dump())

    api.authenticate(HeaderAuth="Bearer %s" % (auth,))
    with pytest.raises(ValueError, match="Request Body is required but none was provided."):
        api._.createUser(data=None, parameters={})
    api._.createUser(data={}, parameters={})
    api._.createUser(data=user, parameters={})


def test_paths_security_v20_parameters(httpx_mock, with_paths_security_v20):
    api = OpenAPI(URLBASE, with_paths_security_v20, session_factory=httpx.Client)
    user = api._.createUser.return_value().get_type().model_construct(name="test", id=1)

    auth = str(uuid.uuid4())
    api.authenticate(BasicAuth=(auth, auth))

    with pytest.raises(ValueError, match=r"Required Parameter \['userId'\] missing \(provided \[\]\)"):
        api._.getUser(data={}, parameters={})

    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json=[user.model_dump()])
    api.authenticate(None)
    api._.listUsers(data={}, parameters={"inQuery": "Q", "inHeader": "H"})

    request = httpx_mock.get_requests()[-1]
    assert request.headers["inHeader"] == "H"
    assert yarl.URL(str(request.url)).query["inQuery"] == "Q"


def test_paths_response_header_v20(httpx_mock, with_paths_response_header_v20):
    httpx_mock.add_response(
        headers={"Content-Type": "application/json", "X-required": "1", "X-optional": "1,2,3"}, json="get"
    )
    api = OpenAPI(URLBASE, with_paths_response_header_v20, session_factory=httpx.Client)
    h, b = api._.get(return_headers=True)
    request = httpx_mock.get_requests()[-1]

    assert isinstance(h["X-required"], str)
    o = h["X-optional"]
    assert isinstance(o, list) and len(o) == 3 and isinstance(o[0], str) and o[-1] == "3"

    # seems like there is no notion of required headers in swagger
    # with pytest.raises(ValueError, match=r"missing Header \['x-required'\]"):
    #     httpx_mock.add_response(
    #         headers={"Content-Type": "application/json", "X-optional": "2"}, content=b"[]"
    #     )
    #     h, b = api._.get(return_headers=True)
    #     request = httpx_mock.get_requests()[-1]

    return


def test_paths_parameter_format_v20(httpx_mock, with_paths_parameter_format_v20):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json="ok")
    api = OpenAPI(URLBASE, with_paths_parameter_format_v20, session_factory=httpx.Client)

    parameters = {
        "array": ["blue", "black", "brown"],
        "string": "blue",
    }
    r = api._.path(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.parts[4] == "blue|black|brown"
    assert u.parts[5] == "default"

    r = api._.query(parameters=parameters)
    request = httpx_mock.get_requests()[-1]
    u = yarl.URL(str(request.url))
    assert u.query["default"] == "default"
    assert u.query["string"] == "blue"
    assert u.query["array"] == "blue\tblack\tbrown"

    params = {x.name: "" for x in api._.formdata.operation.parameters}
    params["file0"] = ("file0name", io.BytesIO(b"x"), "ct")
    params["file1"] = ("file1name", io.BytesIO(b"y"), "ct")
    result = api._.formdata(parameters=params)
    request = httpx_mock.get_requests()[-1]
    assert (
        (f := request.stream.fields[0]) is not None
        and f.filename == "file0name"
        and f.headers["Content-Type"] == "ct"
        and f.file.read() == b"x"
    )
    assert (
        (f := request.stream.fields[1]) is not None
        and f.filename == "file1name"
        and f.headers["Content-Type"] == "ct"
        and f.file.read() == b"y"
    )
    assert result == "ok"

    params = dict(A="a", B=5)
    result = api._.urlencoded(parameters=params)
    request = httpx_mock.get_requests()[-1]
    assert (v := urllib.parse.parse_qs(request.content.decode())) is not None and v["A"] == ["a"] and v["B"] == ["5"]
    assert result == "ok"

    return


def test_paths_stream(httpx_mock, with_paths_parameter_format_v20):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json="ok")
    api = OpenAPI(URLBASE, with_paths_parameter_format_v20, session_factory=httpx.Client)

    parameters = {
        "array": ["blue", "black", "brown"],
        "string": "blue",
    }
    req = api.createRequest("path")
    streamresponse = req.stream(parameters=parameters)
    for i in streamresponse.result.iter_bytes():
        continue
    streamresponse.session.close()
