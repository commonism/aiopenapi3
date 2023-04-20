import datetime
import random
import sys
import asyncio
import uuid

import pydantic

import pytest
import pytest_asyncio

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config

from typing import ForwardRef

import typing

import aiopenapi3
from aiopenapi3 import OpenAPI
from aiopenapi3.v30.schemas import Schema

from pydantic.main import ModelMetaclass


from tests.api.main import app
from tests.api.v2.schema import Dog


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest_asyncio.fixture(scope="session")
async def server(event_loop, config):
    policy = asyncio.get_event_loop_policy()
    uvloop.install()
    try:
        sd = asyncio.Event()
        task = event_loop.create_task(serve(app, config, shutdown_trigger=sd.wait))
        yield config
    finally:
        sd.set()
        await task
    asyncio.set_event_loop_policy(policy)


@pytest.fixture(scope="session", params=[2])
def version(request):
    return f"v{request.param}"


@pytest_asyncio.fixture(scope="session")
async def client(event_loop, server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"
    api = await aiopenapi3.OpenAPI.load_async(url)
    return api


def test_Pet():
    data = Dog.schema()
    shma = Schema.model_validate(data)
    shma._identity = "Dog"
    assert shma.get_type().schema() == data


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_sync(event_loop, server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"
    api = await asyncio.to_thread(aiopenapi3.OpenAPI.load_sync, url)
    return api


@pytest.mark.asyncio
async def test_model(event_loop, server, client):
    orig = client.components.schemas["WhiteCat"].model_dump(exclude_unset=True)
    crea = client.components.schemas["WhiteCat"].get_type().schema()
    assert orig == crea

    orig = client.components.schemas["Cat"].model_dump(exclude_unset=True, by_alias=True)
    crea = (
        client.components.schemas["Cat"].get_type().schema(ref_template="#/components/schemas/{model}", by_alias=True)
    )
    if "definitions" in crea:
        del crea["definitions"]
    assert crea == orig

    orig = client.components.schemas["Pet"].model_dump(exclude_unset=True, by_alias=True)
    crea = (
        client.components.schemas["Pet"].get_type().schema(ref_template="#/components/schemas/{model}", by_alias=True)
    )
    if "definitions" in crea:
        del crea["definitions"]
    assert crea == orig


def randomPet(client, name=None):
    if name:
        return client._.createPet.data.get_type().model_construct(
            pet=client.components.schemas["Dog"]
            .get_type()
            .model_construct(name=name, age=datetime.timedelta(seconds=random.randint(1, 2**32)))
        )
    else:
        return {
            "pet": client.components.schemas["WhiteCat"]
            .model({"name": str(uuid.uuid4()), "white_name": str(uuid.uuid4())})
            .model_dump()
        }


@pytest.mark.asyncio
async def test_Request(event_loop, server, client):
    client._.createPet.data
    client._.createPet.parameters
    client._.createPet.args()
    client._.createPet.return_value()


@pytest.mark.asyncio
async def test_createPet(event_loop, server, client):
    data = {
        "pet": client.components.schemas["WhiteCat"]
        .model({"name": str(uuid.uuid4()), "white_name": str(uuid.uuid4())})
        .model_dump()
    }
    #    r = await client._.createPet( data=data)
    r = await client._.createPet(data=data)
    assert type(r.__root__.__root__).schema() == client.components.schemas["WhiteCat"].get_type().schema()

    r = await client._.createPet(data=randomPet(client, name=r.__root__.__root__.name))
    assert type(r).schema() == client.components.schemas["Error"].get_type().schema()

    with pytest.raises(pydantic.ValidationError):
        cls = client._.createPet.data.get_type()
        cls()


@pytest.mark.asyncio
async def test_listPet(event_loop, server, client):
    r = await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    l = await client._.listPet()
    assert len(l) > 0


@pytest.mark.asyncio
async def test_getPet(event_loop, server, client):
    pet = await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    r = await client._.getPet(parameters={"petId": pet.__root__.identifier})
    assert type(r.__root__).schema() == type(pet.__root__).schema()

    r = await client._.getPet(parameters={"petId": "-1"})
    assert type(r).schema() == client.components.schemas["Error"].get_type().schema()


@pytest.mark.asyncio
async def test_deletePet(event_loop, server, client):
    r = await client._.deletePet(parameters={"petId": -1})
    assert type(r).schema() == client.components.schemas["Error"].get_type().schema()

    await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    zoo = await client._.listPet()
    for pet in zoo:
        while hasattr(pet, "__root__"):
            pet = pet.__root__
        await client._.deletePet(parameters={"petId": pet.identifier})


@pytest.mark.asyncio
async def test_patchPet(event_loop, server, client):
    pets = [
        client.components.schemas["Dog"]
        .get_type()
        .model_construct(name=str(uuid.uuid4()), age=datetime.timedelta(seconds=random.randint(1, 2**32)))
        for i in range(2)
    ]
    print(pets)
    p = client._.patchPets.data.get_type()
    p = p.model_construct(__root__=pets)
    r = await client._.patchPets(data=p)
    assert isinstance(r, list)
    print(r)


def test_allOf_resolution(openapi_version, petstore_expanded):
    """
    Tests that allOfs are resolved correctly
    """
    petstore_expanded["openapi"] = str(openapi_version)
    petstore_expanded_spec = OpenAPI("/", petstore_expanded)

    ref = petstore_expanded_spec.paths["/pets"].get.responses["200"].content["application/json"].schema_.get_type()

    assert type(ref) == ModelMetaclass

    assert typing.get_origin(ref.__fields__["__root__"].outer_type_) == list

    # outer_type may be ForwardRef
    if isinstance(typing.get_args(ref.__fields__["__root__"].outer_type_)[0], ForwardRef):
        assert ref.__fields__["__root__"].sub_fields[0].type_.__name__ == "Pet"
        items = ref.__fields__["__root__"].sub_fields[0].type_.__fields__
    else:
        assert typing.get_args(ref.__fields__["__root__"].outer_type_)[0].__name__ == "Pet"
        items = typing.get_args(ref.__fields__["__root__"].outer_type_)[0].__fields__

    try:
        assert sorted(map(lambda x: x.name, filter(lambda y: y.required == True, items.values()))) == sorted(
            ["id", "name"]
        ), ref.schema()
    except Exception as e:
        print(e)

    assert sorted(map(lambda x: x.name, items.values())) == ["id", "name", "tag"]

    assert items["id"].outer_type_ == int
    assert items["name"].outer_type_ == str
    assert items["tag"].outer_type_ == str
