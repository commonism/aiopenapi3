import asyncio

from collections.abc import AsyncIterable


from hypercorn.asyncio import serve
from hypercorn.config import Config
import pydantic
from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

import pytest
import pytest_asyncio


import aiopenapi3

app = FastAPI(
    version="1.0.0",
    title="Sequential Streaming tests",
    servers=[{"url": "/", "description": "Default, relative server"}],
)


def openapi32():
    """
    https://github.com/fastapi/fastapi/discussions/15328#discussioncomment-16543627
    """
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        openapi_version="3.2.0", title=app.title, version=app.version, routes=app.routes, servers=app.servers
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = openapi32


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest_asyncio.fixture(loop_scope="session")
async def server(config):
    event_loop = asyncio.get_event_loop()
    try:
        sd = asyncio.Event()
        task = event_loop.create_task(serve(app, config, shutdown_trigger=sd.wait))
        yield config
    finally:
        sd.set()
        await task


@pytest_asyncio.fixture(loop_scope="session")
async def client(server):
    api = await aiopenapi3.OpenAPI.load_async(f"http://{server.bind[0]}/openapi.json")
    return api


class Item(pydantic.BaseModel):
    name: str
    description: str | None


items = [
    Item(name="Plumbus", description="A multi-purpose household device."),
    Item(name="Portal Gun", description="A portal opening device."),
    Item(name="Meeseeks Box", description="A box that summons a Meeseeks."),
]


@app.get("/jsonl", operation_id="jsonl")
async def jsonl() -> AsyncIterable[Item]:
    """
    https://fastapi.tiangolo.com/tutorial/stream-json-lines/#use-cases
    """
    for item in items:
        yield item


@app.get("/sse", operation_id="sse", response_class=EventSourceResponse)
async def sse() -> AsyncIterable[ServerSentEvent]:
    for idx, item in enumerate(items):
        yield ServerSentEvent(comment=str(idx), data=item)


@pytest.mark.asyncio(loop_scope="session")
async def test_jsonl(server, client):
    req = client.createRequest("jsonl")
    async with req.sequence() as sequence:
        async for obj in sequence:
            print(obj)


@pytest.mark.asyncio(loop_scope="session")
async def test_sse(server, client):
    from aiopenapi3.request import AsyncRequestBase

    req: AsyncRequestBase
    req = client.createRequest("sse")
    async with req.sequence() as sequence:
        async for obj in sequence:
            print(obj)
    await asyncio.sleep(1.1)
