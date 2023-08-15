import sys

if sys.version_info >= (3, 9):
    from typing import List, Optional, Union, Dict, Annotated, Literal
else:
    from typing import List, Optional, Union, Dict
    from typing_extensions import Annotated, Literal


from pydantic import Field, RootModel

from ..base import ObjectExtended


class _SecuritySchemes:
    class _SecurityScheme(ObjectExtended):
        type: Literal["basic", "apiKey", "oauth2"]
        description: Optional[str] = Field(default=None)

        def validate_authentication_value(self, value):
            pass

    class basic(_SecurityScheme):
        type: Literal["basic"]

    class apiKey(_SecurityScheme):
        type: Literal["apiKey"]
        in_: str = Field(alias="in")
        name: str

    class oauth2(_SecurityScheme):
        type: Literal["oauth2"]
        flow: Literal["implicit", "password", "application", "accessCode"]
        authorizationUrl: str
        tokenUrl: str
        scopes: Dict[str, str]


class SecurityScheme(
    RootModel[
        Annotated[
            Union[
                _SecuritySchemes.basic,
                _SecuritySchemes.apiKey,
                _SecuritySchemes.oauth2,
            ],
            Field(discriminator="type"),
        ]
    ]
):
    """
    Allows the definition of a security scheme that can be used by the operations.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#security-scheme-object
    """

    pass


class SecurityRequirement(RootModel):
    """
    Lists the required security schemes to execute this operation.

    https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#security-requirement-object
    """

    root: Dict[str, List[str]]
