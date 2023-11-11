import asyncio
import random
import sys
import string

if sys.version_info >= (3, 9):
    from typing import List, Annotated
else:
    from typing import List
    from typing_extensions import Annotated

from pathlib import Path

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config
import pydantic
from fastapi import FastAPI, Request, Response, Query, UploadFile, Body
from fastapi.responses import PlainTextResponse

import pytest
import pytest_asyncio


import aiopenapi3


app = FastAPI(version="1.0.0", title="TLS tests", servers=[{"url": "/", "description": "Default, relative server"}])


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest_asyncio.fixture(scope="session")
async def server(event_loop, config):
    policy = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    try:
        sd = asyncio.Event()
        task = event_loop.create_task(serve(app, config, shutdown_trigger=sd.wait))
        yield config
    finally:
        sd.set()
        await task
    asyncio.set_event_loop_policy(policy)


@pytest_asyncio.fixture(scope="session")
async def client(event_loop, server):
    api = await aiopenapi3.OpenAPI.load_async(f"http://{server.bind[0]}/openapi.json")
    return api


class File(pydantic.BaseModel):
    name: str = pydantic.Field(default_factory=lambda: "".join(random.choice(string.ascii_letters) for i in range(16)))
    data: pydantic.Base64Bytes


@app.get("/file", operation_id="file", response_class=PlainTextResponse)
def file(request: Request, response: Response, content_length: int = Query()):
    return PlainTextResponse(content=b" " * content_length)


@app.get("/files", operation_id="files", response_model=List[File])
def files(request: Request, response: Response, number: int = Query(), size: int = Query()):
    with Path("/dev/urandom").open("rb") as f:
        return [File(data=f.read(size)) for _ in range(number)]


@app.post("/request-streaming", operation_id="request_streaming", response_model=int)
def request_streaming(
    request: Request, response: Response, files: List[UploadFile], path: Annotated[str, Body()]
) -> int:
    r = 0
    for file in files:
        if file.filename == "a.png":
            assert file.headers["x-extra"] == "yes"

        file.file.seek(0, 2)
        offset = file.file.tell()
        r += offset

    return r + len(path)


@pytest.mark.asyncio
async def test_stream_data(event_loop, server, client):
    cl = client._max_response_content_length
    req = client.createRequest("file")
    headers, schema_, session, result = await req.stream(parameters=dict(content_length=cl))

    chunk = l = 0
    async for i in result.aiter_bytes():
        chunk += 1
        l += len(i)
    await session.aclose()
    assert chunk > 0
    assert l == cl


@pytest.mark.asyncio
async def test_request(event_loop, server, client):
    import io

    data = [
        ("files", ("a.png", io.BytesIO(b"data:a"), "image/png", {"x-extra": "yes"})),
        ("files", ("b.png", io.BytesIO(b"data:b"))),
        ("path", "media/images"),
    ]
    size = await client._.request_streaming(data=data)
    assert size == 24


@pytest.mark.asyncio
async def test_stream_array(event_loop, server, client):
    import ijson

    req = client.createRequest("files")

    headers, schema_, session, result = await req.stream(parameters=dict(number=10, size=512 * 1024))

    assert schema_ == req.operation.responses["200"].content["application/json"].schema_

    t = schema_.items.get_type()
    """
    get the type - it is .items as it is an array
    """

    @ijson.coroutine
    def cb():
        while True:
            data = yield
            try:
                file = t.model_validate(data)
            except Exception as e:
                print(e)
            assert len(file.name) == 16
            # process received File model here

    coro = ijson.items_coro(cb(), "item")

    assert result.status_code == 200
    async for i in result.aiter_bytes():
        coro.send(i)

    await session.aclose()
    coro.close()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_sync_stream(event_loop, server):
    client = await asyncio.to_thread(
        aiopenapi3.OpenAPI.load_sync,
        f"http://{server.bind[0]}/openapi.json",
    )

    cl = client._max_response_content_length

    req = client.createRequest("file")
    headers, schema_, session, result = await asyncio.to_thread(req.stream, parameters=dict(content_length=cl))

    def blocking_recv(rs):
        r = 0
        for i in rs.iter_bytes():
            r += len(i)
        return r

    l = await asyncio.to_thread(blocking_recv, result)
    assert l == cl
    await asyncio.to_thread(session.close)
