import asyncio
import random

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config
from fastapi import FastAPI, Request, Response, Query
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


@pytest.fixture(scope="session")
def event_loop_policy():
    return uvloop.EventLoopPolicy()


@pytest_asyncio.fixture(loop_scope="session")
async def client(server):
    api = await aiopenapi3.OpenAPI.load_async(f"http://{server.bind[0]}/openapi.json")

    return api


@app.get("/content_length", operation_id="content_length", response_class=PlainTextResponse)
def content_length(request: Request, response: Response, content_length: int = Query()):
    return PlainTextResponse(content=b" " * content_length)


@pytest.mark.asyncio(loop_scope="session")
async def test_content_length_exceeded(server, client):
    cl = random.randint(1, client._max_response_content_length)
    r = await client._.content_length(parameters=dict(content_length=cl))
    assert len(r) == cl

    cl = client._max_response_content_length
    r = await client._.content_length(parameters=dict(content_length=cl))
    assert len(r) == cl

    with pytest.raises(aiopenapi3.errors.ContentLengthExceededError):
        cl = client._max_response_content_length + 1
        await client._.content_length(parameters=dict(content_length=cl))


@pytest.mark.asyncio(loop_scope="session")
async def test_sync_content_length_exceeded(server):
    client = await asyncio.to_thread(
        aiopenapi3.OpenAPI.load_sync,
        f"http://{server.bind[0]}/openapi.json",
    )

    cl = random.randint(1, client._max_response_content_length)
    r = await asyncio.to_thread(client._.content_length, parameters=dict(content_length=cl))
    assert len(r) == cl

    cl = client._max_response_content_length
    r = await asyncio.to_thread(client._.content_length, parameters=dict(content_length=cl))
    assert len(r) == cl

    with pytest.raises(aiopenapi3.errors.ContentLengthExceededError):
        cl = client._max_response_content_length + 1
        await asyncio.to_thread(client._.content_length, parameters=dict(content_length=cl))
