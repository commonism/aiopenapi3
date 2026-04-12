import httpx

import pytest
from pytest_httpx import IteratorStream

from aiopenapi3 import OpenAPI
from aiopenapi3 import v32


def test_Components():
    # mediaTypes
    pass


def test_Example():
    # dataValue
    # serializedValue
    pass


def test_Encoding():
    # encoding
    # prefixEncoding
    # itemEncoding
    pass


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
@pytest.mark.asyncio(loop_scope="session")
async def test_MediaType(httpx_mock, with_schema_itemSchema):
    # itemSchema
    import pydantic

    api = OpenAPI("https://example.org/api/", with_schema_itemSchema, session_factory=httpx.AsyncClient)
    LogEntry: pydantic.BaseModel = api.components.schemas["LogEntry"].get_type()

    records = with_schema_itemSchema["components"]["examples"]["LogJSONPerLine"]["value"].strip("\n").split("\n")
    t = pydantic.TypeAdapter(list[LogEntry])
    ct = t.dump_json(t.validate_python([LogEntry.model_validate_json(i) for i in records * 16]))

    httpx_mock.add_response(
        url="https://example.org/api/json_seq",
        headers={"Content-Type": "application/json-seq"},
        stream=IteratorStream([b"\x1e" + i.encode() + b"\n" for i in (records * 16)]),
    )
    httpx_mock.add_response(
        url="https://example.org/api/jsonl",
        headers={"Content-Type": "application/jsonl"},
        stream=IteratorStream([i.encode() + b"\n" for i in (records * 16)]),
    )
    httpx_mock.add_response(
        url="https://example.org/api/ndjson",
        headers={"Content-Type": "application/x-ndjson"},
        stream=IteratorStream([i.encode() + b"\n" for i in (records * 16)]),
    )
    httpx_mock.add_response(
        url="https://example.org/api/text_events", headers={"Content-Type": "text/event-stream"}, content=ct
    )

    import aiopenapi3.v30

    req: aiopenapi3.v30.glue.AsyncRequest
    req = api.createRequest("json_seq")
    async with req.sequence() as sequence:
        async for obj in sequence:
            print(obj)

    req = api.createRequest("jsonl")
    async with req.sequence() as sequence:
        async for obj in sequence:
            print(obj)

    req = api.createRequest("ndjson")
    async with req.sequence() as sequence:
        async for obj in sequence:
            print(obj)

    req = api.createRequest("text_events")
    async with req.sequence() as sequence:
        async for obj in sequence:
            print(obj)

    # prefixEncoding
    # itemEncoding
    pass


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_MediaType_itemSchema_sync(httpx_mock, with_schema_itemSchema):
    # itemSchema
    import pydantic

    api = OpenAPI("https://example.org/api/", with_schema_itemSchema, session_factory=httpx.Client)
    LogEntry: pydantic.BaseModel = api.components.schemas["LogEntry"].get_type()

    records = with_schema_itemSchema["components"]["examples"]["LogJSONPerLine"]["value"].strip("\n").split("\n")
    t = pydantic.TypeAdapter(list[LogEntry])
    ct = t.dump_json(t.validate_python([LogEntry.model_validate_json(i) for i in records * 16]))

    httpx_mock.add_response(
        url="https://example.org/api/json_seq",
        headers={"Content-Type": "application/json-seq"},
        stream=IteratorStream([b"\x1e" + i.encode() + b"\n" for i in (records * 16)]),
    )

    req = api.createRequest("json_seq")
    with req.sequence() as sequence:
        print(sequence.headers)
        for obj in sequence:
            print(obj)


def test_Response():
    # description
    # summary
    pass


def test_PathItem_query(with_path_query):
    api = OpenAPI("https://example.org/api/", with_path_query)


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_PathItem_additionalOperations(httpx_mock, with_path_additionalOperations):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json="ok")

    api = OpenAPI("https://example.org/api/", with_path_additionalOperations, session_factory=httpx.Client)
    assert api._.test() == "ok"

    request: httpx.Request = httpx_mock.get_requests()[-1]
    assert request.method == "TEST" and request.url.path == "/api/data"

    assert api._[("/api/data", "test")]() == "ok"
    request = httpx_mock.get_requests()[-1]
    assert request.method == "TEST" and request.url.path == "/api/data"


def test_Callback_RuntimeExpression():
    pass


def test_Root(with_schema_v32):
    api = OpenAPI("https://example.org/api/", with_schema_v32)
    # $self

    v = api.resolve_jr(api._root, None, v32.Reference(**{"$ref": "http://example.org#/components/schemas/String"}))
    assert v is not None

    # For API URLs the $self field, which identifies the OpenAPI document, is ignored and the retrieval URI is used instead.
    assert str(api.url) == "https://example.org/api/v32"

    # https://spec.openapis.org/oas/v3.2.0.html#base-uri-within-content


def test_Discriminator_defaultMapping():
    # c.f. https://github.com/pydantic/pydantic/issues/11188
    pass


def test_Server_name():
    pass


def test_Tag(httpx_mock, with_schema_tags_v32):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, status_code=204)
    api = OpenAPI("https://example.org/api/", with_schema_tags_v32, session_factory=httpx.Client)
    api._.external.partner.x()

    assert sorted(filter(lambda x: x.partition(".")[0] == "external", api._.Iter(api, True))) == ["external.partner.x"]
