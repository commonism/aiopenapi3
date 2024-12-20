import asyncio
import uuid

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


@pytest_asyncio.fixture(loop_scope="session")
async def server(config):
    event_loop = asyncio.get_running_loop()
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
    api = await asyncio.to_thread(aiopenapi3.OpenAPI.load_sync, f"http://{server.bind[0]}/v1/openapi.json")
    return api


def randomPet(name=None):
    return {"data": {"pet": {"name": str(name or uuid.uuid4()), "pet_type": "dog"}}, "return_headers": True}


@pytest.mark.asyncio(loop_scope="session")
async def test_createPet(server, client):
    h, r = await asyncio.to_thread(client._.createPet, **randomPet())
    assert type(r).model_json_schema() == client.components.schemas["Pet"].get_type().model_json_schema()
    assert h["X-Limit-Remain"] == 5

    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await asyncio.to_thread(client._.createPet, data={"pet": {"name": r.name}})
    assert type(e.value.data).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()


@pytest.mark.asyncio(loop_scope="session")
async def test_listPet(server, client):
    h, r = await asyncio.to_thread(client._.createPet, **randomPet(uuid.uuid4()))
    l = await asyncio.to_thread(client._.listPet)
    assert len(l) > 0


@pytest.mark.asyncio(loop_scope="session")
async def test_getPet(server, client):
    h, pet = await asyncio.to_thread(client._.createPet, **randomPet(uuid.uuid4()))
    r = await asyncio.to_thread(client._.getPet, parameters={"petId": pet.id})
    # FastAPI 0.101 Serialization changes
    # assert type(r).model_json_schema() == type(pet).model_json_schema()
    assert r.id == pet.id

    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await asyncio.to_thread(client._.getPet, parameters={"petId": -1})

    assert type(e.value.data).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()


@pytest.mark.asyncio(loop_scope="session")
async def test_deletePet(server, client):
    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await asyncio.to_thread(client._.deletePet, parameters={"petId": -1})

    assert type(e.value.data).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()

    await asyncio.to_thread(client._.createPet, **randomPet(uuid.uuid4()))
    zoo = await asyncio.to_thread(client._.listPet)
    for pet in zoo:
        await asyncio.to_thread(client._.deletePet, parameters={"petId": pet.id})
