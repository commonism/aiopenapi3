from __future__ import annotations

"""
This file tests that $ref resolution works as expected, and that
allOfs are populated as expected as well.
"""

from typing import ForwardRef

import typing

import pytest
from aiopenapi3 import OpenAPI

from pydantic._internal._model_construction import ModelMetaclass

import pydantic._internal._fields
from pydantic import RootModel


def test_ref_resolution(openapi_version, petstore_expanded):
    """
    Tests that $refs are resolved as we expect them to be
    """
    petstore_expanded_spec = OpenAPI("/", petstore_expanded)

    ref = petstore_expanded_spec.paths["/pets"].get.responses["default"].content["application/json"].schema_

    assert type(ref._target) == openapi_version.schema
    assert ref.type == "object"
    assert len(ref.properties) == 2
    assert "code" in ref.properties
    assert "message" in ref.properties
    assert ref.required == ["code", "message"]

    code = ref.properties["code"]
    assert code.type == "integer"
    assert code.format == "int32"

    message = ref.properties["message"]
    assert message.type == "string"


def test_allOf_resolution(petstore_expanded):
    """
    Tests that allOfs are resolved correctly
    """
    petstore_expanded_spec = OpenAPI("/", petstore_expanded)

    ref = petstore_expanded_spec.paths["/pets"].get.responses["200"].content["application/json"].schema_.get_type()

    # RootModel[List[ForwardRef('__types["Pet"]')]]
    assert type(ref) == ModelMetaclass

    assert issubclass(ref, RootModel)
    assert typing.get_origin(ref.model_fields["root"].annotation) == list

    fwd = typing.get_args(ref.model_fields["root"].annotation)[0]
    if isinstance(fwd, ForwardRef):
        pet = fwd.__forward_value__
    else:
        pet = fwd
    items = pet.model_fields

    assert sorted(items.keys()) == ["id", "name", "tag"]

    def is_nullable(x):
        # Optional[…] or | None
        return typing.get_origin(x.annotation) == typing.Union and type(None) in typing.get_args(x.annotation)

    assert sorted(map(lambda x: x[0], filter(lambda y: is_nullable(y[1]), items.items()))) == sorted(
        ["tag"]
    ), ref.schema()

    def is_required(x):
        # not assign a default '= Field(default=…)' or '= …'
        return x.default == pydantic._internal._fields.Undefined

    assert sorted(map(lambda x: x[0], filter(lambda y: is_required(y[1]), items.items()))) == sorted(
        ["id", "name"]
    ), ref.schema()

    assert items["id"].annotation == int
    assert items["name"].annotation == str
    assert items["tag"].annotation == typing.Optional[str]

    r = ref.model_validate([dict(id=1, name="dog"), dict(id=2, name="cat", tag="x")])
    assert len(r.root) == 2
    assert r.root[1].tag == "x"


def test_paths_content_schema_array_ref(openapi_version):
    import aiopenapi3.v30.general
    import aiopenapi3.v31.general

    expected = {0: aiopenapi3.v30.general.Reference, 1: aiopenapi3.v31.general.Reference}[openapi_version.minor]

    SPEC = f"""openapi: {openapi_version}
info:
  title: API
  version: 1.0.0
paths:
  /pets:
    get:
      description: "yes"
      operationId: findPets
      responses:
        '200':
          description: pet response
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/Pet'
components:
  schemas:
    Pet:
      type: string
    """
    api = OpenAPI.loads("test.yaml", SPEC)
    assert api.paths["/pets"].get.responses["200"].content["application/json"].schema_.items.__class__ == expected
