import re

from pydantic import Field, model_validator

from ..base import ObjectExtended


class ServerVariable(ObjectExtended):
    """
    4.6 Server Variable Object
    An object representing a Server Variable for server URL template substitution.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#server-variable-object
    """

    enum: list[str] | None = Field(default=None)
    default: str
    description: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_ServerVariable(self):
        assert isinstance(self.enum, (list, None.__class__))
        # default value must be in enum
        assert self.default is None or self.default in (self.enum or [self.default])
        return self


class Server(ObjectExtended):
    """
    4.5 Server Object
    An object representing a Server.

    As described `here`_
    .. _here: https://spec.openapis.org/oas/v3.2.0.html#server-object
    """

    url: str = Field(...)
    description: str | None = Field(default=None)
    name: str | None = Field(default=None)
    variables: dict[str, ServerVariable] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_server_url_parameters(self) -> "Server":
        if (p := frozenset(re.findall(r"\{([^\}]+)\}", self.url))) != (r := frozenset(self.variables.keys())):
            raise ValueError(f"Missing Server Variables {sorted(p - r)} in {self.url}")
        return self

    def validate_parameter_enum(self, parameters: dict[str, str]):
        for name, value in parameters.items():
            if v := self.variables.get(name):
                if v.enum and value not in v.enum:
                    raise ValueError(f"Server Variable {name} value {value} not allowed ({v.enum})")

    def createUrl(self, variables: dict[str, str]) -> str:
        self.validate_parameter_enum(variables)
        vars: dict[str, str | None] = dict(map(lambda x: (x[0], x[1].default), self.variables.items()))
        vars.update(variables)
        url: str = self.url.format(**vars)
        return url
