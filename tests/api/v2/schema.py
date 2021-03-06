from datetime import timedelta
import uuid

import sys

if sys.version_info >= (3, 9):
    from typing import List, Optional, Literal, Union, Annotated
else:
    from typing import List, Optional, Union
    from typing_extensions import Annotated, Literal


import pydantic
from pydantic import BaseModel, Field
from pydantic.fields import Undefined


class PetBase(BaseModel):
    identifier: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    tags: Optional[List[str]]  # = Field(default_factory=list)


class BlackCat(PetBase):
    pet_type: Literal["cat"] = "cat"
    color: Literal["black"] = "black"
    black_name: str


class WhiteCat(PetBase):
    pet_type: Literal["cat"] = "cat"
    color: Literal["white"] = "white"
    white_name: str


# Can also be written with a custom root type
#
class Cat(BaseModel):
    __root__: Annotated[Union[BlackCat, WhiteCat], Field(discriminator="color")]

    def __getattr__(self, item):
        return getattr(self.__root__, item)

    def __setattr__(self, item, value):
        return setattr(self.__root__, item, value)


# Cat = Annotated[Union[BlackCat, WhiteCat], Field(default=Undefined, discriminator='color')]


class Dog(PetBase):
    pet_type: Literal["dog"] = "dog"
    name: str
    age: timedelta


# Pet = Annotated[Union[Cat, Dog], Field(default=Undefined, discriminator='pet_type')]


class Pet(BaseModel):
    __root__: Annotated[Union[Cat, Dog], Field(discriminator="pet_type")]

    def __getattr__(self, item):
        return getattr(self.__root__, item)

    def __setattr__(self, item, value):
        return setattr(self.__root__, item, value)


class Pets(BaseModel):
    __root__: List[Pet] = Field(..., description="list of pet")


class Error(BaseModel):
    code: int
    message: str
