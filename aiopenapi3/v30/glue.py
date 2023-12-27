import io
from typing import List, Union, cast, TYPE_CHECKING, Dict, Optional, cast, Any, Tuple, Sequence
import json
import urllib.parse

import httpx

try:
    import httpx_auth
    from httpx_auth.authentication import SupportMultiAuth
    import inspect
except ImportError:
    httpx_auth = None
else:
    HTTPX_AUTH_METHODS = {
        name.lower(): getattr(httpx_auth, name)
        for name in httpx_auth.__all__
        if inspect.isclass((class_ := getattr(httpx_auth, name)))
        if issubclass(class_, httpx.Auth)
    }

import pydantic

# import pydantic.json

import aiopenapi3.v30.media
from ..base import SchemaBase, ParameterBase
from ..request import RequestBase, AsyncRequestBase
from ..errors import HTTPStatusError, ContentTypeError, ResponseDecodingError, ResponseSchemaError, HeadersMissingError
from .formdata import parameters_from_multipart, parameters_from_urlencoded, encode_multipart_parameters

from .root import Root as v30Root
from ..v31.root import Root as v31Root

if TYPE_CHECKING:
    from .._types import (
        SchemaType,
        RequestParameters,
        RequestData,
        ParameterType,
        RequestFilesParameter,
        RequestFileParameter,
    )

    from .paths import Response as v30Response, MediaType as v30MediaType
    from ..v31.paths import Response as v31Response, MediaType as v31MediaType

    v3xResponseType = Union[v30Response, v31Response]
    v3xMediaTypeType = Union[v30MediaType, v31MediaType]


class Request(RequestBase):
    root: Union[v30Root, v31Root]

    @property
    def security(self):
        return self.api._security

    @property
    def data(self) -> Optional["SchemaType"]:
        if (
            self.operation.requestBody is not None
            and self.operation.requestBody.content is not None
            and (ex := self.operation.requestBody.content.get("application/json", None)) is not None
        ):
            return ex.schema_
        return None

    @property
    def parameters(self) -> List["ParameterType"]:
        return self.operation.parameters + self.root.paths[self.path].parameters

    def args(self, content_type: str = "application/json") -> Dict[str, Any]:
        op = self.operation
        parameters = op.parameters + self.root.paths[self.path].parameters
        if (
            op.requestBody
            and op.requestBody.content
            and (media := op.requestBody.content.get(content_type, None)) is not None
        ):
            schema = media.schema_
        else:
            schema = None
        return {"parameters": parameters, "data": schema}

    def return_value(self, http_status: int = 200, content_type: str = "application/json") -> Optional["SchemaType"]:
        status_key = str(http_status)
        if a := self.operation.responses.get(status_key) or self.operation.responses.get(status_key[0] + "XX"):
            if b := a.content.get(content_type):
                return b.schema_
        return None

    def _prepare_security(self) -> None:
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
                raise ValueError(f"No security requirement satisfied (accepts {options})")

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
                f"No security requirement satisfied (accepts {options} given {{{' and '.join(sorted(self.security.keys()))}}}"
            )

    def _prepare_secschemes(self, scheme: str, value: Union[str, Sequence[str]]) -> None:
        assert (
            self.root.components
            and self.root.components.securitySchemes
            and scheme in self.root.components.securitySchemes
            and self.root.components.securitySchemes[scheme].root
        )
        if httpx_auth is not None:
            self._prepare_secschemes_extra(scheme, value)
        else:
            self._prepare_secschemes_default(scheme, value)

    def _prepare_secschemes_default(self, scheme: str, value: Union[str, Sequence[str]]) -> None:
        assert (
            self.root.components
            and self.root.components.securitySchemes
            and scheme in self.root.components.securitySchemes
            and self.root.components.securitySchemes[scheme].root
        )
        ss = self.root.components.securitySchemes[scheme].root
        from .. import v30, v31

        if ss.type == "http":
            assert isinstance(ss, (v30.security._SecuritySchemes.http, v31.security._SecuritySchemes.http))
            if ss.scheme_ == "basic":
                self.req.auth = httpx.BasicAuth(*value)
            elif ss.scheme_ == "digest":
                self.req.auth = httpx.DigestAuth(*value)
            elif ss.scheme_ == "bearer":
                self.req.headers["Authorization"] = f"Bearer {value:s}"
            else:
                raise ValueError(f"Authentication {ss.type}/{ss.scheme_} is not supported.")

        if ss.type == "mutualTLS":
            self.req.cert = value

        value = cast(str, value)

        if ss.type == "apiKey":
            assert isinstance(ss, (v30.security._SecuritySchemes.apiKey, v31.security._SecuritySchemes.apiKey))
            if ss.in_ == "query":
                # apiKey in query parameter
                self.req.params[ss.name] = value

            if ss.in_ == "header":
                # apiKey in query header data
                self.req.headers[ss.name] = value

            if ss.in_ == "cookie":
                self.req.cookies = {ss.name: value}

    def _prepare_secschemes_extra(self, scheme: str, value: Union[str, Sequence[str]]) -> None:
        assert (
            self.root.components
            and self.root.components.securitySchemes
            and scheme in self.root.components.securitySchemes
            and self.root.components.securitySchemes[scheme].root
        )
        ss = self.root.components.securitySchemes[scheme].root
        auths = []

        from .. import v30, v31

        if ss.type == "oauth2":
            assert isinstance(ss, (v30.security._SecuritySchemes.oauth2, v31.security._SecuritySchemes.oauth2))
            # NOTE: refresh_url is not currently supported by httpx_auth
            # REF: https://github.com/Colin-b/httpx_auth/issues/17
            if flow := ss.flows.implicit:
                auths.append(
                    httpx_auth.OAuth2Implicit(
                        **value,
                        authorization_url=flow.authorizationUrl,
                        scopes=flow.scopes,
                        # refresh_url=flow.refreshUrl,
                    )
                )
            if flow := ss.flows.password:
                auths.append(
                    httpx_auth.OAuth2ResourceOwnerPasswordCredentials(
                        **value,
                        token_url=flow.tokenUrl,
                        scopes=flow.scopes,
                        # refresh_url=flow.refreshUrl,
                    )
                )
            if flow := ss.flows.clientCredentials:
                auths.append(
                    httpx_auth.OAuth2ClientCredentials(
                        **value,
                        token_url=flow.tokenUrl,
                        scopes=flow.scopes,
                        # refresh_url=flow.refreshUrl,
                    )
                )
            if flow := ss.flows.authorizationCode:
                auths.append(
                    httpx_auth.OAuth2AuthorizationCode(
                        **value,
                        authorization_url=flow.authorizationUrl,
                        token_url=flow.tokenUrl,
                        scopes=flow.scopes,
                        # refresh_url=flow.refreshUrl,
                    )
                )

        if ss.type == "http":
            assert isinstance(ss, (v30.security._SecuritySchemes.http, v31.security._SecuritySchemes.http))
            if auth := HTTPX_AUTH_METHODS.get(ss.scheme_, None):
                if isinstance(value, tuple):
                    auths.append(auth(*value))
                elif isinstance(value, dict):
                    auths.append(auth(**value))
            elif ss.scheme_ == "bearer":
                auths.append(httpx_auth.HeaderApiKey(f"Bearer {value}", "Authorization"))
            else:
                raise ValueError(f"Authentication method {ss.type}/{ss.scheme_} is not supported by httpx-auth")

        if ss.type == "mutualTLS":
            self.req.cert = value

        value = cast(str, value)

        if ss.type == "apiKey":
            assert isinstance(ss, (v30.security._SecuritySchemes.apiKey, v31.security._SecuritySchemes.apiKey))
            if auth := HTTPX_AUTH_METHODS.get((ss.in_ + ss.type).lower(), None):
                auths.append(auth(value, ss.name))

            if ss.in_ == "cookie":
                self.req.cookies = {ss.name: value}

        for auth in auths:
            if self.req.auth and isinstance(self.req.auth, SupportMultiAuth):
                self.req.auth += auth
            else:
                self.req.auth = auth

    def _prepare_parameters(self, provided: Optional["RequestParameters"]) -> Dict[str, str]:
        """
        assigns the parameters provided to the header/path/cookie …

        FIXME: handle parameter location
          https://spec.openapis.org/oas/v3.0.3#parameter-object
          A unique parameter is defined by a combination of a name and location.
        """

        provided = provided or dict()
        possible = {_.name: _ for _ in self.operation.parameters + self.root.paths[self.path].parameters}

        from .. import v30, v31

        assert isinstance(self.operation, (v30.Operation, v31.Operation))

        if self.operation.requestBody:
            rbq: Dict[str, str] = dict()  # requestBody Parameters
            ct = "multipart/form-data"
            if ct in self.operation.requestBody.content:
                assert self.operation.requestBody.content[ct].encoding is not None
                for k, v in self.operation.requestBody.content[ct].encoding.items():
                    assert v.headers is not None and isinstance(v.headers, dict)
                    rbq.update(v.headers)
                possible.update(rbq)

        parameters = {}

        """collect default values"""
        for i in possible.values():
            if i.schema_ is not None and i.schema_.default is not None:
                parameters[i.name] = i.schema_.default
            elif (
                i.content is not None
                and (m := i.content.get("application/json", None)) is not None
                and m.schema_.default
            ):
                parameters[i.name] = m.schema_.default

        parameters.update(provided)

        available = frozenset(parameters.keys())
        accepted = frozenset(possible.keys())
        required = frozenset(map(lambda x: x[0], filter(lambda y: y[1].required, possible.items())))
        if available - accepted:
            raise ValueError(f"Parameter {sorted(available - accepted)} unknown (accepted {sorted(accepted)})")
        if required - available:
            raise ValueError(
                f"Required Parameter {sorted(required - available)} missing (provided {sorted(available)})"
            )

        path_parameters = {}
        rbqh = dict()
        for name, value in parameters.items():
            spec = possible[name]
            values = spec._encode(name, value)
            assert isinstance(values, dict)

            if isinstance(spec, (v30.parameter.Header, v31.parameter.Header)):
                rbqh.update(values)
            elif spec.in_ == "header":
                self.req.headers.update(values)
            elif spec.in_ == "path":
                # The string method `format` is incapable of partial updates,
                # as such we need to collect all the path parameters before
                # applying them to the format string.
                path_parameters.update(values)
            elif spec.in_ == "query":
                self.req.params.update(values)
            elif spec.in_ == "cookie":
                self.req.cookies.update(values)

        self.req.url = self.req.url.format(**path_parameters)
        return rbqh

    def _prepare_body(self, data_: Optional["RequestData"], rbq: Dict[str, str]) -> None:
        from .. import v30, v31

        assert isinstance(self.operation, (v30.Operation, v31.Operation))

        if not self.operation.requestBody:
            ctx = self.api.plugins.message.sending(
                request=self, operationId=self.operation.operationId, sending=None, headers=self.req.headers
            )
            self.req.content = ctx.sending
            self.req.headers = ctx.headers
            return

        if data_ is None and self.operation.requestBody.required:
            raise ValueError("Request Body is required but none was provided.")

        if "application/json" in self.operation.requestBody.content:
            if isinstance(data_, (dict, list)):
                data = data_
            elif isinstance(data_, pydantic.BaseModel):
                data = data_.model_dump(mode="json")
            else:
                raise TypeError(data_)
            data = self.api.plugins.message.marshalled(
                request=self, operationId=self.operation.operationId, marshalled=data
            ).marshalled
            data: str = json.dumps(data)
            data: bytes = data.encode()  # type: ignore[union-attr]
            self.req.headers["Content-Type"] = "application/json"
            ctx = self.api.plugins.message.sending(
                request=self, operationId=self.operation.operationId, sending=data, headers=self.req.headers
            )
            self.req.content = ctx.sending
            self.req.headers = ctx.headers
        elif (ct := "multipart/form-data") in self.operation.requestBody.content:
            """
            https://swagger.io/docs/specification/describing-request-body/multipart-requests/
            https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#media-type-object
            """
            media: aiopenapi3.v30.media.MediaType = self.operation.requestBody.content[ct]
            if media.schema_ and isinstance(data_, media.schema_.get_type()):
                """data is a model"""
                params = parameters_from_multipart(data_, media, rbq)
                msg = encode_multipart_parameters(params)
                self.req.content = msg.as_string()
                self.req.headers["Content-Type"] = f'{msg.get_content_type()}; boundary="{msg.get_boundary()}"'
            elif isinstance(data_, list):
                rfiles = list()
                rdata: Dict[str, str] = dict()
                name: str
                value: Tuple[str, Any]
                for name, value in cast(Sequence[Tuple[str, Any]], data_):
                    if isinstance(value, tuple):
                        alias = fh = content_type = None
                        headers: Dict[str, str] = {}
                        if len(value) == 4:
                            (alias, fh, content_type, headers) = cast(Tuple[str, Any, str, Dict[str, str]], value)
                        elif len(value) == 3:
                            (alias, fh, content_type) = cast(Tuple[str, Any, str], value)
                        elif len(value) == 2:
                            (alias, fh) = cast(Tuple[str, Any], value)
                        elif len(value) == 1:
                            fh = cast(Any, value)

                        assert media.encoding is not None
                        if (e := media.encoding.get(name)) is not None:
                            assert e.headers
                            headers.update({name: rbq[name] for name in e.headers.keys() if name in rbq})
                        _value = (alias, fh, content_type, headers)
                        rfiles.append((name, _value))
                    elif isinstance(value, str):
                        rdata[name] = value
                    else:
                        raise TypeError(type(value))  # noqa
                self.req.files = rfiles
                self.req.data = rdata
            else:
                assert media.schema_
                raise TypeError((type(data_), media.schema_.get_type()))
        elif (ct := "application/x-www-form-urlencoded") in self.operation.requestBody.content:
            self.req.headers["Content-Type"] = ct
            media: aiopenapi3.v30.media.MediaType = self.operation.requestBody.content[ct]
            assert media
            if not media.schema_ or not isinstance(data_, media.schema_.get_type()):
                """expect the data to be a model"""
                raise TypeError((type(data_), media.schema_))

            params = parameters_from_urlencoded(data_, media)
            content = urllib.parse.urlencode(params, doseq=True)
            self.req.content = content
        elif (ct := "application/octet-stream") in self.operation.requestBody.content:
            self.req.headers["Content-Type"] = ct
            value: "RequestFileParameter"
            if isinstance(data_, tuple) and len(data_) >= 2:
                # (name, file-like-object, …)
                self.req.content = data_[1]
            elif isinstance(data_, (io.IOBase, str, bytes)):
                self.req.content = data_
            else:
                raise TypeError(data_)
        else:
            raise NotImplementedError(self.operation.requestBody.content)

    def _prepare(self, data: Optional["RequestData"], parameters: Optional["RequestParameters"]) -> None:
        self._prepare_security()
        rbq = self._prepare_parameters(parameters)
        self._prepare_body(data, rbq)

    def _process__status_code(self, result: httpx.Response, status_code: str) -> "v3xResponseType":
        expected_response = (
            self.operation.responses.get(status_code)
            or self.operation.responses.get(status_code[0] + "XX")
            or self.operation.responses.get("default")
        )
        if expected_response is None:
            options = ",".join(self.operation.responses.keys())
            raise HTTPStatusError(
                self.operation,
                result.status_code,
                f"Unexpected response {result.status_code} from {self.operation.operationId} "
                f"(expected one of {options}), no default is defined",
                result,
            )
        return expected_response

    def _process__headers(
        self, result: httpx.Response, headers: Dict[str, str], expected_response: "v3xResponseType"
    ) -> Dict[str, str]:
        rheaders = dict()
        if expected_response.headers:
            required = dict(
                map(
                    lambda x: (x[0].lower(), x[1]),
                    filter(lambda x: x[1].required is True, expected_response.headers.items()),
                )
            )
            available = frozenset(headers.keys())
            if missing := (required.keys() - available):
                missed = {k: required[k] for k in missing}
                raise HeadersMissingError(self.operation, missed, result)
            for name, header in expected_response.headers.items():
                data = headers.get(name, None)
                if data:
                    assert header.schema_ is not None
                    rheaders[name] = header.schema_.model(header._decode(data))
        return rheaders

    def _process__content_type(
        self, result: httpx.Response, expected_response: "v3xResponseType", content_type: Optional[str]
    ) -> Tuple[str, "v3xMediaTypeType"]:
        if content_type:
            content_type, _, encoding = content_type.partition(";")
            expected_media: Optional["v3xMediaTypeType"] = expected_response.content.get(content_type, None)
            if expected_media is None and "/" in content_type:
                # accept media type ranges in the spec. the most specific matching
                # type should always be chosen, but if we do not have a match here
                # a generic range should be accepted if one if provided
                # https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.0.3.md#response-object

                generic_type = content_type.split("/")[0] + "/*"
                expected_media = expected_response.content.get(generic_type, None)
        else:
            expected_media = None

        if expected_media is None:
            options = ",".join(expected_response.content.keys())
            raise ContentTypeError(
                self.operation,
                content_type,
                f"Unexpected Content-Type {content_type} returned for operation {self.operation.operationId} \
                         (expected one of {options})",
                result,
            )
        assert content_type is not None
        return content_type, expected_media

    def _process_stream(self, result: httpx.Response) -> Tuple[Dict[str, str], Optional["SchemaType"]]:
        status_code = str(result.status_code)
        content_type = result.headers.get("Content-Type", None)

        expected_response = self._process__status_code(result, status_code)
        content_type, expected_media = self._process__content_type(result, expected_response, content_type)

        headers = self._process__headers(result, result.headers, expected_response)

        return headers, expected_media.schema_

    def _process_request(
        self, result: httpx.Response
    ) -> Tuple[Dict[str, str], Optional[Union[pydantic.BaseModel, str]]]:
        rheaders = dict()
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

        # status_code == 204 should match here
        if len(expected_response.content) == 0:
            return rheaders, None

        content_type, expected_media = self._process__content_type(result, expected_response, content_type)

        if content_type.lower() == "application/json":
            data = ctx.received
            try:
                data = json.loads(data)
            except json.decoder.JSONDecodeError:
                raise ResponseDecodingError(self.operation, result, data)
            data = self.api.plugins.message.parsed(
                request=self,
                operationId=self.operation.operationId,
                parsed=data,
                expected_type=getattr(expected_media.schema_, "_target", expected_media.schema_),
            ).parsed

            if expected_media.schema_ is None:
                raise ResponseSchemaError(self.operation, expected_media, expected_media.schema_, result, None)

            try:
                data = expected_media.schema_.model(data)
            except pydantic.ValidationError as e:
                raise ResponseSchemaError(self.operation, expected_media, expected_media.schema_, result, e)

            data = self.api.plugins.message.unmarshalled(
                request=self, operationId=self.operation.operationId, unmarshalled=data
            ).unmarshalled
            return rheaders, data
        else:
            """
            We have received a valid (i.e. expected) content type,
            e.g. application/octet-stream
            but we can't validate it since it's not json.
            """
            return rheaders, ctx.received


class AsyncRequest(Request, AsyncRequestBase):
    pass
