import shlex

import pytest

from aiopenapi3.cli import main


def test_validate_cli():
    with pytest.raises(TypeError):
        main(shlex.split("validate tests/fixtures/schema-yaml-tags-invalid.yaml"))

    main(shlex.split("-v validate -Y -l tests/fixtures/schema-yaml-tags-invalid.yaml"))

    main(shlex.split("-v validate -D tag:yaml.org,2002:timestamp -l tests/fixtures/schema-yaml-tags-invalid.yaml"))
