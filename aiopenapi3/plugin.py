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
        initialized: "OpenAPISpec"

    def initialized(self, ctx: "Init.Context") -> "Init.Context":  # pragma: no cover
        pass


class Document(Plugin):
    @dataclasses.dataclass
    class Context:
        url: yarl.URL
        document: Dict[str, Any]

    """
    loaded(text) -> parsed(dict)
    """

    def loaded(self, ctx: "Document.Context") -> "Document.Context":  # pragma: no cover
        """modify the text before parsing"""
        pass

    def parsed(self, ctx: "Document.Context") -> "Document.Context":  # pragma: no cover
        """modify the parsed dict before …"""
        pass


class Message(Plugin):
    @dataclasses.dataclass
    class Context:
        operationId: str
        marshalled: Optional[Dict[str, Any]] = None
        sending: Optional[str] = None
        received: Optional[str] = None
        parsed: Optional[Dict[str, Any]] = None
        unmarshalled: Optional[BaseModel] = None
        expected_type: Optional[typing.Type] = None

    """
    sending: marshalled(dict)-> sending(str)

    receiving: received -> parsed -> unmarshalled
    """

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
        p: List[Plugin] = list(filter(lambda x: isinstance(x, self._domains.get(name)), plugins))
        return Domain(self._domains.get(name).Context, p)

    @property
    def init(self) -> Domain:
        return self._init

    @property
    def document(self) -> Domain:
        return self._document

    @property
    def message(self) -> "Domain":
        return self._message
