import pytest
import os
from yaml import safe_load
import dataclasses

import aiopenapi3
from aiopenapi3 import OpenAPI

LOADED_FILES = {}
URLBASE = "/"


@pytest.fixture(autouse=True)
def skip_env(request):
    if request.node.get_closest_marker("skip_env"):
        m = set(request.node.get_closest_marker("skip_env").args) & set(os.environ.keys())
        if m:
            pytest.skip(f"skipped due to env : {sorted(m)}")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "skip_env(env): skip test if the environment variable is set",
    )


@dataclasses.dataclass
class _Version:
    major: int
    minor: int
    patch: int

    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    def __repr__(self):
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def schema(self):
        return getattr(getattr(aiopenapi3, f"v{self.major}{self.minor}"), "Schema")


@pytest.fixture(scope="session", params=[_Version(3, 0, 3), _Version(3, 1, 0)])
def openapi_version(request):
    return request.param


def _get_parsed_yaml(filename):
    """
    Returns a python dict that is a parsed yaml file from the tests/fixtures
    directory.

    :param filename: The filename to load.  Must exist in tests/fixtures and
                     include extension.
    :type filename: str
    """
    if filename not in LOADED_FILES:
        with open("tests/fixtures/" + filename) as f:
            raw = f.read()
        parsed = safe_load(raw)

        LOADED_FILES[filename] = parsed

    return LOADED_FILES[filename]


@pytest.fixture
def petstore_expanded():
    """
    Provides the petstore-expanded.yaml spec
    """
    yield _get_parsed_yaml("petstore-expanded.yaml")


@pytest.fixture
def broken():
    """
    Provides the parsed yaml for a broken spec
    """
    yield _get_parsed_yaml("broken.yaml")


@pytest.fixture
def broken_reference():
    """
    Provides the parsed yaml for a spec with a broken reference
    """
    yield _get_parsed_yaml("broken-ref.yaml")


def has_bad_parameter_name():
    """
    Provides the parsed yaml for a spec with a bad parameter name
    """
    yield _get_parsed_yaml("bad-parameter-name.yaml")


@pytest.fixture
def dupe_op_id():
    """
    A spec with a duplicate operation ID
    """
    yield _get_parsed_yaml("dupe-operation-ids.yaml")


@pytest.fixture
def parameter_with_underscores():
    """
    A valid spec with underscores in a path parameter
    """
    yield _get_parsed_yaml("parameter-with-underscores.yaml")


@pytest.fixture
def obj_example_expanded():
    """
    Provides the obj-example.yaml spec
    """
    yield _get_parsed_yaml("obj-example.yaml")


@pytest.fixture
def float_validation_expanded():
    """
    Provides the float-validation.yaml spec
    """
    yield _get_parsed_yaml("float-validation.yaml")


@pytest.fixture
def has_bad_parameter_name():
    """
    Provides a spec with a bad parameter name
    """
    yield _get_parsed_yaml("bad-parameter-name.yaml")


@pytest.fixture
def with_links():
    """
    Provides a spec with links defined
    """
    yield _get_parsed_yaml("with-links.yaml")


@pytest.fixture
def with_broken_links():
    """
    Provides a spec with broken links defined
    """
    yield _get_parsed_yaml("with-broken-links.yaml")


@pytest.fixture
def with_securityparameters():
    """
    Provides a spec with security parameters
    """
    yield _get_parsed_yaml("with-securityparameters.yaml")


@pytest.fixture
def with_parameters():
    """
    Provides a spec with parameters
    """
    yield _get_parsed_yaml("with-parameters.yaml")


@pytest.fixture
def with_parameter_format():
    """
    parameters formatting
    """
    yield _get_parsed_yaml("with-parameter-format.yaml")


@pytest.fixture
def with_parameter_format_v20():
    """
    parameters formatting
    """
    yield _get_parsed_yaml("with-parameter-format-v20.yaml")


@pytest.fixture
def with_parameter_missing():
    yield _get_parsed_yaml("with-parameter-missing.yaml")


@pytest.fixture
def with_callback():
    """
    Provides a spec with callback
    """
    yield _get_parsed_yaml("callback-example.yaml")


@pytest.fixture
def with_swagger():
    yield _get_parsed_yaml("swagger-example.yaml")


@pytest.fixture
def with_allof_discriminator():
    yield _get_parsed_yaml("with-allof-discriminator.yaml")


@pytest.fixture
def with_enum():
    yield _get_parsed_yaml("with-enum.yaml")


@pytest.fixture
def with_anyOf_properties():
    yield _get_parsed_yaml("with-anyOf-properties.yaml")


@pytest.fixture
def with_schema_recursion():
    yield _get_parsed_yaml("with-schema-recursion.yaml")


@pytest.fixture
def with_array():
    yield _get_parsed_yaml("with-array.yaml")


@pytest.fixture
def with_schema_Of_parent_properties():
    yield _get_parsed_yaml("with-schema-Of-parent-properties.yaml")


@pytest.fixture
def with_schema_additionalProperties():
    yield _get_parsed_yaml("with-schema-additionalProperties.yaml")


@pytest.fixture
def with_schema_empty():
    yield _get_parsed_yaml("with-schema-empty.yaml")


@pytest.fixture
def with_schema_additionalProperties_v20():
    yield _get_parsed_yaml("with-schema-additionalProperties-v20.yaml")
