from pathlib import Path

import httpx
import pytest

from aiopenapi3 import OpenAPI
from aiopenapi3.loader import FileSystemLoader
from aiopenapi3.extra import Reduced


class PetStoreReduced(Reduced):
    def __init__(self):
        super().__init__({"/user/{username}": None})


class MSGraphReduced(Reduced):
    def __init__(self):
        super().__init__(
            {
                "/me/sendMail": None,
                "/me/mailFolders": None,
            }
        )


@pytest.mark.skip_env("GITHUB_ACTIONS")
def test_reduced_msgraph():
    from aiopenapi3.extra import Reduced

    api = OpenAPI.load_file(
        "/api.json",
        "data/ms-graph-openapi.json",
        session_factory=httpx.Client,
        loader=FileSystemLoader(Path("tests/").absolute()),
        plugins=[MSGraphReduced()],
    )


@pytest.mark.skip_env("GITHUB_ACTIONS")
def test_reduced_small():
    from aiopenapi3.extra import Reduced

    api = OpenAPI.load_file(
        "/",
        "data/petstorev3-openapi.yaml",
        session_factory=httpx.Client,
        loader=FileSystemLoader(Path("tests/").absolute()),
        plugins=[PetStoreReduced()],
    )
    return


def test_reduced(with_schema_reduced, httpx_mock):
    api = OpenAPI.load_file(
        "http://127.0.0.1/api.yaml",
        with_schema_reduced,
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
        with_schema_reduced,
        session_factory=httpx.Client,
        plugins=[Reduced({"/A/{Path}": None})],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )

    assert "/A/{Path}" in api.paths.paths
    assert "A" in api.components.parameters
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
        with_schema_reduced,
        session_factory=httpx.Client,
        plugins=[Reduced({"/B": None})],
        loader=FileSystemLoader(Path("tests/fixtures")),
    )
    assert "/A/{Path}" not in api.paths.paths
    assert "A" not in api.components.parameters
    assert "A" not in api.components.schemas
    assert "A" not in api.components.responses
    assert "A" not in api.components.requestBodies
