import re
import typing

from pathlib import Path

import httpx
import pytest

from aiopenapi3 import OpenAPI
from aiopenapi3.loader import FileSystemLoader

from aiopenapi3.extra import Cull, Reduce

if typing.TYPE_CHECKING:
    from aiopenapi3.plugin import Document


class PetStoreReduced(Reduce):
    def __init__(self):
        super().__init__(("/user/{username}", None))


class MSGraph:
    def __init__(self):
        super().__init__(
            ("/me/profile", None),
            (re.compile(r"/me/sendMail.*"), None),
            "accessReviewDecisions.accessReviewDecision.ListAccessReviewDecision",
            re.compile(r"drives.drive.items.driveItem.permissions.permission*"),
        )

    @staticmethod
    def _remove_parameter(document, path, parameter_name):
        if document["paths"].get(path, {}).get("parameters"):
            document["paths"][path]["parameters"] = [
                p for p in document["paths"][path]["parameters"] if p.get("name", "") != parameter_name
            ]

    @staticmethod
    def _drop_required(schema: dict, requirement: str) -> None:
        if "required" in schema:
            schema["required"] = [i for i in schema["required"] if i != requirement]
            if not schema["required"]:
                del schema["required"]

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        # Drop massive unnecessary discriminator
        del ctx.document["components"]["schemas"]["microsoft.graph.entity"]["discriminator"]
        # Run standard reduction process
        ctx = super().parsed(ctx)
        # Remove superfluous parameters
        self._remove_parameter(ctx.document, "/applications(appId='{appId}')", "uniqueName")
        self._remove_parameter(ctx.document, "/applications(uniqueName='{uniqueName}')", "appId")
        # Fix parameter names
        for operation in ctx.document.get("paths", {}).values():
            for details in operation.values():
                # Check if parameters exist for this operation
                if isinstance(details, dict):
                    parameters = details.get("parameters", [])
                    for parameter in parameters:
                        description = parameter.get("description", "")
                        # Check if description matches the desired format
                        if description.strip() == "Usage: on='{on}'":
                            parameter["name"] = "on"
                        if "content" in parameter.keys():
                            parameter["schema"] = parameter["content"].get("application/json", {}).get("schema", {})
                            del parameter["content"]
        # Drop requirement for @odata.type since it's not actually enforced
        for schema in ctx.document.get("components", {}).get("schemas", {}).values():
            if isinstance(schema, dict):
                self._drop_required(schema, "@odata.type")
                for s in schema.get("allOf", []):
                    self._drop_required(s, "@odata.type")
        return ctx


class MSGraphCulled(MSGraph, Cull):
    pass


class MSGraphReduced(MSGraph, Reduce):
    pass


@pytest.mark.skip_env("GITHUB_ACTIONS")
def test_reduced_msgraph():
    api = OpenAPI.load_file(
        "/api.json",
        "data/ms-graph-openapi.json",
        session_factory=httpx.Client,
        loader=FileSystemLoader(Path("tests/").absolute()),
        plugins=[MSGraphReduced()],
    )


@pytest.mark.skip_env("GITHUB_ACTIONS")
def test_reduced_small():
    api = OpenAPI.load_file(
        "/",
        "data/petstorev3-openapi.yaml",
        session_factory=httpx.Client,
        loader=FileSystemLoader(Path("tests/").absolute()),
        plugins=[PetStoreReduced()],
    )
    return


@pytest.mark.parametrize("compressor", [Reduce, Cull])
def test_reduced(with_extra_reduced, httpx_mock, compressor):
    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )

    assert "/A/{Path}" in api.paths.paths
    assert "A" in api.components.parameters
    assert "A" in api.components.schemas
    assert "A" in api.components.responses
    assert "A" in api.components.requestBodies

    # (str, methods)
    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[compressor(("/A/{Path}", None))],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )

    assert "/A/{Path}" in api.paths.paths
    assert "A" in api.components.parameters
    assert "AA" in api.components.schemas
    assert "A" in api.components.schemas

    assert "A0" in api.components.schemas
    assert "A1" in api.components.schemas
    assert "A" in api.components.responses
    assert "A" in api.components.requestBodies

    httpx_mock.add_response(headers={"Content-Type": "application/json", "X-A": "A"}, json=dict(a=1))

    from aiopenapi3.request import RequestBase

    req: RequestBase = api._.A
    data = req.data.get_type().model_construct(a="a")
    headers, payload = req(data=data, parameters=dict(Path="a"), return_headers=True)
    assert payload.a == 1
    assert headers["X-A"] == "A"

    # (re, methods)
    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[compressor((re.compile("/B"), None))],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )
    assert "/A/{Path}" not in api.paths.paths
    assert "A" not in api.components.parameters
    assert "A" not in api.components.schemas
    assert "A" not in api.components.responses
    assert "A" not in api.components.requestBodies

    # operationId str
    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[compressor("A")],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )
    assert "/A/{Path}" in api.paths.paths
    assert "A" in api.components.parameters
    assert "AA" in api.components.schemas
    assert "A" in api.components.schemas

    assert "A0" in api.components.schemas
    assert "A1" in api.components.schemas
    assert "A" in api.components.responses
    assert "A" in api.components.requestBodies

    # operationId re
    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[compressor(re.compile(r"[A]{1}$"))],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )
    assert "/A/{Path}" in api.paths.paths
    assert "A" in api.components.parameters
    assert "AA" in api.components.schemas
    assert "A" in api.components.schemas

    assert "A0" in api.components.schemas
    assert "A1" in api.components.schemas
    assert "A" in api.components.responses
    assert "A" in api.components.requestBodies


from aiopenapi3.extra import Cookies


@pytest.mark.parametrize("cookie", [dict(policy="jar"), dict(policy="securitySchemes")], ids=["jar", "securityScheme"])
def test_cookies(httpx_mock, with_extra_cookie, cookie):

    api = OpenAPI(
        "http://127.0.0.1/api.yaml",
        with_extra_cookie,
        session_factory=httpx.Client,
        plugins=[Cookies(**cookie)],
    )

    httpx_mock.add_response(
        url="http://127.0.0.1/api/set-cookie",
        headers=[("Set-Cookie", "Session=value"), ("Set-Cookie", "a=b")],
        json='"ok"',
    )
    api._.set_cookie()

    if cookie["policy"] == "jar":
        httpx_mock.add_response(
            url="http://127.0.0.1/api/require-cookie", match_headers={"Cookie": "Session=value; a=b"}, json='"ok"'
        )
    else:
        httpx_mock.add_response(
            url="http://127.0.0.1/api/require-cookie", match_headers={"Cookie": "Session=value"}, json='"ok"'
        )
    api._.require_cookie()

    req = httpx_mock.get_requests()[-1]

    if cookie["policy"] == "securitySchemes":
        assert req.headers.get_list("cookie") == ["Session=value"]


def test_cookies_policy(with_extra_cookie):
    with pytest.raises(ValueError, match="policy … is not a valid policy"):
        Cookies(policy="…")
