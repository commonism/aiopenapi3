from pathlib import Path

from aiopenapi3 import OpenAPI


def test_clone(petstore_expanded):
    api = OpenAPI("/", petstore_expanded)
    _ = api.clone("/v2")


def test_cache(petstore_expanded):
    api = OpenAPI("/", petstore_expanded)

    p = Path("tests/data/cache-test.pickle")
    api.cache_store(p)
    _ = OpenAPI.cache_load(p)
