import httpx2
import pytest

from aiopenapi3 import (
    ContentTypeError,
    HTTPStatusError,
    OpenAPI,
    RequestError,
    ResponseDecodingError,
    ResponseSchemaError,
)


def test_response_error(httpx2_mock, with_paths_response_error_vXX):
    api = OpenAPI("/", with_paths_response_error_vXX, session_factory=httpx2.Client)

    httpx2_mock.add_response(headers={"Content-Type": "application/json"}, status_code=200, json="ok")
    r = api._.test()
    assert r == "ok"

    httpx2_mock.add_response(headers={"Content-Type": "text/html"}, status_code=200, json="ok")
    with pytest.raises(ContentTypeError) as e:
        api._.test()
    str(e.value)

    httpx2_mock.add_response(headers={"Content-Type": "application/json"}, status_code=201, json="ok")
    with pytest.raises(HTTPStatusError) as e:
        api._.test()
    str(e.value)

    httpx2_mock.add_response(headers={"Content-Type": "application/json"}, status_code=200, content="'")
    with pytest.raises(ResponseDecodingError) as e:
        api._.test()
    str(e.value)

    httpx2_mock.add_response(headers={"Content-Type": "application/json"}, status_code=200, json="fail")
    with pytest.raises(ResponseSchemaError) as e:
        api._.test()
    str(e.value)


def test_request_error(with_paths_response_error_vXX):
    class Client(httpx2.Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, transport=RaisingTransport(), **kwargs)

    class RaisingTransport(httpx2.BaseTransport):
        def handle_request(self, request):
            raise httpx2.TimeoutException(message="timeout")

    api = OpenAPI("/", with_paths_response_error_vXX, session_factory=Client)

    with pytest.raises(RequestError) as e:
        api._.test()
    str(e.value)
