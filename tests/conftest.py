import os
import dataclasses
import sys

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from yaml import safe_load
import pytest

import aiopenapi3

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


@dataclasses.dataclass
class _VersionS:
    major: int
    minor: int
    patch: int = 0

    def __str__(self):
        if self.major == 3:
            return f'openapi: "{self.major}.{self.minor}.{self.patch}"'
        else:
            return f'swagger: "{self.major}.{self.minor}"'


@pytest.fixture(scope="session", params=[_VersionS(2, 0), _VersionS(3, 0, 3), _VersionS(3, 1, 0)])
def api_version(request):
    return request.param


def _get_parsed_yaml(filename, version=None):
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

    data = LOADED_FILES[filename]
    if version:
        data["openapi"] = str(version)
    return data


@pytest.fixture
def petstore_expanded(openapi_version):
    """
    Provides the petstore-expanded.yaml spec
    """
    yield _get_parsed_yaml("petstore-expanded.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_invalid(openapi_version):
    """
    Provides the parsed yaml for a broken spec
    """
    yield _get_parsed_yaml("parsing-paths-invalid.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_response_ref_invalid(openapi_version):
    """
    Provides the parsed yaml for a spec with a broken reference
    """
    yield _get_parsed_yaml("parsing-paths-response-ref-invalid.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_operationid_duplicate(openapi_version):
    """
    A spec with a duplicate operation ID
    """
    yield _get_parsed_yaml("parsing-paths-operationid-duplicate.yaml", openapi_version)


@pytest.fixture
def with_parsing_path_parameter_name_with_underscores(openapi_version):
    """
    A valid spec with underscores in a path parameter
    """
    yield _get_parsed_yaml("parsing-paths-parameter-name-with-underscores.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_content_schema_object(openapi_version):
    """
    Provides the parsing-paths-content-schema-object.yaml spec
    """
    yield _get_parsed_yaml("parsing-paths-content-schema-object.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_content_schema_float_validation(openapi_version):
    """
    Provides the parsing-paths-content-schema-float-validation.yaml spec
    """
    yield _get_parsed_yaml("parsing-paths-content-schema-float-validation.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_parameter_name_mismatch(openapi_version):
    """
    Provides a spec with a bad parameter name
    """
    yield _get_parsed_yaml("parsing-paths-parameter-name-mismatch.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_links(openapi_version):
    """
    Provides a spec with links defined
    """
    yield _get_parsed_yaml("parsing-paths-links.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_links_invalid(openapi_version):
    """
    Provides a spec with broken links defined
    """
    yield _get_parsed_yaml("parsing-paths-links-invalid.yaml", openapi_version)


@pytest.fixture
def with_parsing_schema_names(openapi_version):
    yield _get_parsed_yaml("parsing-schema-names.yaml", openapi_version)


@pytest.fixture
def with_paths_security(openapi_version):
    """
    Provides a spec with security parameters
    """
    yield _get_parsed_yaml("paths-security.yaml", openapi_version)


@pytest.fixture
def with_paths_security_v20():
    yield _get_parsed_yaml("paths-security-v20.yaml")


@pytest.fixture
def with_paths_parameters(openapi_version):
    """
    Provides a spec with parameters
    """
    yield _get_parsed_yaml("paths-parameters.yaml", openapi_version)


@pytest.fixture
def with_paths_parameters_invalid(openapi_version):
    """
    Provides a spec with parameters
    """
    yield _get_parsed_yaml("paths-parameter-name-invalid.yaml", openapi_version)


@pytest.fixture
def with_paths_parameter_format(openapi_version):
    """
    parameters formatting
    """
    yield _get_parsed_yaml("paths-parameter-format.yaml", openapi_version)


@pytest.fixture
def with_paths_parameter_format_v20():
    """
    parameters formatting
    """
    yield _get_parsed_yaml("paths-parameter-format-v20.yaml")


@pytest.fixture
def with_paths_parameter_missing(openapi_version):
    yield _get_parsed_yaml("paths-parameter-missing.yaml", openapi_version)


@pytest.fixture
def with_paths_parameter_default(openapi_version):
    yield _get_parsed_yaml("paths-parameter-default.yaml", openapi_version)


@pytest.fixture
def with_parsing_schema_properties_name_empty(openapi_version):
    yield _get_parsed_yaml("parsing-schema-properties-name-empty.yaml", openapi_version)


@pytest.fixture
def with_parsing_paths_content_nested_array_ref(openapi_version):
    yield _get_parsed_yaml("parsing-paths-content-nested-array-ref.yaml", openapi_version)


@pytest.fixture
def with_schema_properties_default(openapi_version):
    yield _get_parsed_yaml("schema-properties-default.yaml", openapi_version)


@pytest.fixture
def with_schema_yaml_tags_invalid(openapi_version):
    return "schema-yaml-tags-invalid.yaml"


@pytest.fixture
def with_paths_response_header(openapi_version):
    yield _get_parsed_yaml("paths-response-header.yaml", openapi_version)


@pytest.fixture
def with_paths_response_header_v20():
    yield _get_parsed_yaml("paths-response-header-v20.yaml")


@pytest.fixture
def with_paths_tags(openapi_version):
    yield _get_parsed_yaml("paths-tags.yaml", openapi_version)


@pytest.fixture
def with_paths_callback(openapi_version):
    """
    Provides a spec with callback
    """
    yield _get_parsed_yaml("paths-callbacks.yaml", openapi_version)


@pytest.fixture
def with_schema_allof_discriminator(openapi_version):
    yield _get_parsed_yaml("schema-allof-discriminator.yaml", openapi_version)


@pytest.fixture
def with_schema_enum(openapi_version):
    yield _get_parsed_yaml("schema-enum.yaml")


@pytest.fixture
def with_schema_anyof(openapi_version):
    yield _get_parsed_yaml("schema-anyof.yaml")


@pytest.fixture
def with_schema_recursion(openapi_version):
    yield _get_parsed_yaml("schema-recursion.yaml")


@pytest.fixture
def with_schema_array(openapi_version):
    yield _get_parsed_yaml("schema-array.yaml")


@pytest.fixture
def with_schema_Of_parent_properties(openapi_version):
    yield _get_parsed_yaml("schema-Of-parent-properties.yaml")


@pytest.fixture
def with_schema_additionalProperties(openapi_version):
    yield _get_parsed_yaml("schema-additionalProperties.yaml")


@pytest.fixture
def with_schema_additionalProperties_v20():
    yield _get_parsed_yaml("schema-additionalProperties-v20.yaml")


@pytest.fixture
def with_schema_empty(openapi_version):
    yield _get_parsed_yaml("schema-empty.yaml")


@pytest.fixture
def with_plugin_base():
    filename = "plugin-base.yaml"
    with (Path("tests/fixtures/") / filename).open("rt") as f:
        raw = f.read()
    return raw
