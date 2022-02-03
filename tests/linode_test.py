import os
import asyncio

import aiopenapi3.plugin
from aiopenapi3 import OpenAPI
import pytest
import pytest_asyncio


# downloading the description document in the github CI fails due to the cloudflare captcha
noci = pytest.mark.skipif(os.environ.get("GITHUB_ACTIONS", None) is not None, reason="fails on github")


class LinodeDiscriminators(aiopenapi3.plugin.Document):
    def parsed(self, ctx):
        if False:
            ctx.document["paths"]["/tags/{label}"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
                "properties"
            ]["data"]["items"]["properties"]["data"]["discriminator"].update(
                {
                    "mapping": {
                        "linode": "#/components/schemas/Linode",
                        "domain": "#/components/schemas/Domain",
                        "volume": "#/components/schemas/Volume",
                        "nodeBalancer": "#/components/schemas/NodeBalancer",
                    },
                    #            "propertyName":"x-linode-ref-name",
                }
            )

            ctx.document["paths"]["/managed/stats"]["get"]["responses"]["200"]["content"]["application/json"]["schema"][
                "properties"
            ]["data"]["discriminator"].update(
                {
                    "mapping": {
                        "Stats Available": "#/components/schemas/StatsDataAvailable",
                        "Stats Unavailable": "#/components/schemas/StatsDataUnavailable",
                    }
                }
            )

        ctx.document["components"]["schemas"]["PaymentMethod"] = {
            "type": "object",
            "oneOf": [
                {"$ref": "#/components/schemas/CreditCardData"},
                {"$ref": "#/components/schemas/GooglePayData"},
                {"$ref": "#/components/schemas/PayPalData"},
            ],
            "discriminator": {
                "mapping": {
                    "credit_card": "#/components/schemas/CreditCardData",
                    "google_pay": "#/components/schemas/GooglePayData",
                    "paypal": "#/components/schemas/PayPalData",
                },
                "propertyName": "type",
            },
        }
        ctx.document["paths"]["/account/payment-methods"]["post"]["requestBody"]["content"]["application/json"][
            "schema"
        ]["properties"]["is_default"]["$ref"] = "#/components/schemas/CreditCardData/properties/is_default"

        for i in ["CreditCardData", "PayPalData", "GooglePayData"]:

            ctx.document["components"]["schemas"][i]["properties"]["type"] = {
                "type": "string",
                "default": "paypal",
            }

            ctx.document["components"]["schemas"][i]["properties"]["is_default"] = {
                "type": "boolean",
            }

        return ctx


@pytest_asyncio.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def api():
    from aiopenapi3.loader import NullLoader, YAMLCompatibilityLoader

    return await OpenAPI.load_async(
        "https://www.linode.com/docs/api/openapi.yaml",
        loader=NullLoader(YAMLCompatibilityLoader),
        plugins=[LinodeDiscriminators()],
    )


@pytest.mark.asyncio
@noci
async def test_linode_components_schemas(api):
    for name, schema in api.components.schemas.items():
        schema.get_type().construct()

    pay = api.components.schemas["PayPalData"].get_type()(email="a@b.de", paypal_id="1")
    data = pay.json()
    pay_ = api.components.schemas["PaymentMethod"].get_type().parse_raw(data)
    assert pay == pay_.__root__


@pytest.mark.asyncio
@noci
async def test_linode_return_values(api):
    for i in api._:
        call = getattr(api._, i)
        try:
            a = call.return_value()
        except KeyError:
            pass
        else:
            a.get_type().construct()
