from decimal import Decimal
from datetime import datetime, date, time, timedelta
from ipaddress import IPv4Network, IPv6Network, IPv4Interface, IPv6Interface, IPv4Address, IPv6Address
from pathlib import Path
from typing import Any
from re import Pattern
from uuid import UUID

from pydantic import TypeAdapter

field_classes_to_support: tuple[type[Any], ...] = (
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

field_class_to_schema: tuple[tuple[Any, dict[str, Any]], ...] = tuple(
    (field_class, TypeAdapter(field_class).json_schema()) for field_class in field_classes_to_support
)
