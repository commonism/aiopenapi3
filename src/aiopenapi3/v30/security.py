from typing import Union, Annotated, Literal
from pydantic import Field, RootModel, constr

from ..base import ObjectExtended


class OAuthFlow(ObjectExtended):
    """
    Configuration details for a supported OAuth Flow

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#oauth-flow-object
    """

    authorizationUrl: str | None = Field(default=None)
    tokenUrl: str | None = Field(default=None)
    refreshUrl: str | None = Field(default=None)
    scopes: dict[str, str] = Field(default_factory=dict)


class OAuthFlows(ObjectExtended):
    """
    Allows configuration of the supported OAuth Flows.

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#oauth-flows-object
    """

    implicit: OAuthFlow | None = Field(default=None)
    password: OAuthFlow | None = Field(default=None)
    clientCredentials: OAuthFlow | None = Field(default=None)
    authorizationCode: OAuthFlow | None = Field(default=None)


class _SecuritySchemes:
    class _SecurityScheme(ObjectExtended):
        type: Literal["apiKey", "http", "oauth2", "openIdConnect"]
        description: str | None = Field(default=None)

        def validate_authentication_value(self, value):
            pass

    class apiKey(_SecurityScheme):
        type: Literal["apiKey"]
        in_: str = Field(alias="in")
        name: str

    class http(_SecurityScheme):
        type: Literal["http"]
        scheme_: constr(to_lower=True) = Field(default=None, alias="scheme")  # type: ignore[valid-type]
        bearerFormat: str | None = Field(default=None)

    class oauth2(_SecurityScheme):
        type: Literal["oauth2"]
        flows: OAuthFlows

    class openIdConnect(_SecurityScheme):
        type: Literal["openIdConnect"]
        openIdConnectUrl: str


class SecurityScheme(
    RootModel[
        Annotated[
            Union[
                _SecuritySchemes.apiKey, _SecuritySchemes.http, _SecuritySchemes.oauth2, _SecuritySchemes.openIdConnect
            ],
            Field(discriminator="type"),
        ]
    ]
):
    """
    A `Security Scheme`_ defines a security scheme that can be used by the operations.

    .. _Security Scheme: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#security-scheme-object
    """

    pass


class SecurityRequirement(RootModel[dict[str, list[str]]]):
    """
    A `SecurityRequirement`_ object describes security schemes for API access.

    .. _SecurityRequirement: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#security-requirement-object
    """

    pass
