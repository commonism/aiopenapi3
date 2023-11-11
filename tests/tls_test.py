import asyncio
import io
import ssl
from pathlib import Path
import sys

import httpx
import pytest
import pytest_asyncio

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config

import trustme
import cryptography

import aiopenapi3
from aiopenapi3.plugin import Document

from fastapi import FastAPI, Request, Response

app = FastAPI(version="1.0.0", title="TLS tests", servers=[{"url": "/", "description": "Default, relative server"}])


@pytest.fixture(scope="session")
def certs():
    _data = {
        "org": {
            "certs": {
                "server": {"args": ["server.example.org", "localhost"], "kwargs": {"common_name": "localhost"}},
                "client": {"args": ["client@example.org", "localhost"]},
            }
        },
        "com": {
            "certs": {
                "client": {"args": ["client@example.com"], "kwargs": {"common_name": "client.example.com"}},
            }
        },
    }
    for caname, cadata in _data.items():
        root = trustme.CA(organization_name=f"{caname} Root")
        root.cert_pem.write_to_path((cafile := Path(f"tests/data/tls-root-{caname}.pem")))
        cadata["issuer"] = str(cafile)

        ca = trustme.CA(root, organization_name=f"{caname} CA")
        root.cert_pem.write_to_path((cafile := Path(f"tests/data/tls-ca-{caname}.pem")))
        cadata["self"] = str(cafile)

        for cert_, argv in cadata["certs"].items():
            if cert_ in ("root", "ca"):
                continue
            cert = ca.issue_cert(*argv.get("args", {}), **argv.get("kwargs", {}))
            (chainfile := Path(f"tests/data/tls-ca-{caname}-{cert_}-chain.pem")).unlink(missing_ok=True)
            for i in cert.cert_chain_pems:
                i.write_to_path(chainfile, append=True)
            cadata["certs"][cert_]["certfile"] = chainfile
            cert.private_key_pem.write_to_path(keyfile := Path(f"tests/data/tls-ca-{caname}-{cert_}-key.pem"))
            cadata["certs"][cert_]["keyfile"] = keyfile
    return _data


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory, certs):
    class _Config(Config):
        def create_ssl_context(self):
            r = super().create_ssl_context()
            #            r.keylog_filename = "tests/data/tls-server-keylog.txt"
            return r

    c = _Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    c.ca_certs = certs["org"]["issuer"]
    c.certfile = certs["org"]["certs"]["server"]["certfile"]
    c.keyfile = certs["org"]["certs"]["server"]["keyfile"]
    c.verify_mode = ssl.VerifyMode.CERT_OPTIONAL
    return c


@pytest_asyncio.fixture(scope="session")
async def server(event_loop, config):
    policy = asyncio.get_event_loop_policy()
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    try:
        sd = asyncio.Event()
        task = event_loop.create_task(serve(app, config, shutdown_trigger=sd.wait))
        yield config
    finally:
        sd.set()
        await task
    asyncio.set_event_loop_policy(policy)


class MutualTLSSecurity(Document):
    """
    patch FastAPI description document to authenticate using mutualTLS
    """

    def parsed(self, ctx: "Document.Context") -> "Document.Context":
        import yaml

        ctx.document["components"] = yaml.safe_load(
            io.StringIO(
                """
securitySchemes:
    tls:
        type: mutualTLS
"""
            )
        )

        # /tls - mutual tls authentication
        ctx.document["paths"]["/required-tls-authentication"]["get"]["security"] = [{"tls": []}]
        # /optional-tls …
        ctx.document["paths"]["/optional-tls-authentication"]["get"]["security"] = [{"tls": []}, {}]

        return ctx


@pytest_asyncio.fixture(scope="session")
async def client(event_loop, server, certs):
    def self_signed(*args, **kwargs) -> httpx.AsyncClient:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certs["org"]["issuer"])
        if (cert := kwargs.get("cert", None)) is not None:
            ctx.load_cert_chain(certfile=cert[0], keyfile=cert[1])
        return httpx.AsyncClient(*args, verify=ctx, **kwargs)

    api = await aiopenapi3.OpenAPI.load_async(
        f"https://{server.bind[0]}/openapi.json", session_factory=self_signed, plugins=[MutualTLSSecurity()]
    )

    return api


@app.get("/required-tls-authentication", operation_id="required_tls_authentication", response_model=str)
def tls(request: Request, response: Response) -> str:
    assert request.scope["extensions"].get("tls", None) is not None
    tls = request.scope["extensions"]["tls"]
    chain = tls["client_cert_chain"]
    cert = chain[-1]
    x509 = cryptography.x509.load_pem_x509_certificate(cert.encode())
    return x509.subject.rfc4514_string()


@app.get(
    "/optional-tls-authentication",
    operation_id="optional_tls_authentication",
    responses={
        200: {
            "model": str,
        },
        204: {"model": None},
    },
)
def optional_tls(request: Request, response: Response) -> str:
    if (tls := request.scope["extensions"].get("tls", None)) is None:
        response.status_code = 204
        return response

    chain = tls["client_cert_chain"]
    cert = chain[-1]
    x509 = cryptography.x509.load_pem_x509_certificate(cert.encode())
    return x509.subject.rfc4514_string()


@pytest.mark.asyncio
async def test_tls_required(event_loop, server, client, certs):
    with pytest.raises(ValueError, match=r"No security requirement satisfied \(accepts {tls}\)"):
        client.authenticate(None)
        await client._.required_tls_authentication()

    with pytest.raises(aiopenapi3.errors.RequestError):
        client.authenticate(tls=((c := certs["com"]["certs"]["client"])["certfile"], c["keyfile"]))
        await client._.required_tls_authentication()

    client.authenticate(tls=((c := certs["org"]["certs"]["client"])["certfile"], c["keyfile"]))
    l = await client._.required_tls_authentication()
    assert l is not None


@pytest.mark.asyncio
async def test_tls_optional(event_loop, server, client, certs):
    client.authenticate(None)
    l = await client._.optional_tls_authentication()
    assert l is None

    client.authenticate(tls=((c := certs["org"]["certs"]["client"])["certfile"], c["keyfile"]))
    l = await client._.required_tls_authentication()
    assert l is not None

    with pytest.raises(aiopenapi3.errors.RequestError):
        client.authenticate(tls=((c := certs["com"]["certs"]["client"])["certfile"], c["keyfile"]))
        await client._.required_tls_authentication()


@pytest.mark.asyncio
@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires asyncio.to_thread")
async def test_sync(event_loop, server, certs):
    def self_signed_(*args, **kwargs) -> httpx.Client:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certs["org"]["issuer"])
        if (cert := kwargs.get("cert", None)) is not None:
            ctx.load_cert_chain(certfile=cert[0], keyfile=cert[1])
        return httpx.Client(*args, verify=ctx, **kwargs)

    client = await asyncio.to_thread(
        aiopenapi3.OpenAPI.load_sync,
        f"https://{server.bind[0]}/openapi.json",
        plugins=[MutualTLSSecurity()],
        session_factory=self_signed_,
    )

    client.authenticate(None)
    l = await asyncio.to_thread(client._.optional_tls_authentication)
    assert l is None

    client.authenticate(tls=((c := certs["org"]["certs"]["client"])["certfile"], c["keyfile"]))
    l = await asyncio.to_thread(client._.required_tls_authentication)
    assert l is not None


@pytest.mark.asyncio
async def test_certificate_invalid(client):
    with pytest.raises(ValueError, match=r"Invalid parameter for SecurityScheme tls mutualTLS") as e:
        client.authenticate(tls="/tmp")
    assert isinstance(e.value.__context__, TypeError) and e.value.__context__.args == (str,)

    with pytest.raises(ValueError, match=r"Invalid parameter for SecurityScheme tls mutualTLS") as e:
        client.authenticate(tls=("/tmp",))
    assert isinstance(e.value.__context__, ValueError) and e.value.__context__.args == (
        "Invalid number of tuple parameters 1 - 2 required",
    )

    with pytest.raises(ValueError, match=r"Invalid parameter for SecurityScheme tls mutualTLS") as e:
        client.authenticate(tls=(p := ("/does/not/exist", "/tmp")))
    assert isinstance(e.value.__context__, FileNotFoundError) and e.value.__context__.args[0] == sorted(
        map(lambda x: Path(x), p)
    )
