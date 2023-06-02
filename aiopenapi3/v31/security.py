from typing import Optional, Dict, List

from pydantic import Field, model_validator, RootModel, constr

from ..base import ObjectExtended


class OAuthFlow(ObjectExtended):
    """
    Configuration details for a supported OAuth Flow

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#oauth-flow-object
    """

    authorizationUrl: Optional[str] = Field(default=None)
    tokenUrl: Optional[str] = Field(default=None)
    refreshUrl: Optional[str] = Field(default=None)
    scopes: Dict[str, str] = Field(default_factory=dict)


class OAuthFlows(ObjectExtended):
    """
    Allows configuration of the supported OAuth Flows.

    .. here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#oauth-flows-object
    """

    implicit: Optional[OAuthFlow] = Field(default=None)
    password: Optional[OAuthFlow] = Field(default=None)
    clientCredentials: Optional[OAuthFlow] = Field(default=None)
    authorizationCode: Optional[OAuthFlow] = Field(default=None)


class SecurityScheme(ObjectExtended):
    """
    A `Security Scheme`_ defines a security scheme that can be used by the operations.

    .. _Security Scheme: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#security-scheme-object
    """

    type: str = Field(...)
    description: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    in_: Optional[str] = Field(default=None, alias="in")
    scheme_: Optional[constr(to_lower=True)] = Field(default=None, alias="scheme")
    bearerFormat: Optional[str] = Field(default=None)
    flows: Optional[OAuthFlows] = Field(default=None)
    openIdConnectUrl: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_SecurityScheme(cls, s: "SecurityScheme"):
        keys = set(s.model_fields_set)
        keys -= frozenset(["type", "description", "extensions"])
        if s.type == "apikey":
            assert keys == set(["in_", "name"])
        if s.type == "http":
            assert keys - frozenset(["scheme_", "bearerFormat"]) == set([])
        if s.type == "oauth2":
            assert keys == frozenset(["flows"])
        if s.type == "openIdConnect":
            assert keys - frozenset(["openIdConnectUrl"]) == set([])
        return s


class SecurityRequirement(BaseModel):
    """
    A `SecurityRequirement`_ object describes security schemes for API access.

    .. _SecurityRequirement: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#securityRequirementObject
    """

    root: Dict[str, List[str]]

    @root_validator(pre=True)
    @classmethod
    def populate_root(cls, values):
        return {"root": values}

    @model_serializer(mode="wrap")
    def _serialize(self, handler, info):
        data = handler(self)
        if info.mode == "json":
            return data["root"]
        else:
            return data

    @classmethod
    def model_modify_json_schema(cls, json_schema):
        return json_schema["properties"]["root"]
