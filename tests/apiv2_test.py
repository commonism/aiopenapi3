import datetime
import random
import sys
import asyncio
import uuid
from typing import ForwardRef
import typing


import pydantic

import pytest
import pytest_asyncio

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config

import aiopenapi3
from aiopenapi3 import OpenAPI
from aiopenapi3.v31.schemas import Schema

from api.main import app
from api.v2.schema import Dog as _Dog

# pytest.skip(allow_module_level=True)

from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse


@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)


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


@pytest.fixture(scope="session", params=[2])
def version(request):
    return f"v{request.param}"


from aiopenapi3.debug import DescriptionDocumentDumper


@pytest_asyncio.fixture(scope="session")
async def client(event_loop, server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"

    api = await aiopenapi3.OpenAPI.load_async(url, plugins=[DescriptionDocumentDumper("/tmp/schema.yaml")])
    return api


@pytest.mark.xfail()
def test_Pet():
    import json

    data = _Dog.model_json_schema()
    #    print(json.dumps(data, indent=True))
    shma = Schema.model_validate(data)
    shma._identity = "Dog"
    t = shma.get_type()
    t.model_rebuild()
    assert t.model_json_schema() == data


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_sync(event_loop, server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"
    api = await asyncio.to_thread(aiopenapi3.OpenAPI.load_sync, url)
    return api


@pytest.mark.asyncio
async def test_description_document(event_loop, server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"
    api = await aiopenapi3.OpenAPI.load_async(url)
    return api


@pytest.mark.xfail()
@pytest.mark.asyncio
async def test_model(event_loop, server, client):
    orig = client.components.schemas["WhiteCat"].model_dump(exclude_unset=True)
    crea = client.components.schemas["WhiteCat"].get_type().model_json_schema()
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


def randomPet(client, name=None, cat=False):
    if name:
        Pet = client.components.schemas["Pet-Input"].get_type()
        if not cat:
            Dog = typing.get_args(typing.get_args(Pet.model_fields["root"].annotation)[0])[1]
            dog = Dog(
                name=name,
                age=datetime.timedelta(seconds=random.randint(1, 2**32)),
                tags=[],
            )
            pet = Pet(dog)
        else:
            Cat = typing.get_args(typing.get_args(Pet.model_fields["root"].annotation)[0])[0]
            WhiteCat = typing.get_args(typing.get_args(Cat.model_fields["root"].annotation)[0])[1]
            wc = WhiteCat(pet_type="cat", color="white", name="whitey", white_name="white")
            cat = Cat(wc)
            pet = Pet(cat)

        return client._.createPet.data.get_type().model_construct(pet=pet)
    else:
        return {
            "pet": client.components.schemas["WhiteCat-Input"]
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
        .model(
            {
                "name": str(uuid.uuid4()),
                "white_name": str(uuid.uuid4()),
                "tags": [],
                "identifier": str(uuid.uuid4()),
            }
        )
        .model_dump()
    }
    import json

    print(json.dumps(data["pet"], indent=4))
    r = await client._.createPet(data=data)
    assert isinstance(r, client.components.schemas["Pet-Input"].get_type())

    r = await client._.createPet(data=randomPet(client, name=r.root.root.name))
    Error = client.components.schemas["Error"].get_type()
    assert isinstance(r, Error)
    # type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()

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
    r = await client._.getPet(parameters={"petId": pet.root.identifier})

    #   mismatch due to serialization vs validation models for in/out
    #   https://github.com/tiangolo/fastapi/pull/10011
    #    assert type(r.root).model_json_schema() == type(pet.root).model_json_schema()

    r = await client._.getPet(parameters={"petId": "-1"})
    assert type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()


@pytest.mark.asyncio
async def test_deletePet(event_loop, server, client):
    r = await client._.deletePet(parameters={"petId": -1})
    assert type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()

    await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    zoo = await client._.listPet()
    for pet in zoo:
        while hasattr(pet, "root"):
            pet = pet.root
        await client._.deletePet(parameters={"petId": pet.identifier})


@pytest.mark.asyncio
async def test_patchPet(event_loop, server, client):
    Pet = client.components.schemas["Pet-Input"].get_type()
    Dog = typing.get_args(typing.get_args(Pet.model_fields["root"].annotation)[0])[1]
    pets = [
        Pet(
            Dog.model_construct(
                name=str(uuid.uuid4()),
                age=datetime.timedelta(seconds=random.randint(1, 2**32)),
                tags=[],
            )
        )
        for i in range(2)
    ]
    print(pets)
    p = client._.patchPets.data.get_type()
    p = p.model_construct(pets)
    r = await client._.patchPets(data=p)
    assert isinstance(r, list)
    print(r)


@pytest.mark.xfail
def test_allOf_resolution(openapi_version, petstore_expanded):
    """
    Tests that allOfs are resolved correctly
    """
    petstore_expanded["openapi"] = str(openapi_version)
    petstore_expanded_spec = OpenAPI("/", petstore_expanded)

    ref = petstore_expanded_spec.paths["/pets"].get.responses["200"].content["application/json"].schema_.get_type()

    #    assert type(ref) == ModelMetaclass

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
        ), ref.model_json_schema()
    except Exception as e:
        print(e)

    assert sorted(map(lambda x: x.name, items.values())) == ["id", "name", "tag"]

    assert items["id"].outer_type_ == int
    assert items["name"].outer_type_ == str
    assert items["tag"].outer_type_ == str
