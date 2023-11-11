import asyncio
import uuid
import sys

import pytest
import pytest_asyncio

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config

import aiopenapi3

# pytest.skip(allow_module_level=True)

from api.main import app


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
    api = await asyncio.to_thread(aiopenapi3.OpenAPI.load_sync, f"http://{server.bind[0]}/v1/openapi.json")
    return api


def randomPet(name=None):
    return {"data": {"pet": {"name": str(name or uuid.uuid4()), "pet_type": "dog"}}, "return_headers": True}


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_createPet(event_loop, server, client):
    h, r = await asyncio.to_thread(client._.createPet, **randomPet())
    assert type(r).model_json_schema() == client.components.schemas["Pet"].get_type().model_json_schema()
    assert h["X-Limit-Remain"] == 5

    r = await asyncio.to_thread(client._.createPet, data={"pet": {"name": r.name}})
    assert type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_listPet(event_loop, server, client):
    h, r = await asyncio.to_thread(client._.createPet, **randomPet(uuid.uuid4()))
    l = await asyncio.to_thread(client._.listPet)
    assert len(l) > 0


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_getPet(event_loop, server, client):
    h, pet = await asyncio.to_thread(client._.createPet, **randomPet(uuid.uuid4()))
    r = await asyncio.to_thread(client._.getPet, parameters={"petId": pet.id})
    # FastAPI 0.101 Serialization changes
    # assert type(r).model_json_schema() == type(pet).model_json_schema()
    assert r.id == pet.id

    r = await asyncio.to_thread(client._.getPet, parameters={"petId": -1})
    assert type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_deletePet(event_loop, server, client):
    r = await asyncio.to_thread(client._.deletePet, parameters={"petId": -1})
    print(r)
    assert type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()

    await asyncio.to_thread(client._.createPet, **randomPet(uuid.uuid4()))
    zoo = await asyncio.to_thread(client._.listPet)
    for pet in zoo:
        await asyncio.to_thread(client._.deletePet, parameters={"petId": pet.id})
