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
def test_reduced():
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
