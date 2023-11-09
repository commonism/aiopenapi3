import base64
import quopri
from typing import List, Tuple, Dict, Union, TYPE_CHECKING
from email.mime import multipart, nonmultipart
from email.message import _unquotevalue, Message
import collections

from .parameter import encode_parameter


if TYPE_CHECKING:
    from pydantic import BaseModel
    from .._types import MediaTypeType, SchemaType


class MIMEFormdata(nonmultipart.MIMENonMultipart):
    def __init__(self, keyname, *args, **kwargs):
        super(MIMEFormdata, self).__init__(*args, **kwargs)
        self.add_header("Content-Disposition", f'form-data; name="{keyname}"')
        del self["MIME-Version"]


class MIMEMultipart(multipart.MIMEMultipart):
    def __init__(self):
        super().__init__("form-data")
        del self["MIME-Version"]

    def _write_headers(self, generator):
        pass


def parameters_from_multipart(data, media, rbq):
    params = list()
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
            headers = {name: rbq[name] for name in e.headers.keys() if name in rbq}
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
                params.append((k, ct, r, headers, m.items))
        else:
            r = encode_parameter(k, v, style, explode, allowReserved, "query", m)
            params.append((k, ct, r, headers, m))
    return params


def parameters_from_urlencoded(data: "BaseModel", media: "MediaTypeType"):
    params = collections.defaultdict(lambda: list())
    k: str
    for k in data.model_fields_set:
        v = getattr(data, k)

        assert media.encoding is not None
        if (e := media.encoding.get(k, None)) != None:
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
    fields: List[Tuple[str, str, Union[str, bytes], Dict[str, str], "SchemaType"]]
) -> MIMEMultipart:
    """
    As shown in
    https://julien.danjou.info/handling-multipart-form-data-python/

    :param fields:
    :return:
    """
    m = MIMEMultipart()
    data: Union[str, bytes]
    for field, ct, value, headers, schema in fields:
        type, subtype, params = decode_content_type(ct)

        if type in ["image", "audio", "application"]:
            if isinstance(value, bytes):
                v: bytes = value
            else:
                v: bytes = value.encode()

            codec = "base64"

            if hasattr(schema, "contentEncoding"):
                """OpenAPI 3.1"""
                if schema.contentEncoding:
                    codec = schema.contentEncoding
                    headers["Content-Encoding"] = codec
            else:
                """OpenAPI 3.0"""

            data = encode_content(v, codec)

            """
            email.message_from_… uses content-transfer-encoding
            """
            headers["Content-Transfer-Encoding"] = codec

        elif type in ["text", "rfc822"]:
            data = value
        else:
            type, subtype = "text", "plain"
            data = value

        env = MIMEFormdata(field, type, subtype)

        for header, value in headers.items():
            env.add_header(header, value)

        v: str
        for k, v in params:
            env.set_param(k, v, "Content-Type")

        env.set_payload(data)

        m.attach(env)

    return m


def decode_content_type(value: str) -> Tuple[str, str, List[Tuple[str, str]]]:
    """
    msg = Message._get_params_preserve({"content-type": value}, header="content-type", failobj=None)
    ct, *params = list(map(lambda x: (x[0], _unquotevalue(x[1])) if x[0].lower() == x[0] else x, msg))
    """
    m = Message()
    m.add_header("content-type", value)
    ct, *params = m.get_params()

    type_, _, subtype = ct[0].partition("/")
    return type_, subtype, params
