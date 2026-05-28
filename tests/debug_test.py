import pytest
import httpx2

import aiopenapi3.debug
from aiopenapi3 import OpenAPI, ResponseSchemaError


def test_debug_log(httpx2_mock, petstore_expanded):
    httpx2_mock.add_response(headers={"Content-Type": "application/json"}, json={"foo": 1})

    def debug_session_factory(*args, **kwargs) -> httpx2.Client:
        s = httpx2.Client(*args, event_hooks=aiopenapi3.debug.httpx_debug_event_hooks(), **kwargs)
        return s

    api = OpenAPI("test.yaml", petstore_expanded, session_factory=debug_session_factory)

    with pytest.raises(ResponseSchemaError) as r:
        p = api._.find_pet_by_id(data={}, parameters={"id": 1})


@pytest.mark.asyncio(loop_scope="session")
async def test_debug_log_async(httpx2_mock, petstore_expanded):
    httpx2_mock.add_response(headers={"Content-Type": "application/json"}, json={"foo": 1})

    def debug_session_factory(*args, **kwargs) -> httpx2.AsyncClient:
        s = httpx2.AsyncClient(*args, event_hooks=aiopenapi3.debug.httpx_debug_event_hooks_async(), **kwargs)
        return s

    api = OpenAPI("test.yaml", petstore_expanded, session_factory=debug_session_factory)

    with pytest.raises(ResponseSchemaError) as r:
        p = await api._.find_pet_by_id(data={}, parameters={"id": 1})


def test_debug_dump(petstore_expanded):
    api = OpenAPI(
        "test.yaml", petstore_expanded, plugins=[aiopenapi3.debug.DescriptionDocumentDumper("debug-test.yaml")]
    )
