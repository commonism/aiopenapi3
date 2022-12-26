"""
Tests parsing specs
"""
import sys
import uuid

import yaml

if sys.version_info >= (3, 9):
    pass
else:
    import pathlib3x as pathlib

import pytest

from pydantic import ValidationError
from aiopenapi3 import OpenAPI, SpecError, ReferenceResolutionError, FileSystemLoader

URLBASE = "/"


def test_parse_from_yaml(petstore_expanded):
    """
    Tests that we can parse a valid yaml file
    """
    spec = OpenAPI(URLBASE, petstore_expanded)


def test_parsing_paths_invalid(with_parsing_paths_invalid):
    """
    Tests that broken specs fail to parse
    """
    with pytest.raises(ValidationError) as e:
        spec = OpenAPI(URLBASE, with_parsing_paths_invalid)


def test_parsing_paths_response_ref_invalid(with_parsing_paths_response_ref_invalid):
    """
    Tests that parsing fails correctly when a reference is broken
    """
    with pytest.raises(ReferenceResolutionError):
        spec = OpenAPI(URLBASE, with_parsing_paths_response_ref_invalid)


def test_parsing_wrong_parameter_name(with_parsing_paths_parameter_name_mismatch):
    """
    Tests that parsing fails if parameter name for path parameters aren't
    actually in the path.
    """
    with pytest.raises(SpecError, match="Parameter name not found in path: different"):
        spec = OpenAPI(URLBASE, with_parsing_paths_parameter_name_mismatch)


def test_parsing_paths_operationid_duplicate(with_parsing_paths_operationid_duplicate):
    """
    Tests that duplicate operation Ids are an error
    """
    with pytest.raises(SpecError, match="Duplicate operationId dupe"):
        spec = OpenAPI(URLBASE, with_parsing_paths_operationid_duplicate)


def test_parsing_path_parameter_name_with_underscores(with_parsing_path_parameter_name_with_underscores):
    """
    Tests that path parameters with underscores in them are accepted
    """
    spec = OpenAPI(URLBASE, with_parsing_path_parameter_name_with_underscores)


def test_parsing_paths_content_schema_object(with_parsing_paths_content_schema_object):
    """
    Tests that `example` exists.
    """
    spec = OpenAPI(URLBASE, with_parsing_paths_content_schema_object)
    schema = spec.paths["/check-dict"].get.responses["200"].content["application/json"].schema_
    assert isinstance(schema.example, dict)
    assert isinstance(schema.example["real"], float)

    schema = spec.paths["/check-str"].get.responses["200"].content["text/plain"]
    assert isinstance(schema.example, str)


def test_parsing_paths_content_schema_float_validation(with_parsing_paths_content_schema_float_validation):
    """
    Tests that `minimum` and similar validators work with floats.
    """
    spec = OpenAPI(URLBASE, with_parsing_paths_content_schema_float_validation)
    properties = spec.paths["/foo"].get.responses["200"].content["application/json"].schema_.properties

    assert isinstance(properties["integer"].minimum, int)
    assert isinstance(properties["integer"].maximum, int)
    assert isinstance(properties["real"].minimum, float)
    assert isinstance(properties["real"].maximum, float)


def test_parsing_with_links(with_parsing_paths_links):
    """
    Tests that "links" parses correctly
    """
    spec = OpenAPI(URLBASE, with_parsing_paths_links)

    assert "exampleWithOperationRef" in spec.components.links
    assert spec.components.links["exampleWithOperationRef"].operationRef == "/with-links"

    response_a = spec.paths["/with-links"].get.responses["200"]
    assert "exampleWithOperationId" in response_a.links
    assert response_a.links["exampleWithOperationId"].operationId == "withLinksTwo"

    response_b = spec.paths["/with-links-two/{param}"].get.responses["200"]
    assert "exampleWithRef" in response_b.links
    assert response_b.links["exampleWithRef"]._target == spec.components.links["exampleWithOperationRef"]


def test_parsing_paths_links_invalid(with_parsing_paths_links_invalid):
    """
    Tests that broken "links" values error properly
    """
    with pytest.raises(ValidationError) as e:
        spec = OpenAPI(URLBASE, with_parsing_paths_links_invalid)

    assert all(
        [
            i in str(e.value)
            for i in [
                "operationId and operationRef are mutually exclusive, only one of them is allowed",
                "operationId and operationRef are mutually exclusive, one of them must be specified",
            ]
        ]
    )


def test_securityparameters(with_paths_security):
    OpenAPI(URLBASE, with_paths_security)


def test_callback(with_paths_callback):
    OpenAPI(URLBASE, with_paths_callback)


def test_schema_paths_extended(api_version):
    DOC = f"""{api_version}
info:
  title: ''
  version: 0.0.0
paths:
    x-codegen-contextRoot: /apis/registry/v2
"""
    api = OpenAPI.loads("test.yaml", DOC)
    print(api)


def test_schema_allof_discriminator(with_schema_allof_discriminator):
    api = OpenAPI(URLBASE, with_schema_allof_discriminator)

    schema = api.components.schemas["Object1"]
    type_ = schema.get_type()
    obj1 = type_.construct(
        type="obj1",
        subtypeProperties=schema.properties["subtypeProperties"].get_type().construct(property1a="1a", property1b="1b"),
        id=uuid.uuid4(),
    )
    data = obj1.json()
    obj1_ = api.components.schemas["ObjectBaseType"].get_type().parse_raw(data)


def test_schema_enum(openapi_version, with_schema_enum):
    import copy
    import json

    data = copy.deepcopy(with_schema_enum)  # .deepcopy()

    import linode_test

    data["openapi"] = str(openapi_version)
    api = OpenAPI.loads(URLBASE, json.dumps(data), plugins=[linode_test.LinodeDiscriminators()])
    import datetime

    s = api.components.schemas["PaymentMethod"]
    t = s.get_type()
    pay = t(__root__=dict(created=datetime.datetime.now(), id=5, is_default=True, type="google_pay", data=None))
    data = pay.json()
    pay_ = t.parse_raw(data)
    assert pay == pay_

    pay = t(__root__=dict(created=datetime.datetime.now(), id=5, is_default=True, type="google_pay", data=None))

    with pytest.raises(ValidationError):
        pay = t(__root__=dict(created=datetime.datetime.now(), id=5, is_default=True, type="no_pay", data=None))

    pp = api.components.schemas["PayPalData"].get_type()(email="a@b.de", paypal_id="1")
    assert pp.dict()["type"] == "paypal"


def test_parsing_properties_empty_name(with_parsing_schema_properties_name_empty):
    with pytest.raises(ValueError, match=r"empty property name"):
        OpenAPI("/", with_parsing_schema_properties_name_empty)


def test_schema_array(with_schema_array):
    api = OpenAPI(URLBASE, with_schema_array)


def test_parsing_paths_content_nested_array_ref(openapi_version, with_parsing_paths_content_nested_array_ref):
    import aiopenapi3.v30.general
    import aiopenapi3.v31.general

    expected = {0: aiopenapi3.v30.general.Reference, 1: aiopenapi3.v31.general.Reference}[openapi_version.minor]

    OpenAPI("/", with_parsing_paths_content_nested_array_ref)


def test_parsing_schema_names(with_parsing_schema_names):
    OpenAPI("/", with_parsing_schema_names)
