import datetime
import random
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

from fastapi.responses import PlainTextResponse


@app.exception_handler(Exception)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest.fixture(scope="session")
def event_loop_policy():
    return uvloop.EventLoopPolicy()


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


@pytest.fixture(scope="session", params=[2])
def version(request):
    return f"v{request.param}"


from aiopenapi3.debug import DescriptionDocumentDumper


@pytest_asyncio.fixture(loop_scope="session")
async def client(server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"

    api = await aiopenapi3.OpenAPI.load_async(url, plugins=[DescriptionDocumentDumper("/tmp/schema.yaml")])
    return api


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.xfail()
def test_Pet():

    data = _Dog.model_json_schema()
    #    print(json.dumps(data, indent=True))
    shma = Schema.model_validate(data)
    shma._identity = "Dog"
    t = shma.get_type()
    t.model_rebuild()
    assert t.model_json_schema() == data


@pytest.mark.asyncio(loop_scope="session")
async def test_sync(server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"
    api = await asyncio.to_thread(aiopenapi3.OpenAPI.load_sync, url)
    return api


@pytest.mark.asyncio(loop_scope="session")
async def test_description_document(server, version):
    url = f"http://{server.bind[0]}/{version}/openapi.json"
    api = await aiopenapi3.OpenAPI.load_async(url)
    return api


@pytest.mark.xfail()
@pytest.mark.asyncio(loop_scope="session")
async def test_model(server, client):
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
        Pet = client.components.schemas["Pet"].get_type()
        if not cat:
            Dog = typing.get_args(Pet.model_fields["root"].annotation)[1]
            dog = Dog(
                name=name,
                age=datetime.timedelta(seconds=random.randint(1, 2**32)),
                tags=[],
            )
            pet = Pet(dog)
        else:
            Cat = typing.get_args(Pet.model_fields["root"].annotation)[0]
            WhiteCat = typing.get_args(Cat.model_fields["root"].annotation)[1]
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


@pytest.mark.asyncio(loop_scope="session")
async def test_Request(server, client):
    client._.createPet.data
    client._.createPet.parameters
    client._.createPet.args()
    client._.createPet.return_value()


@pytest.mark.asyncio(loop_scope="session")
async def test_createPet(server, client):
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
    assert isinstance(r, client.components.schemas["Cat"].get_type())

    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await client._.createPet(data=randomPet(client, name=r.root.name))

    Error = client.components.schemas["Error"].get_type()
    assert isinstance(e.value.data, Error)
    # type(r).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()

    with pytest.raises(pydantic.ValidationError):
        cls = client._.createPet.data.get_type()
        cls()


@pytest.mark.asyncio(loop_scope="session")
async def test_listPet(server, client):
    r = await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    l = await client._.listPet(parameters={"limit": 1})
    assert len(l) > 0

    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await client._.listPet(parameters={"limit": None})

    Error = client.components.schemas["HTTPValidationError"].get_type()
    assert isinstance(e.value.data, Error)


@pytest.mark.asyncio(loop_scope="session")
async def test_getPet(server, client):
    pet = await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    r = await client._.getPet(parameters={"petId": pet.identifier})

    #   mismatch due to serialization vs validation models for in/out
    #   https://github.com/tiangolo/fastapi/pull/10011
    #    assert type(r.root).model_json_schema() == type(pet.root).model_json_schema()

    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await client._.getPet(parameters={"petId": "-1"})

    assert type(e.value.data).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()


@pytest.mark.asyncio(loop_scope="session")
async def test_deletePet(server, client):

    with pytest.raises(aiopenapi3.errors.HTTPClientError) as e:
        await client._.deletePet(parameters={"petId": str(uuid.uuid4()), "x-raise-nonexist": True})

    assert type(e.value.data).model_json_schema() == client.components.schemas["Error"].get_type().model_json_schema()

    await client._.createPet(data=randomPet(client, str(uuid.uuid4())))
    zoo = await client._.listPet(parameters={"limit": 1})
    for pet in zoo:
        while hasattr(pet, "root"):
            pet = pet.root
        await client._.deletePet(parameters={"petId": pet.identifier, "x-raise-nonexist": False})


@pytest.mark.asyncio(loop_scope="session")
async def test_patchPet(server, client):
    Pet = client.components.schemas["Pet"].get_type()
    Dog = typing.get_args(Pet.model_fields["root"].annotation)[1]
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

    assert typing.get_origin(ref.__fields__["__root__"].outer_type_) is list

    # outer_type may be ForwardRef
    if isinstance(typing.get_args(ref.__fields__["__root__"].outer_type_)[0], ForwardRef):
        assert ref.__fields__["__root__"].sub_fields[0].type_.__name__ == "Pet"
        items = ref.__fields__["__root__"].sub_fields[0].type_.__fields__
    else:
        assert typing.get_args(ref.__fields__["__root__"].outer_type_)[0].__name__ == "Pet"
        items = typing.get_args(ref.__fields__["__root__"].outer_type_)[0].__fields__

    try:
        assert sorted(map(lambda x: x.name, filter(lambda y: y.required, items.values()))) == sorted(["id", "name"]), (
            ref.model_json_schema()
        )
    except Exception as e:
        print(e)

    assert sorted(map(lambda x: x.name, items.values())) == ["id", "name", "tag"]

    assert items["id"].outer_type_ is int
    assert items["name"].outer_type_ is str
    assert items["tag"].outer_type_ is str
