import sys
import re

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

import httpx
import pytest

from aiopenapi3 import OpenAPI
from aiopenapi3.loader import FileSystemLoader
from aiopenapi3.extra import Cull, Reduce


class PetStoreReduced(Reduce):
    def __init__(self):
        super().__init__({"/user/{username}": None})


class MSGraph:
    def __init__(self):
        super().__init__(
            operations={
                "/me/profile": None,
                re.compile(r"/me/sendMail.*"): None,
            }
        )

    def parsed(self, ctx):
        # Drop massive unnecessary discriminator
        del ctx.document["components"]["schemas"]["microsoft.graph.entity"]["discriminator"]

        # Run standard reduction process
        ctx = super().parsed(ctx)

        # Fix invalids
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

        # Drop requirement for @odata.type since it's not actually required
        for schema in ctx.document["components"]["schemas"].values():
            if "required" in schema:
                schema["required"] = [i for i in schema["required"] if i != "@odata.type"]
                if not schema["required"]:
                    del schema["required"]
            if isinstance(schema, dict):
                for s in schema.get("allOf", []):
                    if "required" in s:
                        s["required"] = [i for i in s["required"] if i != "@odata.type"]
                        if not s["required"]:
                            del s["required"]

        ctx.document.setdefault("security", []).append({"token": []})
        ctx.document.setdefault("components", {}).setdefault("securitySchemes", {}).setdefault(
            "token",
            {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        )

        # Rebuild Tags
        ctx.document["tags"] = [
            {"name": tag}
            for tag in set(
                tag
                for operations in ctx.document.get("paths", {}).values()
                for details in operations.values()
                if isinstance(details, dict)
                for tag in details.get("tags", [])
            )
        ]

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

    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[compressor({"/A/{Path}": None})],
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

    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_extra_reduced,
        session_factory=httpx.Client,
        plugins=[compressor({re.compile("/B"): None})],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )
    assert "/A/{Path}" not in api.paths.paths
    assert "A" not in api.components.parameters
    assert "A" not in api.components.schemas
    assert "A" not in api.components.responses
    assert "A" not in api.components.requestBodies
