import os
import shlex

import pytest

from aiopenapi3.cli import main


def test_validate_cli():
    with pytest.raises(TypeError):
        main(shlex.split("validate tests/fixtures/schema-yaml-tags-invalid.yaml"))

    main(shlex.split("-v validate -Y -l tests/fixtures/schema-yaml-tags-invalid.yaml"))

    main(shlex.split("-v validate -D tag:yaml.org,2002:timestamp -l tests/fixtures/schema-yaml-tags-invalid.yaml"))


def test_convert_cli():
    main(shlex.split("-v convert --format json -Y -l tests/fixtures/schema-yaml-tags-invalid.yaml /dev/null"))


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
    main(shlex.split("--tracemalloc validate tests/fixtures/petstore-expanded.yaml"))
