import errno
import uuid
from typing import Optional, Union
from typing import Annotated

import starlette.status
from fastapi import Body, Response, Header, APIRouter, Path
from fastapi.responses import JSONResponse
from fastapi_versioning import version

from . import schema

from fastapi_versioning import versioned_api_route

from pydantic import RootModel

router = APIRouter(route_class=versioned_api_route(2))

ZOO = dict()


def _idx(l):
    yield from range(l)


idx = _idx(100)


@router.post(
    "/pet",
    operation_id="createPet",
    response_model=schema.Pet,
    responses={201: {"model": schema.Pet}, 409: {"model": schema.Error}},
)
def createPet(
    response: Response,
    pet: schema.Pet = Body(..., embed=True),
) -> schema.Pet:
    # if isinstance(pet, Cat):
    #     pet = pet.__root__
    # elif isinstance(pet, Dog):
    #     pass
    #    name = getattr(pet, "name") or getattr(pet, "white_name") or getattr(pet, "black_name")
    if pet.name in ZOO:
        return JSONResponse(
            status_code=starlette.status.HTTP_409_CONFLICT,
            content=schema.Error(code=errno.EEXIST, message=f"{pet.name} already exists").model_dump(),
        )
    pet.identifier = str(uuid.uuid4())
    ZOO[pet.name] = r = pet
    response.status_code = starlette.status.HTTP_201_CREATED
    return r


@router.get("/pet", operation_id="listPet", response_model=schema.Pets)
def listPet(limit: Optional[int] = None) -> schema.Pets:
    return list(ZOO.values())


@router.get("/pets/{petId}", operation_id="getPet", response_model=schema.Pet, responses={404: {"model": schema.Error}})
def getPet(pet_id: str = Path(..., alias="petId")) -> schema.Pets:
    for k, pet in ZOO.items():
        if pet_id == pet.identifier:
            return pet
    else:
        return JSONResponse(
            status_code=starlette.status.HTTP_404_NOT_FOUND,
            content=schema.Error(code=errno.ENOENT, message=f"{pet_id} not found").model_dump(),
        )


@router.delete(
    "/pets/{petId}", operation_id="deletePet", responses={204: {"model": None}, 404: {"model": schema.Error}}
)
def deletePet(
    response: Response,
    x_raise_nonexist: Annotated[Union[bool, None], Header()],
    pet_id: str = Path(..., alias="petId"),
) -> None:
    for k, pet in ZOO.items():
        if pet_id == pet.identifier:
            del ZOO[k]
            response.status_code = starlette.status.HTTP_204_NO_CONTENT
            return response
    else:
        return JSONResponse(
            status_code=starlette.status.HTTP_404_NOT_FOUND,
            content=schema.Error(code=errno.ENOENT, message=f"{pet_id} not found").model_dump(),
        )


@router.patch("/pets", operation_id="patchPets", responses={200: {"model": schema.Pets}})
def patchPets(response: Response, pets: schema.Pets):
    print(pets)
    return pets + list(ZOO.values())
