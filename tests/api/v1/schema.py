from typing import Optional

from pydantic import BaseModel, RootModel, Field


class PetBase(BaseModel):
    name: str
    tag: Optional[str] = Field(default=None)


class PetCreate(PetBase):
    pass


class Pet(PetBase):
    id: int


class Pets(RootModel):
    root: list[Pet] = Field(..., description="list of pet")


class Error(BaseModel):
    code: int
    message: str
