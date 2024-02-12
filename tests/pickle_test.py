"""
Tests parsing specs
"""

from pathlib import Path
import sys
import pickle
import copy

if sys.version_info >= (3, 9):
    pass
else:
    import pathlib3x as pathlib

import pytest


from aiopenapi3 import OpenAPI

URLBASE = "/"


def test_pickle(with_paths_security_v20, with_schema_oneOf_properties, with_parsing_paths_links):
    """
    Test pickle for
        * Swagger
        * OpenAPI 3
        * OpenAPI 3.1
    """
    for dd in [with_paths_security_v20, with_schema_oneOf_properties, with_parsing_paths_links]:
        api = OpenAPI(URLBASE, dd)
        name = "test"
        p = Path(f"{name}.pickle")

        if dd == with_schema_oneOf_properties:
            A = api.components.schemas["A"].model_construct()
            with p.open("wb") as f:
                pickle.dump(A, f)
            with p.open("rb") as f:
                A_ = pickle.load(f)

        api.cache_store(p)
        OpenAPI.cache_load(p)


def test_unpickle():
    name = "test"
    p = Path(f"{name}.pickle")
    with p.open("rb") as f:
        A_ = pickle.load(f)


def test_copy(petstore_expanded):
    api_ = OpenAPI(URLBASE, petstore_expanded)
    api = copy.copy(api_)
    assert api != api_
    assert id(api_._security) != id(api._security)
