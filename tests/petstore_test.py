import httpx
import pytest

from aiopenapi3 import OpenAPI
from aiopenapi3.plugin import Document, Message

from pydantic import ValidationError


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
    ApiResponse = {"description": "successful operation", "schema": {"$ref": "#/definitions/ApiResponse"}}
    PetResponse = {"description": "successful operation", "schema": {"$ref": "#/definitions/Pet"}}

    def parsed(self, ctx):
        for name, path in ctx.document["paths"].items():
            for method, action in path.items():
                if "default" not in action["responses"]:
                    action["responses"]["default"] = OnDocument.ApiResponse

        ctx.document["paths"]["/pet"]["post"]["responses"]["200"] = OnDocument.PetResponse
        ctx.document["paths"]["/pet"]["put"]["responses"]["200"] = OnDocument.PetResponse

        ctx.document["paths"]["/user"]["post"]["responses"]["200"] = OnDocument.ApiResponse
        ctx.document["paths"]["/pet/{petId}"]["get"]["responses"]["404"] = OnDocument.ApiResponse
        return ctx


class OnMessage(Message):
    def parsed(self, ctx):
        def goodPet(i):
            if not isinstance(i.get("photoUrls", None), list):
                i["photoUrls"] = list()
            for idx, j in enumerate(i["photoUrls"]):
                if not isinstance(j, str):
                    i["photoUrls"][idx] = "<invalid>"

            if i.get("status", None) not in frozenset(["available", "pending", "sold"]):
                i["status"] = "pending"

        if ctx.operationId == "getPetById":
            goodPet(ctx.parsed)

        if ctx.operationId in frozenset(["findPetsByStatus", "findPetsByTags"]):
            for i in ctx.parsed:
                goodPet(i)
        return ctx


@pytest.fixture(scope="session")
def api():
    url = "https://petstore.swagger.io:443/v2/swagger.json"
    api = OpenAPI.load_sync(url, plugins=[OnDocument(), OnMessage()], session_factory=session_factory)
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
    api.authenticate(petstore_auth="")


def test_oauth(api):
    api.authenticate(petstore_auth="test")
    d = api._root.definitions
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


def test_pets(api, login):
    d = api._root.definitions

    ApiResponse = d["ApiResponse"].get_type()
    Pet = api._.addPet.data.get_type()
    # addPet
    fido = Pet(
        name="fido",
        status="available",
        category=d["Category"].get_type()(id=101, name="dogz"),
        photoUrls=["http://fido.jpg"],
        tags=[d["Tag"].get_type()(id=102, name="friendly")],
    )
    fido = api._.addPet(data=fido)

    # updatePet
    fido.name = "fodi"
    r = api._.updatePet(data=fido)
    assert isinstance(r, Pet)

    fido.category = "involid"
    r = api._.updatePet(data=fido)
    assert (
        isinstance(r, ApiResponse) and r.code == 500 and r.type == "unknown" and r.message == "something bad happened"
    )

    # uploadFile
    with open("tests/data/dog.png", "rb") as f:
        r = api._.uploadFile(
            parameters={
                "petId": fido.id,
                "additionalMetadata": "yes",
                "file": ("test.png", f, "image/png"),
            }
        )
    assert (
        isinstance(r, ApiResponse)
        and r.code == 200
        and r.type == "unknown"
        and r.message == "additionalMetadata: yes\nFile uploaded to ./test.png, 5783 bytes"
    )

    # getPetById
    r = api._.getPetById(parameters={"petId": fido.id})
    assert isinstance(r, Pet)
    r = api._.getPetById(parameters={"petId": -1})
    assert isinstance(r, ApiResponse) and r.code == 1 and r.type == "error" and r.message == "Pet not found"

    # findPetsByStatus
    r = api._.findPetsByStatus(parameters={"status": ["available", "pending"]})
    assert len(r) > 0

    # findPetsByTags
    r = api._.findPetsByTags(parameters={"tags": ["friendly"]})
    assert len(r) > 0

    r = api._.findPetsByTags(parameters={"tags": ["unknown"]})
    assert len(r) == 0

    # deletePet
    r = api._.findPetsByStatus(parameters={"status": ["available", "pending", "sold"]})
    for i, pet in enumerate(r):
        try:
            api._.deletePet(parameters={"petId": pet.id})
        except Exception:
            pass
        if i > 3:
            break

    with pytest.raises(ValidationError):
        """
        we do not patch updatePet, therefore this will raise during validation

        E   pydantic.error_wrappers.ValidationError: 1 validation error for Pet
        E   status
        E     unexpected value; permitted: 'available', 'pending', 'sold' (type=value_error.const; given=invalid; permitted=('available', 'pending', 'sold'))
        """
        f = Pet(
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
        api._.updatePet(data=f)

    # findPetsByStatus is patched
    r = api._.findPetsByStatus(parameters={"status": ["invalid"]})
    assert all([i.status == "pending" for i in r])


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
