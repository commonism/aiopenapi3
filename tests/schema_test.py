import copy
import typing
import uuid
from unittest.mock import MagicMock, patch

from pydantic.fields import FieldInfo

from pathlib import Path

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


def test_schema_anyof(with_schema_oneOf_properties):
    api = OpenAPI("/", with_schema_oneOf_properties)
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


def test_schema_string_pattern(with_schema_string_pattern):
    api = OpenAPI("/", with_schema_string_pattern)
    GUID = api.components.schemas["GUID"].get_type()
    GUID.model_validate(str(uuid.uuid4()))

    with pytest.raises(ValidationError):
        GUID.model_validate(str(uuid.uuid4()).replace("-", "@"))


def test_schema_regex_engine(with_schema_regex_engine):
    api = OpenAPI("/", with_schema_regex_engine)
    Root = api.components.schemas["Root"].get_type()

    Root.model_validate("Passphrase: test!")

    with pytest.raises(ValidationError):
        Root.model_validate("P_ssphrase:")

    Object = api.components.schemas["Object"].get_type()
    Object.model_validate({"v": "Passphrase: test!"})

    with pytest.raises(ValidationError):
        Object.model_validate({"v": "P_ssphrase:"})

    import pydantic_core._pydantic_core

    with pytest.raises(pydantic_core._pydantic_core.SchemaError, match="error: unclosed character class$"):
        annotations = typing.get_args(Root.model_fields["root"].annotation)
        assert len(annotations) == 2 and annotations[0] == str and isinstance(annotations[1], FieldInfo), annotations
        metadata = annotations[1].metadata
        assert len(metadata) == 1, metadata
        pattern = metadata[0].pattern
        assert isinstance(pattern, str), pattern
        from typing import Annotated

        C = Annotated[str, pydantic.Field(pattern=pattern)]
        pydantic.create_model("C", __base__=(pydantic.RootModel[C],))


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
    assert isinstance(e.root["ENODEV"], pydantic.BaseModel)

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

    with pytest.raises(ValidationError):
        A.model_validate({"X_5": {1: 2}})

    o = O.model_validate({"O_5": {1: 2}})
    assert isinstance(o, pydantic.BaseModel)

    with pytest.raises(ValidationError):
        O.model_validate({"X_5": {1: 2}})


def test_schema_discriminated_union(with_schema_discriminated_union):
    api = OpenAPI("/", with_schema_discriminated_union)


def test_schema_discriminated_union_discriminator_name(with_schema_discriminated_union_discriminator_name):
    api = OpenAPI("/", with_schema_discriminated_union_discriminator_name)


def test_schema_discriminated_union_invalid_array(with_schema_discriminated_union_invalid_array):
    with pytest.raises(aiopenapi3.errors.SpecError):
        api = OpenAPI("/", with_schema_discriminated_union_invalid_array)


def test_schema_discriminated_union_warnings(with_schema_discriminated_union_warning, openapi_version):
    from aiopenapi3.errors import DiscriminatorWarning

    with (
        pytest.warns(
            DiscriminatorWarning,
            match=r"Discriminated Union member key property enum mismatches property mapping \S+ \!= \S+",
        ),
        pytest.warns(DiscriminatorWarning, match=r"Discriminated Union member \S+ without const/enum key property \S+"),
    ):
        api = OpenAPI("/", with_schema_discriminated_union_warning)

    if (openapi_version.major, openapi_version.minor, openapi_version.patch) >= (3, 1, 0):
        s = copy.deepcopy(with_schema_discriminated_union_warning)
        del s["components"]["schemas"]["B"]["properties"]["object_type"]["enum"]
        s["components"]["schemas"]["B"]["properties"]["object_type"]["enum"] = ["f"]
        s["components"]["schemas"]["A"]["properties"]["object_type"]["enum"] = ["a"]
        s["components"]["schemas"]["C"]["properties"]["object_type"]["const"] = "c"
        with pytest.warns(
            DiscriminatorWarning,
            match=r"Discriminated Union member key property enum mismatches property mapping \S+ \!= \S+",
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

    Nullable = api.components.schemas["Nullable"]
    Nullable.model("a")
    Nullable.model(None)
    with pytest.raises(ValidationError):
        Nullable.model("c")

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


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
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


@pytest.mark.parametrize(
    "schema, input, output, okay",
    [
        ("object", None, None, True),
        ("object", {"attr": "a"}, {"attr": "a"}, True),
        ("object", {"attr": None}, {"attr": None}, True),
        ("object", {}, {}, False),
        ("integer", None, None, True),
        ("integer", 1, 1, True),
        ("boolean", None, None, True),
        ("boolean", True, True, True),
        ("string", None, None, True),
        ("string", "a", "a", True),
        ("array", None, None, True),
        ("array", [], [], True),
        ("array", [None], [None], True),
        ("union", 1, 1, True),
        ("union", "a", "a", True),
        ("union", None, None, True),
        ("multi", 1, 1, True),
        ("multi", "a", "a", True),
        ("multi", None, None, True),
        ("null", None, None, True),
    ],
)
def test_schema_nullable(with_schema_nullable, schema, input, output, okay):
    api = OpenAPI("/", with_schema_nullable)  # , plugins=[NullableRefs()])

    if schema in ("multi", "null") and not api.openapi.startswith("3.1"):
        pytest.skip("version")

    m = api.components.schemas[schema]
    t = m.get_type()
    if okay:
        m.model(input)
    else:
        with pytest.raises(ValidationError):
            m.model(input)


def test_schema_oneOf(with_schema_oneOf):
    api = OpenAPI("/", with_schema_oneOf)
    al = api.components.schemas["AL"]
    t = al.get_type()
    m = t.model_validate([{"type": "a", "value": 1}])

    ab = api.components.schemas["AB"]
    t = ab.get_type()
    m = t.model_validate([{"type": "a", "value": 1}])
    m = t.model_validate({"type": "a", "value": 1})
    m = t.model_validate("string")

    with pytest.raises(ValidationError):
        t.model_validate({"type": "a", "value": "a"})

    with pytest.raises(ValidationError):
        t.model_validate([{"type": "a", "value": "a"}])

    with pytest.raises(ValidationError):
        t.model_validate(1)

    with pytest.raises(ValidationError):
        t.model_validate(1.1)

    with pytest.raises(ValidationError):
        t.model_validate(True)


def test_schema_oneOf_nullable(with_schema_oneOf_nullable):
    api = OpenAPI("/", with_schema_oneOf_nullable)

    s = api.components.schemas["object"]
    t = s.get_type()
    n = s.model({"typed": None})
    m = s.model({"typed": "4"})
    assert not isinstance(m, pydantic.RootModel)
    m = s.model({"typed": "5"})
    assert not isinstance(m, pydantic.RootModel)
    with pytest.raises(ValidationError):
        s.model({"typed": "6"})

    s = api.components.schemas["enumed"]
    t = s.get_type()
    s.model("5")
    s.model(None)
    with pytest.raises(ValidationError):
        s.model("4")


def test_schema_oneOf_mixed(with_schema_oneOf_mixed):
    api = OpenAPI("/", with_schema_oneOf_mixed)

    s = api.components.schemas["object"]
    t = s.get_type()
    m = s.model({"typed": 4})
    assert not isinstance(m, pydantic.RootModel)
    m = s.model({"typed": "5"})
    assert not isinstance(m, pydantic.RootModel)
    with pytest.raises(ValidationError):
        s.model({"typed": "6"})


def test_schema_anyOf(with_schema_anyOf):
    api = OpenAPI("/", with_schema_anyOf)
    oa = api.components.schemas["OA"]
    toa = oa.get_type()
    m = toa.model_validate({"type": "a", "value": 1})
    m = toa.model_validate(None)
    with pytest.raises(ValidationError):
        toa.model_validate({"type": "a", "value": 5})

    ob = api.components.schemas["OB"]
    tob = ob.get_type()
    m = tob.model_validate("b")
    m = tob.model_validate(None)
    with pytest.raises(ValidationError):
        tob.model_validate("a")

    ol = api.components.schemas["OL"]
    tol = ol.get_type()
    m = tol.model_validate([{"type": "a", "value": 1}])


def test_schema_type_validators(with_schema_type_validators):
    api = OpenAPI("/", with_schema_type_validators)

    t = (m := api.components.schemas["Integer"]).get_type()
    v = t.model_validate("10")
    with pytest.raises(ValidationError):
        v = t.model_validate("9")

    t = (m := api.components.schemas["Number"]).get_type()
    v = t.model_validate("10.")
    with pytest.raises(ValidationError):
        v = t.model_validate("9.99")

    t = (m := api.components.schemas["String"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        v = t.model_validate("invalid")

    t = (m := api.components.schemas["Any"]).get_type()

    v = t.model_validate("10")
    with pytest.raises(ValidationError):
        v = t.model_validate("9")

    v = t.model_validate("10.")
    with pytest.raises(ValidationError):
        v = t.model_validate("9.99")

    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        v = t.model_validate("invalid")


def test_schema_allof_string(with_schema_allof_string):
    api = OpenAPI("/", with_schema_allof_string)

    t = (m := api.components.schemas["allOfEnum"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        v = t.model_validate("invalid")

    t = (m := api.components.schemas["minLength"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        t.model_validate("_")

    t = (m := api.components.schemas["maxLength"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        t.model_validate("invalid")

    t = (m := api.components.schemas["mixLength"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        t.model_validate("invalid")
    with pytest.raises(ValidationError):
        t.model_validate("_")

    t = (m := api.components.schemas["allOfmixLength"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        t.model_validate("invalid")

    t = (m := api.components.schemas["allOfCombined"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        t.model_validate("invalid")

    t = (m := api.components.schemas["allOfMinMaxLength"]).get_type()
    v = t.model_validate("valid")
    with pytest.raises(ValidationError):
        t.model_validate("invalid")


def test_schema_allof_oneof_combined(with_schema_allof_oneof_combined):
    api = OpenAPI("/", with_schema_allof_oneof_combined)

    t = (m := api.components.schemas["AllOfResponse"]).get_type()
    t.model_validate({"retCode": 0, "data": {"string": ""}})
    with pytest.raises(ValidationError):
        t.model_validate({"retCode": 0, "data": {"a": {"a": "a"}}})
    with pytest.raises(ValidationError):
        t.model_validate({"data": {"a": {"a": "a"}}})
    with pytest.raises(ValidationError):
        t.model_validate({"retCode": 0, "data": 1})

    t = (m := api.components.schemas["ShutdownRequest"]).get_type()
    t.model_validate({"token": "1", "cmd": "shutdown", "data": {"delay": 0}})

    with pytest.raises(ValidationError):
        t.model_validate({"token": 1444, "cmd": "shutdown", "data": {"delay": 0}})
    with pytest.raises(ValidationError):
        t.model_validate({"token": "1", "cmd": "invalid", "data": {"delay": 0}})
    with pytest.raises(ValidationError):
        t.model_validate({"token": "1", "cmd": "shutdown", "data": {"delay": "invalid"}})
