import shlex

import pytest

from aiopenapi3.cli import main


def test_cli():
    with pytest.raises(TypeError):
        main(shlex.split("tests/fixtures/with-broken-tags.yaml"))

    main(shlex.split("-C -l -v tests/fixtures/with-broken-tags.yaml"))

    main(shlex.split("-D tag:yaml.org,2002:timestamp -l -v tests/fixtures/with-broken-tags.yaml"))
