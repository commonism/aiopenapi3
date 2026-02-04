import base64
import quopri
from typing import TYPE_CHECKING, NamedTuple
from email.mime import multipart, nonmultipart
from email.message import Message
import collections

from .parameter import encode_parameter


if TYPE_CHECKING:
    from pydantic import BaseModel
    from .._types import MediaTypeType, SchemaType


class MIMEFormdata(nonmultipart.MIMENonMultipart):
    def __init__(self, keyname, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_header("Content-Disposition", f'form-data; name="{keyname}"')
        del self["MIME-Version"]


class MIMEMultipart(multipart.MIMEMultipart):
    def __init__(self):
        super().__init__("form-data")
        del self["MIME-Version"]

    def _write_headers(self, generator):
        pass


class MultipartParameter(NamedTuple):
    field: str
    content_type: str
    value: str | bytes
    headers: dict[str, str]
    schema: "SchemaType"


def parameters_from_multipart(
    data: "BaseModel", media: "MediaTypeType", mph: dict[str, str]
) -> list[MultipartParameter]:
    params: list[MultipartParameter] = list()
    for k in data.model_fields_set:
        v = getattr(data, k)
        ct = "text/plain"

        if (p := media.schema_.properties.get(k, None)) is not None:
            """OpenAPI 3.0 - Special Considerations for multipart Content"""
            if p.type == "array":
                p = p.items
            if p.type == "string" and (
                p.format in ("binary", "base64") or getattr(p, "contentEncoding", None) is not None
            ):
                ct = "application/octet-stream"
            elif p.type == "object":
                ct = "application/json"

        if (e := media.encoding.get(k, None)) is not None:
            ct = e.contentType or ct
            style = e.style or "form"
            explode = e.explode if e.explode is not None else (True if style == "form" else False)
            allowReserved = e.allowReserved or False
            headers = {name: mph[name] for name in e.headers.keys() if name in mph}
        else:
            allowReserved = False
            style = "form"
            explode = True
            headers = dict()

        m = media.schema_.properties[k]
        """
        using in=query should be fine
        it is only used to lookup the codec (style,explode) which is provided anyway
        """
        if isinstance(v, list):
            for i in v:
                r = encode_parameter(k, i, style, explode, allowReserved, "query", m.items)
                params.append(MultipartParameter(k, ct, r, headers, m.items))
        else:
            r = encode_parameter(k, v, style, explode, allowReserved, "query", m)
            params.append(MultipartParameter(k, ct, r, headers, m))
    return params


def parameters_from_urlencoded(data: "BaseModel", media: "MediaTypeType") -> dict[str, list[str]]:
    params: dict[str, list[str]] = collections.defaultdict(list)
    k: str
    for k in data.model_fields_set:
        v = getattr(data, k)

        assert media.encoding is not None
        if (e := media.encoding.get(k, None)) is not None:
            assert e
            explode = e.explode
            allowReserved = e.allowReserved
            style = e.style
        else:
            explode = True
            allowReserved = False
            style = "form"

        assert media.schema_ is not None and media.schema_.properties is not None
        m = media.schema_.properties[k]
        if isinstance(v, list):
            for i in v:
                r = encode_parameter(k, i, style, explode, allowReserved, "query", m.items)
                params[k].append(r)
        else:
            r = encode_parameter(k, v, style, explode, allowReserved, "query", m)
            params[k].append(r)
    return params


def encode_content(data: bytes, codec: str) -> bytes:
    """
    … supports all encodings defined in [RFC4648], including “base64” and “base64url”, as well as “quoted-printable” from [RFC2045].
    :param data:
    :param codec:
    :return:
    """
    if codec in ["base16", "base32", "base64", "base64url"]:
        if codec == "base16":
            r = base64.b16encode(data)
        elif codec == "base32":
            r = base64.b32encode(data)
        elif codec == "base64":
            r = base64.b64encode(data)
        elif codec == "base64url":
            r = base64.urlsafe_b64encode(data).rstrip(b"=")
        return r
    elif codec == "quoted-printable":
        return quopri.encodestring(data)
    else:
        raise ValueError(f"unsupported codec {codec}")


def encode_multipart_parameters(
    fields: list[MultipartParameter],
) -> MIMEMultipart:
    """
    As shown in
    https://julien.danjou.info/handling-multipart-form-data-python/

    :param fields:
    :return:
    """
    m = MIMEMultipart()
    data: str | bytes
    for f in fields:
        type, subtype, params = decode_content_type(f.content_type)
        if type in ["image", "audio", "application"]:
            v: bytes
            if isinstance(f.value, bytes):
                v = f.value
            else:
                v = f.value.encode()

            codec = "base64"

            if hasattr(f.schema, "contentEncoding"):
                """OpenAPI 3.1"""
                if f.schema.contentEncoding:
                    codec = f.schema.contentEncoding
                    f.headers["Content-Encoding"] = codec
            else:
                """OpenAPI 3.0"""
                pass

            data = encode_content(v, codec)

            """
            email.message_from_… uses content-transfer-encoding
            """
            f.headers["Content-Transfer-Encoding"] = codec

        elif type in ["text", "rfc822"]:
            data = f.value
        else:
            type, subtype = "text", "plain"
            data = f.value

        env = MIMEFormdata(f.field, type, subtype)

        for header, value in f.headers.items():
            env.add_header(header, value)

        for k, p in params:
            env.set_param(k, p, "Content-Type")

        env.set_payload(data)

        m.attach(env)

    return m


class ContentType(NamedTuple):
    type: str
    subtype: str
    params: list[tuple[str, str]]


def decode_content_type(value: str) -> ContentType:
    """
    from email.message import _unquotevalue
    msg = Message._get_params_preserve({"content-type": value}, header="content-type", failobj=None)
    ct, *params = list(map(lambda x: (x[0], _unquotevalue(x[1])) if x[0].lower() == x[0] else x, msg))
    """
    m = Message()
    m.add_header("content-type", value)
    ct, *params = m.get_params()

    type_, _, subtype = ct[0].partition("/")
    return ContentType(type_, subtype, params)
