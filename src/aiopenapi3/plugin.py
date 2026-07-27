import abc
import dataclasses
from typing import TYPE_CHECKING, Any, Optional, TypeGuard

import yarl
from pydantic import BaseModel

if TYPE_CHECKING:
    import httpx2

    from aiopenapi3 import OpenAPI

    from .base import PathItemBase, SchemaBase
    from .request import RequestBase

"""
the plugin interface replicates the suds way of  dealing with broken data/schema information
"""


class Plugin(abc.ABC):
    @dataclasses.dataclass
    class Context: ...

    def __init__(self) -> None:
        self._api: OpenAPI | None = None

    @property
    def api(self):
        return self._api

    @api.setter
    def api(self, v):
        if self._api is not None:
            raise ValueError(f"api is already set {v}")
        self._api = v


class Init(Plugin):
    @dataclasses.dataclass
    class Context:
        initialized: Optional["OpenAPI"] = None
        """available in :func:`~aiopenapi3.plugin.Init.initialized`"""
        schemas: dict[str, "SchemaBase"] | None = None
        """available in :func:`~aiopenapi3.plugin.Init.schemas`"""
        resolved: list["SchemaBase"] | None = None
        """available in :func:`~aiopenapi3.plugin.Init.schemas`"""
        paths: dict[str, "PathItemBase"] | None = None
        """available in :func:`~aiopenapi3.plugin.Init.paths`"""

    def schemas(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """modify the Schema before creating Models"""
        return ctx

    def resolved(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """modify the resolved paths/PathItems before initializing the Operations"""
        return ctx

    def paths(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """modify the paths/PathItems before initializing the Operations"""
        return ctx

    def initialized(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """it is initialized"""
        return ctx


class Document(Plugin):
    """
    loaded(text) -> parsed(dict)
    """

    @dataclasses.dataclass
    class Context:
        url: yarl.URL
        """available in :func:`~aiopenapi3.plugin.Document.loaded` :func:`~aiopenapi3.plugin.Document.parsed`"""
        document: dict[str, Any]
        """available in :func:`~aiopenapi3.plugin.Document.loaded` :func:`~aiopenapi3.plugin.Document.parsed`"""

    def loaded(self, ctx: "Document.Context") -> "Document.Context":  # pragma: no cover
        """modify the text before parsing"""
        return ctx

    def parsed(self, ctx: "Document.Context") -> "Document.Context":  # pragma: no cover
        """modify the parsed dict before …"""
        return ctx


class Message(Plugin):
    """
    sending: marshalled(dict)-> sending(str)

    receiving: received -> parsed -> unmarshalled
    """

    @dataclasses.dataclass
    class Context:
        request: "RequestBase"
        """available :func:`~aiopenapi3.plugin.Message.marshalled` :func:`~aiopenapi3.plugin.Message.sending`
        :func:`~aiopenapi3.plugin.Message.received` :func:`~aiopenapi3.plugin.Message.parsed`
        :func:`~aiopenapi3.plugin.Message.unmarshalled`"""
        operationId: str
        """available :func:`~aiopenapi3.plugin.Message.marshalled` :func:`~aiopenapi3.plugin.Message.sending`
        :func:`~aiopenapi3.plugin.Message.received` :func:`~aiopenapi3.plugin.Message.parsed`
        :func:`~aiopenapi3.plugin.Message.unmarshalled`"""
        marshalled: dict[str, Any] | None = None
        """available :func:`~aiopenapi3.plugin.Message.marshalled` """
        sending: str | None = None
        """available :func:`~aiopenapi3.plugin.Message.sending` """
        received: bytes | None = None
        """available :func:`~aiopenapi3.plugin.Message.received` """
        headers: "httpx2.Headers" = None
        """available :func:`~aiopenapi3.plugin.Message.sending` :func:`~aiopenapi3.plugin.Message.received` """
        cookies: dict[str, str] = None
        """available :func:`~aiopenapi3.plugin.Message.sending` """
        status_code: str | None = None
        """available :func:`~aiopenapi3.plugin.Message.received` """
        content_type: str | None = None
        """available :func:`~aiopenapi3.plugin.Message.received` """
        parsed: dict[str, Any] | None = None
        """available :func:`~aiopenapi3.plugin.Message.parsed` """
        expected_type: type | None = None
        """available :func:`~aiopenapi3.plugin.Message.parsed` """
        unmarshalled: BaseModel | None = None
        """available :func:`~aiopenapi3.plugin.Message.unmarshalled` """

    def marshalled(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the dict before sending
        """
        return ctx

    def sending(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the text before sending
        """
        return ctx

    def received(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the received text
        """
        return ctx

    def parsed(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the parsed dict structure
        """
        return ctx

    def unmarshalled(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the object
        """
        return ctx


class Domain:
    def __init__(self, ctx, plugins: list[Plugin]):
        self.ctx = ctx
        self.plugins = plugins

    def __getstate__(self):
        return self.ctx, self.plugins

    def __setstate__(self, state):
        self.ctx, self.plugins = state

    def __getattr__(self, name: str) -> "Method":
        return Method(name, self)


class Method:
    def __init__(self, name: str, domain: Domain):
        self.name = name
        self.domain = domain

    def __call__(self, **kwargs):
        # pickle …
        # TypeError: __init__() missing 1 required positional argument: 'initialized'
        #        if not kwargs:
        #            return
        r = self.domain.ctx(**kwargs)
        for plugin in self.domain.plugins:
            method = getattr(plugin, self.name, None)
            if method is None:
                continue
            method(r)
        return r


class Plugins:
    _domains: dict[str, type[Plugin]] = {"init": Init, "document": Document, "message": Message}

    def __init__(self, plugins: list[Plugin]):
        for p in plugins:
            assert isinstance(p, Plugin)

        self._init = self._get_domain("init", plugins)
        self._document = self._get_domain("document", plugins)
        self._message = self._get_domain("message", plugins)

    def _get_domain(self, name: str, plugins: list[Plugin]) -> "Domain":
        domain: type[Plugin] | None
        if (domain := self._domains.get(name)) is None:
            raise ValueError(name)

        def domain_type_f(p: Plugin) -> TypeGuard[Plugin]:
            return isinstance(p, domain)

        p: list[Plugin] = list(filter(domain_type_f, plugins))
        return Domain(domain.Context, p)

    @property
    def init(self) -> Domain:
        return self._init

    @property
    def document(self) -> Domain:
        return self._document

    @property
    def message(self) -> "Domain":
        return self._message
