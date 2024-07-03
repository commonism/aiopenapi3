from aiopenapi3 import OpenAPI
from aiopenapi3 import ResponseSchemaError, ContentTypeError, HTTPStatusError, ResponseDecodingError, RequestError

import httpx


import pytest


def test_response_error(httpx_mock, with_paths_response_error):
    api = OpenAPI("/", with_paths_response_error, session_factory=httpx.Client)

    httpx_mock.add_response(headers={"Content-Type": "application/json"}, status_code=200, json="ok")
    r = api._.test()
    assert r == "ok"

    httpx_mock.add_response(headers={"Content-Type": "text/html"}, status_code=200, json="ok")
    with pytest.raises(ContentTypeError) as e:
        api._.test()
    str(e.value)

    httpx_mock.add_response(headers={"Content-Type": "application/json"}, status_code=201, json="ok")
    with pytest.raises(HTTPStatusError):
        api._.test()
    str(e.value)

    httpx_mock.add_response(headers={"Content-Type": "application/json"}, status_code=200, content="'")
    with pytest.raises(ResponseDecodingError) as e:
        api._.test()
    str(e.value)

    httpx_mock.add_response(headers={"Content-Type": "application/json"}, status_code=200, json="fail")
    with pytest.raises(ResponseSchemaError) as e:
        api._.test()
    str(e.value)


def test_request_error(with_paths_response_error):
    class Client(httpx.Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, transport=RaisingTransport(), **kwargs)

    class RaisingTransport(httpx.BaseTransport):
        def handle_request(self, request):
            raise httpx.TimeoutException(message="timeout")

    api = OpenAPI("/", with_paths_response_error, session_factory=Client)

    with pytest.raises(RequestError) as e:
        api._.test()
    str(e.value)
