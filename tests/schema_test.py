import copy
import typing
import sys
from unittest.mock import MagicMock, patch

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

import yarl
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
    #    with pytest.raises(RecursionError):
    api = OpenAPI("/", with_schema_recursion)

    a = api.components.schemas["A"].get_type().model_construct(ofA=1)
    b = api.components.schemas["B"].get_type().model_construct(ofB=2, a=a)
    assert b.a.ofA == 1

    D = api.components.schemas["D"].get_type()
    d = api.components.schemas["D"].get_type().model_construct(E="e", F=[D(E="esub")])
    assert d.F[0].E == "esub"


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
    v = t.model_validate("1")


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


def _test_schema_with_additionalProperties(api):
    def gettype(name):
        from aiopenapi3 import v20

        if isinstance(api._root, v20.Root):
            return api._root.definitions[name]
        else:
            return api.components.schemas[name]

    A = gettype("A").get_type()
    assert issubclass(A, pydantic.RootModel)
    a = A({"a": 1})
    with pytest.raises(ValidationError):
        A({"1": {"1": 1}})

    B = gettype("B").get_type()
    assert issubclass(B, pydantic.RootModel)
    b = B({"As": a})

    with pytest.raises(ValidationError):
        B({"1": 1})

    C = gettype("C").get_type()
    assert issubclass(C, pydantic.BaseModel) and not issubclass(C, pydantic.RootModel)
    with pytest.raises(ValidationError):
        C(i="!")  # not integer

    c = C(dict=1)
    assert "dict" in c.aio3_additionalProperties

    c = C(i=0, bar={"A": "B"})
    assert c.aio3_additionalProperties["bar"] == {"A": "B"}

    D = gettype("D").get_type()
    assert issubclass(D, pydantic.BaseModel) and not issubclass(D, pydantic.RootModel)
    D()

    with pytest.raises(ValidationError):
        D(dict=1)

    Translation = gettype("Translation").get_type()
    assert issubclass(Translation, pydantic.RootModel)
    t = Translation({"en": "yes", "fr": "qui"})

    import errno, os

    data = {v: {"code": k, "text": os.strerror(k)} for k, v in errno.errorcode.items()}

    Errors = gettype("Errors").get_type()
    assert issubclass(Errors, pydantic.RootModel)

    e = Errors(data)

    Errnos = gettype("Errnos").get_type()
    assert issubclass(Errnos, pydantic.RootModel)
    Errno = gettype("Errno").get_type()
    e = Errnos(data)

    e = Errno(code=errno.EIO, text=errno.errorcode[errno.EIO])

    with pytest.raises(ValidationError, match=r"a\W+Extra inputs are not permitted"):
        Errno(code=errno.EIO, text=errno.errorcode[errno.EIO], a=1)

    with pytest.raises(ValidationError, match=r"text\W+Field required"):
        Errno(code=errno.EIO)

    with pytest.raises(ValidationError):
        Errnos({"1": 1})

    with pytest.raises(ValidationError):
        Errnos({"1": {"1": 1}})


def test_schema_with_additionalProperties(with_schema_additionalProperties):
    api = OpenAPI("/", with_schema_additionalProperties)
    _test_schema_with_additionalProperties(api)


def test_schema_with_additionalProperties_v20(with_schema_additionalProperties_v20):
    api = OpenAPI("/", with_schema_additionalProperties_v20)
    _test_schema_with_additionalProperties(api)


def test_schema_with_empty(with_schema_empty):
    OpenAPI("/", with_schema_empty)


def test_schema_with_extensions(with_schema_extensions):
    api = OpenAPI("/", with_schema_extensions)
    assert api._root.extensions["root"] == "root"
    assert api.servers[0].extensions["Server"] == "Server"

    assert api.components.schemas["X"].extensions["Schema"] == "Schema"
    assert api.components.schemas["Y"].properties["Z"].extensions["Add"] == "Add"
    assert api.components.securitySchemes["user"].root.extensions["SecurityScheme"] == "SecurityScheme"
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


def test_schema_yaml12(openapi_version, with_schema_yaml12):
    from aiopenapi3.plugin import Document

    class OnDocument(Document):
        def parsed(self, ctx):
            ctx.document["openapi"] = str(openapi_version)

    from aiopenapi3.loader import YAML12Loader
    from aiopenapi3.loader import FileSystemLoader

    OpenAPI.load_file(
        "/test.yaml",
        with_schema_yaml12,
        loader=FileSystemLoader(Path("tests/fixtures"), yload=YAML12Loader),
        plugins=[OnDocument()],
    )


def test_schema_property_name_is_type(with_schema_property_name_is_type):
    OpenAPI("/", with_schema_property_name_is_type)


def test_schema_with_additionalProperties_and_named_properties(with_schema_additionalProperties_and_named_properties):
    api = OpenAPI("/", with_schema_additionalProperties_and_named_properties)

    A = api.components.schemas["A"].get_type()
    A.model_validate({"1": 1})
    A.model_validate({"1": 1, "5": 5, "B": "test"})

    B = api.components.schemas["B"].get_type()
    data = typing.get_args(B.model_fields["data"].annotation)[0](b0="string", b1=0)
    b = B(data=data, foo="bar", bar={"a": "a"})
    assert b.aio3_additionalProperties["foo"] == "bar"


def test_schema_with_patternProperties(with_schema_patternProperties):
    api = OpenAPI("/", with_schema_patternProperties)
    A = api.components.schemas["A"].get_type()
    O = api.components.schemas["O"].get_type()
    a = A.model_validate({"I_5": 100})
    assert list(a.aio3_patternProperty("^I_")) == [("I_5", 100)]
    sorted(typing.get_args(a.aio3_patternProperty.__annotations__["item"])) == ["^I_", "^S_"]

    assert a.aio3_patternProperties == {"^S_": [], "^I_": [("I_5", 100)]}

    o = O.model_validate({"O_5": {1: 2}})

    return


def test_schema_discriminated_union(with_schema_discriminated_union):
    api = OpenAPI("/", with_schema_discriminated_union)


def test_schema_discriminated_union_discriminator_name(with_schema_discriminated_union_discriminator_name):
    api = OpenAPI("/", with_schema_discriminated_union_discriminator_name)


def test_schema_discriminated_union_array(with_schema_discriminated_union_array):
    with pytest.raises(aiopenapi3.errors.SpecError):
        api = OpenAPI("/", with_schema_discriminated_union_array)


def test_schema_discriminated_union_warnings(with_schema_discriminated_union_warning, openapi_version):
    from aiopenapi3.errors import DiscriminatorWarning

    with pytest.warns(
        DiscriminatorWarning, match=r"Discriminated Union member \S+ without const/enum key property \S+"
    ):
        api = OpenAPI("/", with_schema_discriminated_union_warning)

    with pytest.warns(
        DiscriminatorWarning,
        match=r"Discriminated Union member key property enum mismatches property mapping \S+ \!= \S+",
    ):
        api = OpenAPI("/", with_schema_discriminated_union_warning)

    if (openapi_version.major, openapi_version.minor, openapi_version.patch) >= (3, 1, 0):
        s = copy.deepcopy(with_schema_discriminated_union_warning)
        #        del s["components"]["schemas"]["C"]["properties"]["object_type"]["enum"]
        s["components"]["schemas"]["C"]["properties"]["object_type"]["const"] = "f"
        with pytest.warns(
            DiscriminatorWarning,
            match=r"Discriminated Union member key property const mismatches property mapping \S+ \!= \S+",
        ):
            api = OpenAPI("/", s)


def test_schema_discriminated_union_merge(with_schema_discriminated_union_merge, openapi_version):
    from aiopenapi3.errors import DiscriminatorWarning

    with pytest.warns(
        DiscriminatorWarning, match=r"Discriminated Union member \S+ without const/enum key property \S+"
    ):
        api = OpenAPI("/", with_schema_discriminated_union_merge)


def test_schema_discriminated_union_deep(with_schema_discriminated_union_deep):
    api = OpenAPI("/", with_schema_discriminated_union_deep)
    Dog = api.components.schemas["Dog"].get_type()
    Pet = api.components.schemas["Pet"].get_type()
    dog = Dog.model_construct()
    pet = Pet(dog)

    d = Dog.model_construct()
    return None


def test_schema_create_update_read(with_schema_create_update_read):
    api = OpenAPI("/", with_schema_create_update_read)
    A = api.components.schemas["A"].get_type()
    AB = api.components.schemas["AB"].get_type()
    A.model_validate(dict(a="a"))
    with pytest.raises(ValidationError):
        AB.model_validate(dict(a="a"))
    with pytest.raises(ValidationError):
        AB.model_validate(dict(b="b"))
    AB.model_validate(dict(b="b", a="a"))


def test_schema_constraints(with_schema_constraints):
    api = OpenAPI("/", with_schema_constraints)
    A = (_A := api.components.schemas["A"]).get_type()

    for i in [0, 1, 5, 6, 10, 11]:
        if _A.maxLength >= i >= _A.minLength:
            A("i" * i)
        else:
            with pytest.raises(ValidationError):
                A("i" * i)

    B = (_B := api.components.schemas["B"]).get_type()
    for i in range(0, 12):
        if _B.exclusiveMaximum > i > _B.exclusiveMinimum:
            B(i)
        else:
            with pytest.raises(ValidationError):
                B(i)

    C = (_C := api.components.schemas["C"]).get_type()
    for i in range(0, 12):
        if i % _C.multipleOf != 0:
            with pytest.raises(ValidationError):
                C(i)
        else:
            C(i)


def test_schema_enum(with_schema_enum):
    api = OpenAPI("/", with_schema_enum)
    Integer = api.components.schemas["Integer"].get_type()
    Integer(2)
    with pytest.raises(ValidationError):
        Integer(5)
    with pytest.raises(ValidationError):
        Integer(None)

    String = api.components.schemas["String"].get_type()
    String("a")
    with pytest.raises(ValidationError):
        String("c")
    with pytest.raises(ValidationError):
        String(None)

    Nullable = api.components.schemas["Nullable"].get_type()
    Nullable("a")
    Nullable(None)
    with pytest.raises(ValidationError):
        Nullable("c")

    Mixed = api.components.schemas["Mixed"].get_type()
    Mixed(1)
    Mixed("good")
    Mixed("yes")
    Mixed(True)
    Mixed(None)
    with pytest.raises(ValidationError):
        Mixed(2)


def test_schema_enum_object(with_schema_enum_object):
    with pytest.raises(NotImplementedError, match="complex enums/const are not supported"):
        api = OpenAPI("/", with_schema_enum_object)


def test_schema_enum_array(with_schema_enum_array):
    with pytest.raises(NotImplementedError, match="complex enums/const are not supported"):
        api = OpenAPI("/", with_schema_enum_array)


def test_schema_pathitems(httpx_mock, with_schema_pathitems):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, json={"foo": "bar"})
    api = OpenAPI("/", with_schema_pathitems, session_factory=httpx.Client)
    req = api.createRequest(("/a", "get"))
    r = req()

    req = api.createRequest("b")
    r = req()
    r = api._.b()

    return


def test_schema_baseurl_v20(with_schema_baseurl_v20):
    api = OpenAPI("/", with_schema_baseurl_v20, session_factory=httpx.Client)
    assert api.url == yarl.URL("https://api.example.com:81/v1")


def test_schema_ref_nesting(with_schema_ref_nesting):
    for i in range(10):
        OpenAPI("/", with_schema_ref_nesting)
