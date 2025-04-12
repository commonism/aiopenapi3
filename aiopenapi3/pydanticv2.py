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

from pydantic import ConfigDict, BaseModel, PydanticUserError
from pydantic.main import ModelT
from typing import Callable, cast, Optional, Union
import sys
import types


def create_model(  # noqa: C901
    model_name: str,
    /,
    *,
    __config__: Optional[ConfigDict] = None,
    __doc__: Optional[str] = None,
    __base__: Union[type[ModelT], tuple[type[ModelT], ...], None] = None,
    __module__: Optional[str] = None,
    __validators__: Optional[dict[str, Callable[..., Any]]] = None,
    __cls_kwargs__: Optional[dict[str, Any]] = None,
    # TODO PEP 747: replace `Any` by the TypeForm:
    **field_definitions: Union[Any, tuple[str, Any]],
) -> type[ModelT]:
    """
    unfortunate this is required, but …
    c.f. https://github.com/pydantic/pydantic/pull/11032#issuecomment-2797667916
    """
    if __base__ is None:
        __base__ = (cast("type[ModelT]", BaseModel),)
    elif not isinstance(__base__, tuple):
        __base__ = (__base__,)

    __cls_kwargs__ = __cls_kwargs__ or {}

    fields: dict[str, Any] = {}
    annotations: dict[str, Any] = {}

    for f_name, f_def in field_definitions.items():
        if isinstance(f_def, tuple):
            if len(f_def) != 2:
                raise PydanticUserError(
                    f"Field definition for {f_name!r} should a single element representing the type or a two-tuple, the first element "
                    "being the type and the second element the assigned value (either a default or the `Field()` function).",
                    code="create-model-field-definitions",
                )

            if f_def[0]:
                annotations[f_name] = f_def[0]
            fields[f_name] = f_def[1]
        else:
            annotations[f_name] = f_def

    if __module__ is None:
        f = sys._getframe(1)
        __module__ = f.f_globals["__name__"]

    namespace: dict[str, Any] = {"__annotations__": annotations, "__module__": __module__}
    if __doc__:
        namespace.update({"__doc__": __doc__})
    if __validators__:
        namespace.update(__validators__)
    namespace.update(fields)
    if __config__:
        namespace["model_config"] = __config__
    resolved_bases = types.resolve_bases(__base__)
    meta, ns, kwds = types.prepare_class(model_name, resolved_bases, kwds=__cls_kwargs__)
    if resolved_bases is not __base__:
        ns["__orig_bases__"] = __base__
    namespace.update(ns)

    return meta(
        model_name,
        resolved_bases,
        namespace,
        __pydantic_reset_parent_namespace__=False,
        _create_model_module=__module__,
        **kwds,
    )
