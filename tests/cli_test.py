import os
import shlex
from pathlib import Path
import json

import pytest

from aiopenapi3.cli import main
import aiopenapi3.log

import pydantic


def test_validate_cli():
    main(shlex.split("-v validate tests/fixtures/schema-yaml12-tags.yaml"))


def test_convert_cli():
    main(shlex.split("-v convert --format json tests/fixtures/schema-yaml12-tags.yaml /dev/null"))


def test_profile():
    main(shlex.split("--profile validate tests/fixtures/petstore-expanded.yaml"))


def test_plugins():
    main(
        shlex.split(
            "-L tests/fixtures -P tests/plugin_test.py:OnInit,OnDocument,OnMessage --tracemalloc -v validate plugin-base.yaml"
        )
    )


def test_tracemalloc():
    main(shlex.split("--tracemalloc validate tests/fixtures/petstore-expanded.yaml"))


def test_logging():
    os.environ["AIOPENAPI3_LOGGING_HANDLERS"] = "console"
    aiopenapi3.log.handlers = None
    main(shlex.split("validate tests/fixtures/petstore-expanded.yaml"))

    aiopenapi3.log.handlers = None
    aiopenapi3.log.init(True)


def test_call():
    cache = Path("tests/data/cache.pickle")
    if cache.exists():
        cache.unlink()

    main(
        shlex.split(
            """-C tests/data/cache.pickle -P tests/petstore_test.py:OnDocument call https://petstore.swagger.io/v2/swagger.json --method post /user --authenticate '{"api_key":"special-key"}' --data '{"id":1, "username": "bozo", "firstName": "Bozo", "lastName": "Smith", "email": "bozo@email.com", "password": "letmemin", "phone": "111-222-333", "userStatus": 3 }' """
        )
    )

    auth = Path("tests/data/auth.json")
    auth.write_text(json.dumps({"petstore_auth": "test"}))

    main(
        shlex.split(
            """-C tests/data/cache.pickle -P tests/petstore_test.py:OnDocument call https://petstore.swagger.io/v2/swagger.json findPetsByStatus --parameters '{"status": ["available", "pending"]}' --authenticate @tests/data/auth.json --format "[? name=='doggie' && status == 'available'].{name:name, photo:photoUrls} | [0:2]" """
        )
    )
    main(
        shlex.split(
            """-P tests/petstore_test.py:OnDocument call https://petstore.swagger.io/v2/swagger.json findPetsByStatus --parameters '{"status": ["available", "pending"]}' --authenticate '{"petstore_auth":"test"}' --format "[? name=='doggie' && status == 'available'].{name:name, photo:photoUrls} | [0:2]" """
        )
    )
    auth.unlink()
