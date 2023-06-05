import httpx
import sys

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

import yarl

from aiopenapi3 import FileSystemLoader, OpenAPI
from aiopenapi3.plugin import Init, Message, Document


class OnInit(Init):
    def initialized(self, ctx):
        # this does not change the operationId on the ssi as the ssi is initialized already
        # changing an operationId would be better in OnDocument.parsed
        ctx.initialized.paths["/pets"].get.operationId = "listPets"
        # therefore update the operation index
        self.api._init_operationindex(False)
        return ctx


class OnDocument(Document):
    def __init__(self, url):
        self.url = url
        super().__init__()

    def loaded(self, ctx):
        return ctx

    def parsed(self, ctx):
        if ctx.url.path == self.url:
            ctx.document["components"] = {
                "schemas": {"Pet": {"$ref": "petstore-expanded.yaml#/components/schemas/Pet"}}
            }
            ctx.document["servers"] = [{"url": "/"}]
        elif ctx.url.path == "petstore-expanded.yaml":
            ctx.document["components"]["schemas"]["Pet"]["allOf"].append(
                {
                    "type": "object",
                    "required": ["color"],
                    "properties": {
                        "color": {"type": "string", "default": "blue"},
                        "weight": {"type": "integer", "default": 10},
                    },
                }
            )
        else:
            raise ValueError(f"unexpected url {ctx.url.path} expecting {self.url}")

        return ctx


class OnMessage(Message):
    def marshalled(self, ctx):
        return ctx

    def sending(self, ctx):
        return ctx

    def received(self, ctx):
        ctx.received = """[{"id":1,"name":"theanimal", "weight": null}]"""
        return ctx

    def parsed(self, ctx):
        if ctx.operationId == "listPets":
            if ctx.parsed[0].get("color", None) is None:
                ctx.parsed[0]["color"] = "red"

            if ctx.parsed[0]["id"] == 1:
                ctx.parsed[0]["id"] = 2
        return ctx

    def unmarshalled(self, ctx):
        if ctx.operationId == "listPets":
            if ctx.unmarshalled[0].id == 2:
                ctx.unmarshalled[0].id = 3
        return ctx


def test_Plugins(httpx_mock, with_plugin_base):
    httpx_mock.add_response(headers={"Content-Type": "application/json"}, content=b"[]")
    plugins = [OnInit(), OnDocument("plugin-base.yaml"), OnMessage()]
    api = OpenAPI.loads(
        "plugin-base.yaml",
        with_plugin_base,
        plugins=plugins,
        loader=FileSystemLoader(Path().cwd() / "tests/fixtures"),
        session_factory=httpx.Client,
    )
    api._base_url = yarl.URL("http://127.0.0.1:80")
    r = api._.listPets()
    assert r

    item = r[0]
    assert item.id == 3
    assert item.weight == None  # default does not apply as it it unsed
    assert item.color == "red"  # default does not apply
