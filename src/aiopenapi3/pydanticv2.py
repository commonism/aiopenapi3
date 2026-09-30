from datetime import date, datetime, time, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
from pathlib import Path
from re import Pattern
from typing import Any
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
