"""
Tests parsing specs
"""
import sys
import pickle

if sys.version_info >= (3, 9):
    pass
else:
    import pathlib3x as pathlib

import pytest


from aiopenapi3 import OpenAPI

URLBASE = "/"


def test_pickle(with_swagger, with_anyOf_properties, with_links):
    """
    Test pickle for
        * Swagger
        * OpenAPI 3
        * OpenAPI 3.1
    """
    for dd in [with_swagger, with_anyOf_properties, with_links]:
        api = OpenAPI(URLBASE, dd)
        name = "test"

        if dd == with_anyOf_properties:
            A = api.components.schemas["A"].construct()
            with open(f"{name}.pickle", "wb") as f:
                pickle.dump(A, f)
            with open(f"{name}.pickle", "rb") as f:
                A_ = pickle.load(f)

        with open(f"{name}.pickle", "wb") as f:
            pickle.dump(api, f)

        with open(f"{name}.pickle", "rb") as f:
            pickle.load(f)


def test_unpickle():
    name = "test"
    with open(f"{name}.pickle", "rb") as f:
        A_ = pickle.load(f)
    print(A_)
