import aiopenapi3.plugin
import yaml
from pathlib import Path
import json


class DescriptionDocumentDumper(aiopenapi3.plugin.Document):
    def __init__(self, path):
        super().__init__()
        self.path = Path(path)

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        if self.path.suffix in [".yaml", ".yml"]:
            with self.path.open("wt") as f:
                yaml.safe_dump(ctx.document, f)
        elif self.path.suffix == ".json":
            self.path.write_text(json.dumps(ctx.document))
        return ctx


def log_request(request):
    print(f"Request event hook: {request.method} {request.url} - Waiting for response")
    for k, v in request.headers.items():
        print(f"{k}:{v}")


async def log_request_async(request):
    log_request(request)


def log_response(response):
    request = response.request
    print(f"Response event hook: {request.method} {request.url} - Status {response.status_code}")
    data = request.read()
    if data:
        print(json.dumps(json.loads(data.decode()), indent=4))


async def log_response_async(response):
    log_response(response)


def httpx_debug_event_hooks():
    return {"request": [log_request], "response": [log_response]}


def httpx_debug_event_hooks_async():
    return {"request": [log_request_async], "response": [log_response_async]}
