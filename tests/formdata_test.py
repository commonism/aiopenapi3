from pathlib import Path
import httpx

from aiopenapi3 import OpenAPI
from aiopenapi3.v30.formdata import encode_multipart_parameters


def test_encode_formdata():
    with Path("/dev/urandom").open("rb") as f:
        data = f.read(512)

    from aiopenapi3.v30 import Schema

    schema = Schema()
    ITEMS = [
        ("text", "text/plain", "bar", dict(), schema),
        ("text", "text/plain", "bar", {"X-HEAD": "text"}, schema),
        ("audio", "audio/wav", b"jd", dict(), schema),
        ("image", "image/png", b"jd", dict(), schema),
        ("data", "application/octet-stream", data, dict(), schema),
        ("rbh", "application/octet-stream", data, {"X-HEAD": "rbh"}, schema),
    ]

    for i in ITEMS:
        m = encode_multipart_parameters([i])
        ct = m["Content-Type"]
        data = m.as_string()
        assert data

    m = encode_multipart_parameters(ITEMS)
    data = m.as_string()
    assert data


def test_formdata_encoding(httpx_mock, with_paths_requestbody_formdata_encoding):
    api = OpenAPI("http://localhost/api", with_paths_requestbody_formdata_encoding, session_factory=httpx.Client)

    httpx_mock.add_response(
        headers={"Content-Type": "application/json"},
        json="ok",
    )

    cls = api._.encoding.operation.requestBody.content["multipart/form-data"].schema_.get_type()
    data = cls(
        id="3b26b56a-b58a-4855-b26d-0c1ca5c4d071",
        address={"state": "ny"},
        # historyMetadata={"a": "a"},
        profileImage=b"\x00\01\0x2",
    )
    result = api._.encoding(data=data)
    request = httpx_mock.get_request()

    import email

    content = request.content.decode()

    msg = email.message_from_string(
        f"""\
MIME-Version: 1.0
Content-Type: {request.headers["content-type"]}

{content}

"""
    )
    assert msg.defects == [] and msg.is_multipart()

    r = dict()
    for p in msg.get_payload():
        name = p.get_param("name", header="content-disposition")
        payload = p.get_payload(decode=True)
        r[name] = payload

    assert r["address"] == b"state,ny"
    assert r["id"] == str(data.id).encode()
    assert r["profileImage"] == data.profileImage.encode()
    assert result == "ok"


def _test_speed():
    import timeit

    value = "text/plain; a=b"
    a = timeit.timeit(
        f"decode_content_type('{value}')",
        number=1000000,
        setup="from aiopenapi3.v30.formdata import decode_content_type",
    )
    print(f"{a}")
