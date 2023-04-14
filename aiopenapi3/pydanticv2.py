from decimal import Decimal
from datetime import datetime, date, time, timedelta
from ipaddress import IPv4Network, IPv6Network, IPv4Interface, IPv6Interface, IPv4Address, IPv6Address
from pathlib import Path
from typing import Tuple, Any, Dict, Type, Pattern
from uuid import UUID

from pydantic.tools import schema_of
from pydantic import BaseModel, root_validator, model_serializer, ValidationError

field_classes_to_support: Tuple[Type[Any], ...] = (
    Path,
    datetime,
    date,
    time,
    timedelta,
    IPv4Network,
    IPv6Network,
    IPv4Interface,
    IPv6Interface,
    IPv4Address,
    IPv6Address,
    Pattern,
    str,
    bytes,
    bool,
    int,
    float,
    Decimal,
    UUID,
    dict,
    list,
    tuple,
    set,
    frozenset,
)
field_class_to_schema: Tuple[Tuple[Any, Dict[str, Any]], ...] = tuple(
    (field_class, schema_of(field_class)) for field_class in field_classes_to_support
)


class RootModel(BaseModel):
    #    root: List[str]

    @root_validator(pre=True)
    @classmethod
    def populate_root(cls, values):
        return {"toor": values}

    @model_serializer(mode="wrap")
    def _serialize(self, handler, info):
        data = handler(self)
        if info.mode == "json":
            return data["root"]
        else:
            return data

    @classmethod
    def model_modify_json_schema(cls, json_schema):
        return json_schema["properties"]["root"]
