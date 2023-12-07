from typing import List, Optional, Dict
import re

from pydantic import Field, model_validator

from ..base import ObjectExtended


class ServerVariable(ObjectExtended):
    """
    A ServerVariable object as defined `here`_.

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#server-variable-object
    """

    enum: Optional[List[str]] = Field(default=None)
    default: Optional[str] = Field(...)
    description: Optional[str] = Field(default=None)

    @model_validator(mode="after")
    def validate_ServerVariable(cls, s: "ServerVariable"):
        assert isinstance(s.enum, (list, None.__class__))
        # default value must be in enum
        assert s.default in (s.enum or [s.default])
        return s


class Server(ObjectExtended):
    """
    The Server object, as described `here`_

    .. _here: https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#server-object
    """

    url: str = Field(...)
    description: Optional[str] = Field(default=None)
    variables: Dict[str, ServerVariable] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_server_url_parameters(self) -> "Server":
        if (p := frozenset(re.findall(r"\{([^\}]+)\}", self.url))) != (r := frozenset(self.variables.keys())):
            raise ValueError(f"Missing Server Variables {sorted(p-r)} in {self.url}")
        return self

    def validate_parameter_enum(self, parameters: Dict[str, str]):
        for name, value in parameters.items():
            if v := self.variables.get(name):
                if value not in v.enum:
                    raise ValueError(f"Server Variable {name} value {value} not allowed ({v.enum})")

    def createUrl(self, variables: Dict[str, str]) -> str:
        self.validate_parameter_enum(variables)
        vars: Dict[str, str] = dict(map(lambda x: (x[0], x[1].default), self.variables.items()))
        vars.update(variables)
        url: str = self.url.format(**vars)
        return url
