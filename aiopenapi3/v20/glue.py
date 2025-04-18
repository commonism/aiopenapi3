import typing
from typing import Union, cast, Optional
from collections.abc import Sequence
import json
import sys

if sys.version_info >= (3, 10):
    from typing import TypeGuard
else:
    from typing_extensions import TypeGuard


import httpx
import pydantic

from ..base import SchemaBase, ParameterBase, ReferenceBase
from ..request import RequestBase, AsyncRequestBase
from ..errors import HTTPStatusError, ContentTypeError, ResponseSchemaError, ResponseDecodingError, HeadersMissingError


from .parameter import Parameter
from .root import Root

try:
    import httpx_auth
except ImportError:
    httpx_auth = None

if typing.TYPE_CHECKING:
    from .._types import (
        ParameterType,
        ReferenceType,
        RequestParameters,
        RequestData,
        ResponseHeadersType,
        ResponseDataType,
        HeaderType,
    )
    from .schemas import Schema
    from .general import Reference
    from .paths import Response as v20ResponseType


def in_body(x: Union["Parameter", "Reference"]) -> TypeGuard["Parameter"]:
    if isinstance(x, Parameter):
        return x.in_ == "body"
    return in_body(x._target)


def in_not_body(x: Union["Parameter", "Reference"]) -> TypeGuard["Parameter"]:
    if isinstance(x, Parameter):
        return x.in_ != "body"
    return in_not_body(x._target)


class Request(RequestBase):
    root: Root

    @property
    def security(self):
        return self.api._security

    @property
    def _data_parameter(self) -> "Parameter":
        for i in filter(in_body, self.operation.parameters):
            return i
        raise ValueError("body")

    @property
    def data(self) -> Optional["Schema"]:
        try:
            return self._data_parameter.schema_
        except ValueError:
            return None

    @property
    def parameters(self) -> list["Parameter"]:
        return list(filter(in_not_body, self.operation.parameters + self.root.paths[self.path].parameters))

    def args(self, content_type: str = "application/json"):
        op = self.operation
        parameters = op.parameters + self.root.paths[self.path].parameters
        if op.requestBody and op.requestBody.content and (media := op.requestBody.content[content_type]):
            schema = media.schema_
        else:
            schema = None
        return {"parameters": parameters, "data": schema}

    def return_value(self, http_status: int = 200, content_type: str = "application/json") -> Optional["Schema"]:
        try:
            return self.operation.responses[str(http_status)].schema_
        except KeyError:
            return None

    def _prepare_security(self):
        security = self.operation.security if self.operation.security is not None else self.api._root.security

        if not security:
            return

        if not self.security:
            if any([{} == i.root for i in security]):
                return
            else:
                options = " or ".join(
                    sorted(map(lambda x: f"{{{x}}}", [" and ".join(sorted(i.root.keys())) for i in security]))
                )
                raise ValueError(f"No security requirement provided (accepts {options})")

        for s in security:
            if frozenset(s.root.keys()) - frozenset(self.security.keys()):
                continue
            for scheme, _ in s.root.items():
                value = self.security[scheme]
                self._prepare_secschemes(scheme, value)
            break
        else:
            options = " or ".join(
                sorted(map(lambda x: f"{{{x}}}", [" and ".join(sorted(i.root.keys())) for i in security]))
            )
            raise ValueError(
                f"No security requirement satisfied (accepts {options} given {{{' and '.join(sorted(self.security.keys()))}}})"
            )

    def _prepare_secschemes(self, scheme: str, value: Union[str, Sequence[str]]) -> None:
        if httpx_auth is not None:
            self._prepare_secschemes_extra(scheme, value)
        else:
            self._prepare_secschemes_default(scheme, value)

    def _prepare_secschemes_default(self, scheme: str, value: Union[str, Sequence[str]]) -> None:
        assert scheme in self.root.securityDefinitions and self.root.securityDefinitions[scheme] is not None
        ss = self.root.securityDefinitions[scheme].root

        if ss.type == "basic":
            value = cast(list[str], value)
            self.req.auth = httpx.BasicAuth(*value)

        value = cast(str, value)
        if ss.type == "apiKey":
            if ss.in_ == "query":
                # apiKey in query parameter
                self.req.params[ss.name] = value

            if ss.in_ == "header":
                # apiKey in query header data
                self.req.headers[ss.name] = value

    def _prepare_secschemes_extra(self, scheme: str, value: Union[str, Sequence[str]]) -> None:
        assert scheme in self.root.securityDefinitions and self.root.securityDefinitions[scheme] is not None
        ss = self.root.securityDefinitions[scheme].root

        if ss.type == "basic":
            value = cast(list[str], value)
            self.req.auth = httpx_auth.Basic(*value)

        value = cast(str, value)
        if ss.type == "apiKey":
            if ss.in_ == "query":
                # apiKey in query parameter
                self.req.auth = httpx_auth.QueryApiKey(value, ss.name)

            if ss.in_ == "header":
                # apiKey in query header data
                self.req.auth = httpx_auth.HeaderApiKey(value, ss.name)

    def _prepare_parameters(self, provided: Optional["RequestParameters"]):
        provided = provided or dict()
        possible = {_.name: _ for _ in self.operation.parameters + self.root.paths[self.path].parameters}

        parameters = {i.name: i.default for i in filter(lambda x: x.default is not None, possible.values())}
        parameters.update(provided)

        available = frozenset(parameters.keys())
        accepted = frozenset(possible.keys())
        required = frozenset(
            map(lambda x: x[0], filter(lambda y: y[1].required and y[1].in_ != "body", possible.items()))
        )
        if available - accepted:
            raise ValueError(f"Parameter {sorted(available - accepted)} unknown (accepted {sorted(accepted)})")
        if required - available:
            raise ValueError(
                f"Required Parameter {sorted(required - available)} missing (provided {sorted(available)})"
            )

        path_parameters = {}

        for name, value in parameters.items():
            spec = possible[name]

            values = spec._encode(name, value)
            assert isinstance(values, dict)

            if spec.in_ == "formData":
                if "multipart/form-data" in self.operation.consumes:
                    if spec.type == "file":
                        self.req.files.update(values)
                    else:
                        self.req.data.update(values)
                elif "application/x-www-form-urlencoded" in self.operation.consumes:
                    self.req.data.update(values)
                else:
                    raise ValueError(f"operation does not consume form data but parameter {name} is formData")

            if spec.in_ == "path":
                # The string method `format` is incapable of partial updates,
                # as such we need to collect all the path parameters before
                # applying them to the format string.
                path_parameters.update(values)

            if spec.in_ == "query":
                self.req.params.update(values)

            if spec.in_ == "header":
                self.req.headers.update(values)

        self.req.url = self.req.url.format(**path_parameters)

    def _prepare_body(self, data: Optional["RequestData"]):
        try:
            required = self._data_parameter.required
        except ValueError:
            return

        if data is None and required:
            raise ValueError("Request Body is required but none was provided.")

        consumes = frozenset(self.operation.consumes or self.root.consumes)
        if "application/json" in consumes:
            if isinstance(data, (dict, list)):
                pass
            elif isinstance(data, pydantic.BaseModel):
                data = data.model_dump(mode="json")
            else:
                raise TypeError(data)
            data = self.api.plugins.message.marshalled(
                request=self, operationId=self.operation.operationId, marshalled=data
            ).marshalled
            data = json.dumps(data)
            data = data.encode()
            data = self.api.plugins.message.sending(
                request=self, operationId=self.operation.operationId, sending=data
            ).sending
            self.req.content = data
            self.req.headers["Content-Type"] = "application/json"
        else:
            raise NotImplementedError(f"unsupported mime types {consumes}")

    def _prepare(self, data: Optional["RequestData"], parameters: Optional["RequestParameters"]):
        self._prepare_security()
        self._prepare_parameters(parameters)
        self._prepare_body(data)

    def _process__status_code(self, result: httpx.Response, status_code: str) -> "v20ResponseType":
        # find the response model in spec we received
        expected_response = None
        if status_code in self.operation.responses:
            expected_response = self.operation.responses[status_code]
        elif "default" in self.operation.responses:
            expected_response = self.operation.responses["default"]

        if expected_response is None:
            options = ",".join(self.operation.responses.keys())
            raise HTTPStatusError(
                self.operation,
                result.status_code,
                f"""Unexpected response {result.status_code} from {self.operation.operationId} (expected one of {options}), no default is defined""",
                result,
            )
        return expected_response

    def _process__headers(
        self, result: httpx.Response, headers: dict[str, str], expected_response: "v20ResponseType"
    ) -> "ResponseHeadersType":
        rheaders = dict()
        if expected_response.headers:
            required = dict(map(lambda x: (x[0].lower(), x[1]), expected_response.headers.items()))
            """
            Swagger 2.0 does not have optional header - all defined headers are required
            https://github.com/OAI/OpenAPI-Specification/blob/main/versions/2.0.md#header-object
            """
            available = frozenset(result.headers.keys())
            if missing := (required.keys() - available):
                report: dict[str, "HeaderType"] = {k: required[k] for k in missing}
                raise HeadersMissingError(self.operation, report, result)
            for name, header in expected_response.headers.items():
                data = headers.get(name, None)
                if data:
                    rheaders[name] = header._schema.model(header._decode(data))
        return rheaders

    def _process_stream(self, result: httpx.Response) -> tuple["ResponseHeadersType", Optional["Schema"]]:
        status_code = str(result.status_code)
        expected_response = self._process__status_code(result, status_code)
        headers = self._process__headers(result, result.headers, expected_response)
        return headers, expected_response.schema_

    def _process_request(self, result: httpx.Response) -> tuple["ResponseHeadersType", "ResponseDataType"]:
        rheaders: "ResponseHeadersType"
        # spec enforces these are strings
        status_code = str(result.status_code)
        content_type = result.headers.get("Content-Type", None)

        ctx = self.api.plugins.message.received(
            request=self,
            operationId=self.operation.operationId,
            received=result.content,
            headers=result.headers,
            status_code=status_code,
            content_type=content_type,
        )
        status_code = ctx.status_code
        content_type = ctx.content_type
        headers = ctx.headers

        expected_response = self._process__status_code(result, status_code)

        rheaders = self._process__headers(result, headers, expected_response)

        if expected_response.schema_ is None:
            """Swagger treats no schema as a response without a body."""
            return rheaders, None

        if status_code == "204":
            return rheaders, None

        if content_type and content_type.lower().partition(";")[0] == "application/json":
            data = ctx.received.decode()
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                raise ResponseDecodingError(self.operation, data, result)

            data = self.api.plugins.message.parsed(
                request=self,
                operationId=self.operation.operationId,
                parsed=data,
                expected_type=getattr(expected_response.schema_, "_target", expected_response.schema_),
            ).parsed

            if expected_response.schema_ is None:
                raise ResponseSchemaError(self.operation, expected_response, None, result, None)

            try:
                data = expected_response.schema_.model(data)
            except pydantic.ValidationError as e:
                raise ResponseSchemaError(self.operation, expected_response, expected_response.schema_, result, e)

            data = self.api.plugins.message.unmarshalled(
                request=self, operationId=self.operation.operationId, unmarshalled=data
            ).unmarshalled

            self._raise_on_http_status(int(status_code), rheaders, data)

            return rheaders, data
        elif self.operation.produces and content_type in self.operation.produces:
            self._raise_on_http_status(result.status_code, rheaders, ctx.received)
            return rheaders, ctx.received
        else:
            raise ContentTypeError(
                self.operation,
                content_type,
                f"Unexpected Content-Type {content_type} returned for operation {self.operation.operationId} (expected application/json)",
                result,
            )


class AsyncRequest(Request, AsyncRequestBase):
    def _prepare_secschemes(self, scheme: str, value: Union[str, Sequence[str]]):
        """
        httpx_auth does not support async yet
        https://github.com/Colin-b/httpx_auth/pull/48
        """
        return self._prepare_secschemes_default(scheme, value)
