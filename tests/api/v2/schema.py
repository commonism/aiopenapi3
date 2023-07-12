from datetime import timedelta
import uuid

import sys

if sys.version_info >= (3, 9):
    from typing import List, Optional, Literal, Union, Annotated
else:
    from typing import List, Optional, Union
    from typing_extensions import Annotated, Literal


import pydantic
from pydantic import BaseModel, RootModel, Field

# from pydantic.fields import Undefined
from pydantic_core import PydanticUndefined as Undefined


class PetBase(BaseModel):
    identifier: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tags: List[str] = Field(default_factory=list)


class BlackCat(PetBase):
    pet_type: Literal["cat"] = "cat"
    color: Literal["black"] = "black"
    black_name: str


class WhiteCat(PetBase):
    pet_type: Literal["cat"] = "cat"
    color: Literal["white"] = "white"
    white_name: str


class Cat(RootModel[Annotated[Union[BlackCat, WhiteCat], Field(discriminator="color")]]):
    def __getattr__(self, item):
        return getattr(self.root, item)

    def __setattr__(self, item, value):
        return setattr(self.root, item, value)


class Dog(PetBase):
    pet_type: Literal["dog"] = "dog"
    name: str
    age: timedelta


class Pet(RootModel[Annotated[Union[Cat, Dog], Field(discriminator="pet_type")]]):
    def __getattr__(self, item):
        return getattr(self.root, item)

    def __setattr__(self, item, value):
        return setattr(self.root, item, value)


# class Pet(RootModel):
#    root: Annotated[Union[Cat, Dog], Field(discriminator="pet_type")]


Pets = List[Pet]


class Error(BaseModel):
    code: int
    message: str
