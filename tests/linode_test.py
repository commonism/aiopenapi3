import aiopenapi3.plugin
from aiopenapi3 import OpenAPI
import pytest
import pytest_asyncio


class LinodeDiscriminators(aiopenapi3.plugin.Document):
    def parsed(self, ctx):
        if True:
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
        if "paths" in ctx.document:
            ctx.document["paths"]["/account/payment-methods"]["post"]["requestBody"]["content"]["application/json"][
                "schema"
            ]["properties"]["is_default"]["$ref"] = "#/components/schemas/CreditCardData/properties/is_default"

        for k, v in ctx.document["components"]["schemas"]["PaymentMethod"]["discriminator"]["mapping"].items():
            n = v.split("/")[-1]
            ctx.document["components"]["schemas"][n]["properties"]["type"] = {
                "type": "string",
                "default": k,
            }

            ctx.document["components"]["schemas"][n]["properties"]["is_default"] = {
                "type": "boolean",
            }

        return ctx


@pytest_asyncio.fixture(scope="session")
async def api():
    from aiopenapi3.loader import NullLoader, YAMLCompatibilityLoader

    with pytest.warns(aiopenapi3.errors.DiscriminatorWarning):
        return await OpenAPI.load_async(
            "https://www.linode.com/docs/api/openapi.yaml",
            loader=NullLoader(YAMLCompatibilityLoader),
            plugins=[LinodeDiscriminators()],
            use_operation_tags=False,
        )


from typing import ForwardRef


@pytest.mark.asyncio
@pytest.mark.skip_env("GITHUB_ACTIONS")
async def test_linode_components_schemas(api):
    for name, schema in api.components.schemas.items():
        t = schema.set_type()
        u = schema.get_type()
        assert t == u
        assert not isinstance(t, ForwardRef)
        t.model_construct({})

    pay = api.components.schemas["PayPalData"].get_type()(email="a@b.de", paypal_id="1")
    data = pay.model_dump_json()
    pay_ = api.components.schemas["PaymentMethod"].get_type().model_validate_json(data)
    assert id(pay.__class__) != id(pay_.root.__class__)


@pytest.mark.asyncio
@pytest.mark.skip_env("GITHUB_ACTIONS")
async def test_linode_return_values(api):
    for i in api._:
        call = getattr(api._, i)
        try:
            a = call.return_value()
        except KeyError:
            pass
        else:
            a.get_type().model_construct({})
