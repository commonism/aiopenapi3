import dataclasses
import typing
from typing import List, Any, Dict, Optional, Type
import abc

from pydantic import BaseModel

import yarl

"""
the plugin interface replicates the suds way of  dealing with broken data/schema information
"""


class Plugin(abc.ABC):
    def __init__(self):
        self._api: "OpenAPI" = None

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
        initialized: "aiopenapi3.OpenAPI" = None
        """available in :func:`~aiopenapi3.plugin.Init.initialized`"""
        schemas: Dict[str, "Schema"] = None
        """available in :func:`~aiopenapi3.plugin.Init.schemas`"""
        paths: Dict[str, "PathItemBase"] = None
        """available in :func:`~aiopenapi3.plugin.Init.paths`"""

    def schemas(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """modify the Schema before creating Models"""
        pass

    def paths(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """modify the paths/PathItems before initializing the Operations"""
        pass

    def initialized(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        """it is initialized"""
        pass


class Document(Plugin):
    """
    loaded(text) -> parsed(dict)
    """

    @dataclasses.dataclass
    class Context:
        url: yarl.URL
        """available in :func:`~aiopenapi3.plugin.Document.loaded` :func:`~aiopenapi3.plugin.Document.parsed`"""
        document: Dict[str, Any]
        """available in :func:`~aiopenapi3.plugin.Document.loaded` :func:`~aiopenapi3.plugin.Document.parsed`"""

    def loaded(self, ctx: "Document.Context") -> "Document.Context":  # pragma: no cover
        """modify the text before parsing"""
        pass

    def parsed(self, ctx: "Document.Context") -> "Document.Context":  # pragma: no cover
        """modify the parsed dict before …"""
        pass


class Message(Plugin):
    """
    sending: marshalled(dict)-> sending(str)

    receiving: received -> parsed -> unmarshalled
    """

    @dataclasses.dataclass
    class Context:
        operationId: str
        """available :func:`~aiopenapi3.plugin.Message.marshalled` :func:`~aiopenapi3.plugin.Message.sending` :func:`~aiopenapi3.plugin.Message.received` :func:`~aiopenapi3.plugin.Message.parsed` :func:`~aiopenapi3.plugin.Message.unmarshalled`"""
        marshalled: Optional[Dict[str, Any]] = None
        """available :func:`~aiopenapi3.plugin.Message.marshalled` """
        sending: Optional[str] = None
        """available :func:`~aiopenapi3.plugin.Message.sending` """
        received: Optional[bytes] = None
        """available :func:`~aiopenapi3.plugin.Message.received` """
        headers: "httpx.Headers" = None
        """available :func:`~aiopenapi3.plugin.Message.sending` :func:`~aiopenapi3.plugin.Message.received` """
        status_code: Optional[str] = None
        """available :func:`~aiopenapi3.plugin.Message.received` """
        content_type: Optional[str] = None
        """available :func:`~aiopenapi3.plugin.Message.received` """
        parsed: Optional[Dict[str, Any]] = None
        """available :func:`~aiopenapi3.plugin.Message.parsed` """
        expected_type: Optional[typing.Type] = None
        """available :func:`~aiopenapi3.plugin.Message.parsed` """
        unmarshalled: Optional[BaseModel] = None
        """available :func:`~aiopenapi3.plugin.Message.unmarshalled` """

    def marshalled(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the dict before sending
        """
        pass

    def sending(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the text before sending
        """
        pass

    def received(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the received text
        """
        pass

    def parsed(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the parsed dict structure
        """
        pass

    def unmarshalled(self, ctx: "Message.Context") -> "Message.Context":  # pragma: no cover
        """
        modify the object
        """
        pass


class Domain:
    def __init__(self, ctx, plugins: List[Plugin]):
        self.ctx = ctx
        self.plugins = plugins

    def __getstate__(self):
        return (self.ctx, self.plugins)

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
    _domains: Dict[str, Type[Plugin]] = {"init": Init, "document": Document, "message": Message}

    def __init__(self, plugins: List[Plugin]):
        for p in plugins:
            assert isinstance(p, Plugin)

        self._init = self._get_domain("init", plugins)
        self._document = self._get_domain("document", plugins)
        self._message = self._get_domain("message", plugins)

    def _get_domain(self, name, plugins) -> "Domain":
        domain = self._domains.get(name)
        p: List[Plugin] = list(filter(lambda x: isinstance(x, domain), plugins))
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
