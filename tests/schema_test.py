import errno
import sys
from unittest.mock import MagicMock, patch

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

import httpx
import pytest
from pydantic import ValidationError
import pydantic

import aiopenapi3
from aiopenapi3 import OpenAPI
from aiopenapi3.errors import ResponseSchemaError


def test_invalid_response(httpx_mock, petstore_expanded):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json={"foo": 1})
    api = OpenAPI("test.yaml", petstore_expanded, session_factory=httpx.Client)

    with pytest.raises(ResponseSchemaError) as r:
        p = api._.find_pet_by_id(data={}, parameters={"id": 1})


def test_schema_without_properties(httpx_mock):
    """
    Tests that a response model is generated, and responses parsed correctly, for
    response schemas without properties
    """
    api = OpenAPI.load_file(
        "/test.yaml",
        Path("paths-content-schema-property-without-properties.yaml"),
        loader=aiopenapi3.FileSystemLoader(Path("tests/fixtures")),
        session_factory=httpx.Client,
    )
    httpx_mock.add_response(
        headers={"Content-Type": "application/json"},
        json={
            "example": "it worked",
            "no_properties": {},
        },
    )

    result = api._.noProps()
    assert result.example == "it worked"

    # the schema without properties did get its own named type defined
    assert type(result.no_properties).__name__ == "has_no_properties"
    # and it has no fields
    assert len(result.no_properties.model_fields) == 0


def test_schema_anyof(with_schema_anyof):
    api = OpenAPI("/", with_schema_anyof)
    s = api.components.schemas["AB"]
    t = s.get_type()

    # the semantics …


#    A = next(filter(lambda x: x.type_.__name__ == "A", t.model_fields["root"].sub_fields))
#    kwargs = {"ofA": 1, "id": 2}
#    obj = A.type_(**kwargs)
#    assert obj.model_dump() == kwargs
#    ab = t(__root__=obj)
#    assert ab


def test_schema_recursion(with_schema_recursion):
    """
    https://github.com/pydantic/pydantic/issues/5730
    """
    pytest.skip()

    #    with pytest.raises(RecursionError):
    api = OpenAPI("/", with_schema_recursion)


#    a = api.components.schemas["A"].get_type().model_construct(ofA=1)
#    b = api.components.schemas["B"].get_type().model_construct(ofB=2, a=a)


#    e = api.components.schemas["D"].get_type().model_fields["F"].type_(__root__={"E": 0})
#    d = api.components.schemas["D"].get_type().model_construct(E=e)


def test_schema_self_recursion(with_schema_self_recursion):
    api = OpenAPI("/", with_schema_self_recursion)

    with pytest.raises(RecursionError):
        api.components.schemas["Self"].get_type().model_construct()

    with pytest.raises(RecursionError):
        api.components.schemas["Any"].get_type().model_construct()


def test_schema_type_list(with_schema_type_list):
    api = OpenAPI("/", with_schema_type_list)
    _Any = api.components.schemas["Any"]
    Any = _Any.get_type()
    a = Any.model_validate("1")
    print(a)
    A = Any.model_validate(1)
    print(A)


def test_schema_type_missing(with_schema_type_missing):
    """
    https://stackoverflow.com/questions/47374980/schema-object-without-a-type-attribute-in-swagger-2-0

    :param with_schema_type_missing:
    :return:
    """
    api = OpenAPI("/", with_schema_type_missing)
    t = api.components.schemas["Any"].get_type()
    v = t.model_validate(dict(id=1))
    assert v.root.id == 1


def test_schema_type_string_format_byte_base64(with_schema_type_string_format_byte_base64):
    api = OpenAPI("/", with_schema_type_string_format_byte_base64)
    b64 = api.components.schemas["Base64Property"].get_type()
    RAW = "test"
    B64 = {"data": "dGVzdA==\n"}
    v = b64.model_validate(B64)
    assert v.model_dump() == B64
    assert v.data == RAW

    v = b64(**B64)
    assert v.model_dump() == B64
    assert v.data == RAW

    v = b64.model_construct(data="test")
    assert v.model_dump() == B64
    assert v.data == RAW

    b64 = api.components.schemas["Base64Root"].get_type()
    v = b64.model_construct(root=RAW)
    assert v.model_dump() == B64["data"]
    assert v.root == RAW


def test_schema_Of_parent_properties(with_schema_Of_parent_properties):
    # this is supposed to work
    #    with pytest.raises(ValueError, match="__root__ cannot be mixed with other fields"):
    # FIXME
    api = OpenAPI("/", with_schema_Of_parent_properties)


def test_schema_with_additionalProperties(with_schema_additionalProperties):
    api = OpenAPI("/", with_schema_additionalProperties)

    A = api.components.schemas["A"].get_type()
    a = A({"a": 1})
    with pytest.raises(ValidationError):
        A({"1": {"1": 1}})

    B = api.components.schemas["B"].get_type()
    b = B({"As": a})

    with pytest.raises(ValidationError):
        B({"1": 1})

    C = api.components.schemas["C"].get_type()
    # we do not allow additional properties …
    # c = C(dict=1)  # overwriting …
    with pytest.raises(ValidationError):
        C(i="!")  # not integer

    D = api.components.schemas["D"].get_type()
    D()

    with pytest.raises(ValidationError):
        D(dict=1)

    Translation = api.components.schemas["Translation"].get_type()
    t = Translation({"en": "yes", "fr": "qui"})

    import errno, os

    data = {v: {"code": k, "text": os.strerror(k)} for k, v in errno.errorcode.items()}

    Errors = api.components.schemas["Errors"].get_type()

    e = Errors(data)

    Errnos = api.components.schemas["Errnos"].get_type()
    Errno = api.components.schemas["Errno"].get_type()
    e = Errnos(data)

    e = Errno(code=errno.EIO, text=errno.errorcode[errno.EIO])

    with pytest.raises(ValidationError):
        Errno(a=errno.EIO)

    with pytest.raises(ValidationError):
        Errnos({"1": 1})

    with pytest.raises(ValidationError):
        Errnos({"1": {"1": 1}})


def test_schema_with_additionalProperties_v20(with_schema_additionalProperties_v20):
    OpenAPI("/", with_schema_additionalProperties_v20)


def test_schema_with_empty(with_schema_empty):
    OpenAPI("/", with_schema_empty)


def test_schema_with_extensions(with_schema_extensions):
    api = OpenAPI("/", with_schema_extensions)
    assert api._root.extensions["root"] == "root"
    assert api.servers[0].extensions["Server"] == "Server"

    assert api.components.schemas["X"].extensions["Schema"] == "Schema"
    assert api.components.schemas["Y"].properties["Z"].extensions["Add"] == "Add"
    assert api.components.securitySchemes["user"].extensions["SecurityScheme"] == "SecurityScheme"
    assert api.components.parameters["X"].extensions["Parameter"] == "Parameter"
    assert api.paths.extensions["Paths"] == "Paths"
    assert api.paths["/x"].extensions["PathItem"] == "PathItem"
    assert api.paths["/x"].post.extensions["Operation"] == "Operation"
    assert api.paths["/x"].post.requestBody.extensions["requestBody"] == "requestBody"

    assert api.paths["/x"].post.requestBody.content["multipart/form-data"].extensions["MediaType"] == "MediaType"
    assert api.paths["/x"].post.responses["200"].extensions["Response"] == "Response"


def test_schema_properties_default(with_schema_properties_default):
    api = OpenAPI("/", with_schema_properties_default)
    a = api.components.schemas["Number"].model({})
    assert a.code == 1


def test_schema_yaml_tags_invalid(openapi_version, with_schema_yaml_tags_invalid):
    from aiopenapi3.plugin import Document

    class OnDocument(Document):
        def parsed(self, ctx):
            ctx.document["openapi"] = str(openapi_version)

    from aiopenapi3.loader import YAMLCompatibilityLoader
    from aiopenapi3.loader import FileSystemLoader

    OpenAPI.load_file(
        "/test.yaml",
        with_schema_yaml_tags_invalid,
        loader=FileSystemLoader(Path("tests/fixtures"), yload=YAMLCompatibilityLoader),
        plugins=[OnDocument()],
    )


def test_schema_property_name_is_type(with_schema_property_name_is_type):
    OpenAPI("/", with_schema_property_name_is_type)


def test_schema_x(with_schema_additionalProperties_and_named_properties):
    with pytest.warns(UserWarning, match="Ignoring Schema with additionalProperties and named properties"):
        api = OpenAPI("/", with_schema_additionalProperties_and_named_properties)

    # A = api.components.schemas['A'].get_type()
    # A.model_validate({1:"test"})
    # A.model_validate({"1":1, "5":5, "B":"test"})


def test_schema_with_patternProperties(with_schema_patternProperties):
    api = OpenAPI("/", with_schema_patternProperties)
    A = api.components.schemas["A"].get_type()
    a = A.model_validate({"I_5": 100})

    return
