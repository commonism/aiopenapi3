from pathlib import Path
import httpx

from aiopenapi3 import OpenAPI
from aiopenapi3.v30.formdata import encode_multipart_parameters


def _test_encode_formdata(with_paths_requestbody_formdata_encoding):
    with Path("/dev/urandom").open("rb") as f:
        data = f.read(512)

    from aiopenapi3.v30 import Schema

    schema = Schema()
    ITEMS = [
        ("text", "text/plain", "bar", dict()),
        ("text", "text/plain", "bar", {"X-HEAD": "text"}),
        ("audio", "audio/wav", b"jd", dict()),
        ("image", "image/png", b"jd", dict()),
        ("data", "application/octet-stream", data, dict()),
        ("rbh", "application/octet-stream", data, {"X-HEAD": "rbh"}),
    ]

    for i in ITEMS:
        m = encode_multipart_parameters([(*i, schema)])
        ct = m["Content-Type"]
        data = m.as_string()

    m = encode_multipart_parameters(ITEMS)
    data = m.as_string()
    return


def test_formdata_encoding(httpx_mock, with_paths_requestbody_formdata_encoding):
    api = OpenAPI("http://localhost/api", with_paths_requestbody_formdata_encoding, session_factory=httpx.Client)

    httpx_mock.add_response(
        headers={"Content-Type": "application/json"},
        json="ok",
    )

    cls = api._.encoding.operation.requestBody.content["multipart/form-data"].schema_.get_type()
    data = cls(
        id="3b26b56a-b58a-4855-b26d-0c1ca5c4d071",
        #        address={"1": 1},
        #        historyMetadata={"a": "a"},
        #        profileImage=b"\x00\01\0x2",
    )
    result = api._.encoding(data=data)
    request = httpx_mock.get_request()

    assert result == "ok"


def _test_speed():
    value = "text/plain; a=b"
    a = timeit.timeit(
        f"decode_content_type('{value}')", number=1000000, setup="from aiopenapi3.formdata import decode_content_type"
    )
    b = timeit.timeit(
        f"_decode_content_type('{value}')", number=1000000, setup="from aiopenapi3.formdata import _decode_content_type"
    )
    print(f"{a} {b}")
