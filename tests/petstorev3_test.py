import random

import httpx
import pytest

from aiopenapi3 import OpenAPI, ResponseSchemaError
from aiopenapi3.plugin import Document, Message
from aiopenapi3.v20 import Reference


from pydantic import ValidationError

try:
    import httpx_auth
except:
    httpx_auth = None


def log_request(request):
    print(f"Request event hook: {request.method} {request.url} - Waiting for response")


def log_response(response):
    request = response.request
    print(f"Response event hook: {request.method} {request.url} - Status {response.status_code}")


def session_factory(*args, **kwargs) -> httpx.Client:
    if False:
        kwargs["event_hooks"] = {"request": [log_request], "response": [log_response]}
    return httpx.Client(*args, verify=False, **kwargs)


class OnDocument(Document):
    ApiResponse = {
        "description": "",
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ApiResponse"}}},
    }
    PetResponse = {"description": "", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}}}

    def parsed(self, ctx):
        for name, path in ctx.document["paths"].items():
            for method, action in path.items():
                if "default" not in action["responses"]:
                    action["responses"]["default"] = OnDocument.ApiResponse

        ctx.document["paths"]["/pet"]["post"]["responses"]["200"] = OnDocument.PetResponse
        ctx.document["paths"]["/pet"]["put"]["responses"]["200"] = OnDocument.PetResponse

        ctx.document["paths"]["/user"]["post"]["responses"]["200"] = OnDocument.ApiResponse
        ctx.document["paths"]["/pet/{petId}"]["get"]["responses"]["404"] = OnDocument.ApiResponse
        ctx.document["paths"]["/pet/{petId}/uploadImage"]["post"]["responses"]["200"] = OnDocument.PetResponse
        del ctx.document["paths"]["/user/login"]["get"]["responses"]["200"]["headers"]["X-Expires-After"]["schema"][
            "format"
        ]
        return ctx


class OnMessage(Message):
    def received(self, ctx: "Message.Context") -> "Message.Context":
        if ctx.operationId == "loginUser":
            ctx.received = b'"' + ctx.received + b'"'
        if ctx.operationId == "getPetById" and ctx.status_code == "404":
            import json

            ctx.received = json.dumps(dict(code=1, type="error", message=ctx.received.decode())).encode()
        return ctx

    def parsed(self, ctx):
        def goodPet(i):
            if i.get("name", None) is None:
                i["name"] = "default"
            if not isinstance(i.get("photoUrls", None), list):
                i["photoUrls"] = list()
            for idx, j in enumerate(i["photoUrls"]):
                if not isinstance(j, str):
                    i["photoUrls"][idx] = "<invalid>"

            if i.get("status", None) not in frozenset(["available", "pending", "sold"]):
                i["status"] = "pending"

            if (c := i.get("category", None)) is None or not isinstance(c, dict):
                i["category"] = dict(id=0, name="default")

            if (c := i.get("tags", None)) is None or not isinstance(c, list):
                i["tags"] = []
            else:
                for t in c:
                    if not isinstance(t, dict) or not set(t.keys()) == frozenset(["id", "name"]):
                        i["tags"] = []
                        break

        Pet = self.api.resolve_jr(self.api._root, None, Reference(**{"$ref": "#/components/schemas/Pet"}))

        if ctx.operationId == "getPetById":
            if Pet == ctx.expected_type:
                goodPet(ctx.parsed)

        if ctx.operationId in frozenset(["findPetsByStatus", "findPetsByTags"]):
            if Pet == getattr(ctx.expected_type.items, "_target", None):
                for i in ctx.parsed:
                    goodPet(i)

        return ctx


@pytest.fixture(scope="session")
def api():
    #    url = "https://petstore.swagger.io:443/v2/swagger.json"
    #    plugins=[OnDocument(), OnMessage()]
    url = "https://petstore3.swagger.io/api/v3/openapi.json"
    plugins = [OnDocument(), OnMessage()]
    api = OpenAPI.load_sync(url, plugins=plugins, session_factory=session_factory, use_operation_tags=False)
    api.authenticate(api_key="special-key")
    return api


@pytest.fixture
def user(api):
    user = api._.createUser.data.get_type()(
        id=1,
        username="bozo",
        firstName="Bozo",
        lastName="Smith",
        email="bozo@clown.com",
        password="letmein",
        phone="111-222-3333",
        userStatus=3,
    )
    r = api._.createUser(data=user)
    return user


@pytest.fixture
def login(api, user):
    api.authenticate(petstore_auth={})


@pytest.mark.skipif(httpx_auth, reason="oauth does not work")
def test_oauth(api):
    """requires *working* oauth"""
    api.authenticate(petstore_auth={})
    d = api._root.components.schemas
    #    category = api._.addPet.data.
    fido = api._.addPet.data.get_type()(
        id=99,
        name="fido",
        status="available",
        category=d["Category"].get_type()(id=101, name="dogz"),
        photoUrls=["http://fido.jpg"],
        tags=[d["Tag"].get_type()(id=102, name="friendly")],
    )
    result = api._.addPet(data=fido)
    print(result)


def test_user(api, user):
    r = api._.loginUser(parameters={"username": user.username, "password": user.password})


@pytest.mark.xfail
@pytest.mark.skipif(httpx_auth, reason="oauth does not work")
def test_pets(api, login):
    """requires *working* oauth or no oauth"""
    d = api.components.schemas

    ApiResponse = d["ApiResponse"].get_type()
    Pet = api._.addPet.data.get_type()
    # addPet
    fido = Pet(
        id=15,
        name="doggie",
        status="available",
        category=d["Category"].get_type()(id=1, name="Dogs"),
        photoUrls=["http://fido.jpg"],
        tags=[d["Tag"].get_type()(id=0, name="string")],
    )
    data = fido.model_dump()
    fido = api._.addPet(data=fido)
    assert isinstance(fido, Pet), fido.message

    # updatePet
    fido.name = "fodi"
    r = api._.updatePet(data=fido)
    assert isinstance(r, Pet)

    #    fido.category = "involid"
    #    r = api._.updatePet(data=fido)
    #    assert (
    #        isinstance(r, ApiResponse) and r.code == 500 and r.type == "unknown" and r.message == "something bad happened"
    #    )

    # uploadFile
    with open("tests/data/dog.png", "rb") as f:
        r = api._.uploadFile(
            parameters={
                "petId": fido.id,
                "additionalMetadata": "yes",
            },
            data=("test.png", f, "image/png"),
        )
    assert isinstance(r, Pet)

    # getPetById
    r = api._.getPetById(parameters={"petId": fido.id})
    assert isinstance(r, Pet)
    for i in range(100):
        r = api._.getPetById(parameters={"petId": random.randint(-1_000_000_000, 1_000_000_000)})
        if isinstance(r, ApiResponse):
            assert isinstance(r, ApiResponse) and r.code == 1 and r.type == "error" and r.message == "Pet not found"
            break
        elif isinstance(r, Pet):
            pass

    # findPetsByStatus
    r = api._.findPetsByStatus(parameters={"status": ["available", "pending"]})
    assert (isinstance(r, list) and len(r) >= 0) or isinstance(r, ApiResponse)

    # findPetsByTags
    r = api._.findPetsByTags(parameters={"tags": ["friendly"]})
    assert (isinstance(r, list) and len(r) >= 0) or isinstance(r, ApiResponse)

    r = api._.findPetsByTags(parameters={"tags": ["unknown"]})
    assert isinstance(r, list) or isinstance(r, ApiResponse)

    # deletePet
    r = api._.findPetsByStatus(parameters={"status": ["available", "pending", "sold"]})
    for i, pet in enumerate(r):
        try:
            api._.deletePet(parameters={"petId": pet.id})
        except Exception:
            pass
        if i > 3:
            break

    with pytest.raises(ResponseSchemaError):
        """
        we do not patch updatePet, therefore this will raise during validation

        E   pydantic.error_wrappers.ValidationError: 1 validation error for Pet
        E   status
        E     unexpected value; permitted: 'available', 'pending', 'sold' (type=value_error.const; given=invalid; permitted=('available', 'pending', 'sold'))
        """
        f = Pet(
            id=0,
            name="foffy",
            status="available",
            category=d["Category"].get_type()(id=101, name="dogz"),
            photoUrls=["http://fido.jpg"],
            tags=[d["Tag"].get_type()(id=103, name="buggy")],
        )
        f = api._.addPet(data=f)
        assert isinstance(f, Pet)
        #        assert f.id != fido.id

        f.status = "invalid"
        r = api._.updatePet(data=f)
        print(r)

    # findPetsByStatus is patched
    r = api._.findPetsByStatus(parameters={"status": ["available"]})
    assert all([i.status == "available" for i in r])


def test_store(api):
    # getInventory
    r = api._.getInventory()

    # placeOrder
    order = api._.placeOrder.data.get_type()(petId=99, quantity=1, status="placed")
    o = api._.placeOrder(data=order)
    print(o)

    # getOrderById
    o = api._.getOrderById(parameters={"orderId": o.id})
    print(o)
