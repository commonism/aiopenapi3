import asyncio
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


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
        import yaml
        from aiopenapi3.loader import YAML12Loader

        parsed = yaml.load(raw, Loader=YAML12Loader)

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
def with_paths_parameter_format_complex(openapi_version):
    """
    parameters formatting
    """
    yield _get_parsed_yaml("paths-parameter-format-complex.yaml", openapi_version)


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
def with_schema_yaml12(openapi_version):
    return "schema-yaml12-tags.yaml"


@pytest.fixture
def with_paths_response_header(openapi_version):
    yield _get_parsed_yaml("paths-response-header.yaml", openapi_version)


@pytest.fixture
def with_paths_response_content_type_octet(openapi_version):
    yield _get_parsed_yaml("paths-response-content-type-octet.yaml", openapi_version)


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
def with_schema_discriminated_union(openapi_version):
    yield _get_parsed_yaml("schema-discriminated-union.yaml", openapi_version)


@pytest.fixture
def with_schema_discriminated_union_warning(openapi_version):
    yield _get_parsed_yaml("schema-discriminated-union-warning.yaml", openapi_version)


@pytest.fixture
def with_schema_discriminated_union_merge(openapi_version):
    yield _get_parsed_yaml("schema-discriminated-union-merge.yaml", openapi_version)


@pytest.fixture
def with_schema_discriminated_union_discriminator_name(openapi_version):
    yield _get_parsed_yaml("schema-discriminated-union-discriminator-name.yaml", openapi_version)


@pytest.fixture
def with_schema_discriminated_union_array(openapi_version):
    yield _get_parsed_yaml("schema-discriminated-union-array.yaml", openapi_version)


@pytest.fixture
def with_schema_discriminated_union_deep():
    yield _get_parsed_yaml("schema-discriminated-union-deep.yaml")


@pytest.fixture
def with_schema_create_update_read():
    yield _get_parsed_yaml("schema-create-update-read.yaml")


@pytest.fixture
def with_schema_enum():
    yield _get_parsed_yaml("schema-enum.yaml")


@pytest.fixture
def with_schema_enum_object():
    yield _get_parsed_yaml("schema-enum-object.yaml")


@pytest.fixture
def with_schema_enum_array():
    yield _get_parsed_yaml("schema-enum-array.yaml")


@pytest.fixture
def with_schema_extensions(openapi_version):
    yield _get_parsed_yaml("schema-extensions.yaml", openapi_version)


@pytest.fixture
def with_schema_anyof():
    yield _get_parsed_yaml("schema-anyof.yaml")


@pytest.fixture
def with_schema_recursion(openapi_version):
    yield _get_parsed_yaml("schema-recursion.yaml", openapi_version)


@pytest.fixture
def with_extra_reduced():
    yield "extra-reduced.yaml"


@pytest.fixture
def with_schema_self_recursion(openapi_version):
    yield _get_parsed_yaml("schema-self-recursion.yaml", openapi_version)


@pytest.fixture
def with_schema_type_list():
    yield _get_parsed_yaml("schema-type-list.yaml")


@pytest.fixture
def with_schema_type_missing():
    yield _get_parsed_yaml("schema-type-missing.yaml")


@pytest.fixture
def with_schema_type_string_format_byte_base64():
    yield _get_parsed_yaml("schema-type-string-format-byte-base64.yaml")


@pytest.fixture
def with_schema_array():
    yield _get_parsed_yaml("schema-array.yaml")


@pytest.fixture
def with_schema_Of_parent_properties(openapi_version):
    yield _get_parsed_yaml("schema-Of-parent-properties.yaml", openapi_version)


@pytest.fixture
def with_schema_additionalProperties(openapi_version):
    yield _get_parsed_yaml("schema-additionalProperties.yaml", openapi_version)


@pytest.fixture
def with_schema_patternProperties():
    yield _get_parsed_yaml("schema-patternProperties.yaml")


@pytest.fixture
def with_schema_additionalProperties_v20():
    yield _get_parsed_yaml("schema-additionalProperties-v20.yaml")


@pytest.fixture
def with_schema_additionalProperties_and_named_properties():
    yield _get_parsed_yaml("schema-additionalProperties-and-named-properties" ".yaml")


@pytest.fixture
def with_schema_empty(openapi_version):
    yield _get_parsed_yaml("schema-empty.yaml", openapi_version)


@pytest.fixture
def with_schema_property_name_is_type():
    yield _get_parsed_yaml("schema-property-name-is-type.yaml")


@pytest.fixture
def with_schema_constraints():
    yield _get_parsed_yaml("schema-constraints.yaml")


@pytest.fixture
def with_schema_pathitems(openapi_version):
    yield _get_parsed_yaml("schema-pathitems.yaml")


@pytest.fixture
def with_plugin_base():
    filename = "plugin-base.yaml"
    with (Path("tests/fixtures/") / filename).open("rt") as f:
        raw = f.read()
    return raw


@pytest.fixture
def with_paths_requestbody_formdata_encoding():
    yield _get_parsed_yaml("paths-requestbody-formdata-encoding.yaml")


@pytest.fixture(scope="session")
def with_paths_requestbody_formdata_wtforms():
    yield _get_parsed_yaml("paths-requestbody-formdata-wtforms.yaml")


@pytest.fixture(scope="session")
def with_paths_response_status_pattern_default():
    yield _get_parsed_yaml("paths-response-status-pattern-default.yaml")
