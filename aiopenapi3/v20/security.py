from typing import Optional, Dict, List

from pydantic import Field, RootModel, model_validator

from ..base import ObjectExtended


class SecurityScheme(ObjectExtended):
    """
    Allows the definition of a security scheme that can be used by the operations.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#security-scheme-object
    """

    type: str = Field(...)
    description: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    in_: Optional[str] = Field(default=None, alias="in")

    flow: Optional[str] = Field(default=None)
    authorizationUrl: Optional[str] = Field(default=None)
    tokenUrl: Optional[str] = Field(default=None)
    refreshUrl: Optional[str] = Field(default=None)
    scopes: Dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    def validate_SecurityScheme(cls, values):
        if values["type"] == "apiKey":
            assert values["name"], "name is required for apiKey"
            assert values["in"] in frozenset(["query", "header"]), "in must be query or header"
        return values


class SecurityRequirement(RootModel):
    """
    Lists the required security schemes to execute this operation.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#security-requirement-object
    """

    root: Dict[str, List[str]]
