from pathlib import Path

from typing import Optional, Union, Annotated, Literal
from pydantic import Field, RootModel, constr

from ..base import ObjectExtended


class OAuthFlow(ObjectExtended):
    """
    Configuration details for a supported OAuth Flow

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#oauth-flow-object
    """

    authorizationUrl: Optional[str] = Field(default=None)
    tokenUrl: Optional[str] = Field(default=None)
    refreshUrl: Optional[str] = Field(default=None)
    scopes: dict[str, str] = Field(default_factory=dict)


class OAuthFlows(ObjectExtended):
    """
    Allows configuration of the supported OAuth Flows.

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#oauth-flows-object
    """

    implicit: Optional[OAuthFlow] = Field(default=None)
    password: Optional[OAuthFlow] = Field(default=None)
    clientCredentials: Optional[OAuthFlow] = Field(default=None)
    authorizationCode: Optional[OAuthFlow] = Field(default=None)


class _SecuritySchemes:
    class _SecurityScheme(ObjectExtended):
        type: Literal["apiKey", "http", "mutualTLS", "oauth2", "openIdConnect"]
        description: Optional[str] = Field(default=None)

        def validate_authentication_value(self, value):
            pass

    class apiKey(_SecurityScheme):
        type: Literal["apiKey"]
        in_: str = Field(alias="in")
        name: str

    class http(_SecurityScheme):
        type: Literal["http"]
        scheme_: constr(to_lower=True) = Field(default=None, alias="scheme")  # type: ignore[valid-type]
        bearerFormat: Optional[str] = Field(default=None)

    class mutualTLS(_SecurityScheme):
        type: Literal["mutualTLS"]

        def validate_authentication_value(self, value) -> None:
            if not isinstance(value, (list, tuple)):
                raise TypeError(type(value))
            if len(value) != 2:
                raise ValueError(f"Invalid number of tuple parameters {len(value)} - 2 required")
            files: tuple[Path, Path] = (Path(value[0]), Path(value[1]))
            if missing := sorted(filter(lambda x: not (x.exists() and x.is_file()), files)):
                raise FileNotFoundError(missing)

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
                _SecuritySchemes.apiKey,
                _SecuritySchemes.http,
                _SecuritySchemes.mutualTLS,
                _SecuritySchemes.oauth2,
                _SecuritySchemes.openIdConnect,
            ],
            Field(discriminator="type"),
        ]
    ]
):
    """
    A `Security Scheme`_ defines a security scheme that can be used by the operations.

    .. _Security Scheme: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#security-scheme-object
    """

    pass


class SecurityRequirement(RootModel[dict[str, list[str]]]):
    """
    A `SecurityRequirement`_ object describes security schemes for API access.

    .. _SecurityRequirement: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#securityRequirementObject
    """

    pass
