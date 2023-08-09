import abc
import json
import logging

import yaml
import httpx
import yarl
import re

import sys

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from .plugin import Plugins

log = logging.getLogger("aiopenapi3.loader")


class YAML12Loader(yaml.SafeLoader):
    """
    A YAML 1.2 (2009) parser is still a problem in python (in 2023)

    OpenAPI uses YAML 1.2
    pyyaml is limited to 1.1

    try creating a yaml 1.2 parser
    remove all tags from the SafeLoader
    add the YAML 1.2 core tags
    """

    _core_resolvers = [
        ["bool", re.compile(r"""^(?:|true|True|TRUE|false|False|FALSE)$""", re.X), list("tTfF")],
        [
            "int",
            re.compile(
                r"""^(?:
                                  |0o[0-7]+
                                  |[-+]?(?:[0-9]+)
                                  |0x[0-9a-fA-F]+
                                  )$""",
                re.X,
            ),
            list("-+0123456789"),
        ],
        [
            "float",
            re.compile(
                r"""^(?:[-+]?(?:\.[0-9]+|[0-9]+(\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?
                                  |[-+]?\.(?:inf|Inf|INF)
                                  |\.(?:nan|NaN|NAN))$""",
                re.X,
            ),
            list("-+0123456789."),
        ],
        ["null", re.compile(r"""^(?:~||null|Null|NULL)$""", re.X), ["~", "n", "N", ""]],
    ]
    """
    core tags from
    https://github.com/yaml/pyyaml/pull/700/files
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tags = set(
            sum(list(map(lambda x: list(map(lambda y: y[0], x)), YAML12Loader.yaml_implicit_resolvers.values())), [])
        )
        for tag in tags:
            YAML12Loader.remove_implicit_resolver(tag)
        for tag, regex, initial in YAML12Loader._core_resolvers:
            tag = f"tag:yaml.org,2002:{tag}"
            YAML12Loader.add_implicit_resolver(tag, regex, initial)

    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        """
        https://stackoverflow.com/questions/34667108/ignore-dates-and-times-while-parsing-yaml

        Remove implicit resolvers for a particular tag

        Takes care not to modify resolvers in super classes.

        We want to load datetimes as strings, not dates, because we
        go on to serialise as json which doesn't have the advanced types
        of yaml, and leads to incompatibilities down the track.
        """
        if not "yaml_implicit_resolvers" in cls.__dict__:
            cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()

        for first_letter, mappings in cls.yaml_implicit_resolvers.items():
            cls.yaml_implicit_resolvers[first_letter] = [
                (tag, regexp) for tag, regexp in mappings if tag != tag_to_remove
            ]


class Loader(abc.ABC):
    """
    Loaders are used to 'get' description documents:

     * load
     * decode
     * parse
    """

    def __init__(self, yload: yaml.Loader = YAML12Loader):
        self.yload = yload

    @abc.abstractmethod
    def load(self, plugins: Plugins, url: yarl.URL, codec: str = None):
        """
        load and decode description document

        :param plugins: collection of `aiopenapi3.plugin.Document` plugins
        :param url: location of the description document
        :param codec:
        :return: decoded data
        """
        raise NotImplementedError("load")

    @classmethod
    def decode(cls, data: bytes, codec: str):
        """
        decode bytes to ascii or utf-8

        :param data:
        :param codec:
        :return:
        """
        if codec is not None:
            codecs = [codec]
        else:
            codecs = ["ascii", "utf-8"]
        for c in codecs:
            try:
                data = data.decode(c)
                break
            except UnicodeError:
                continue
        else:
            raise ValueError("encoding")
        return data

    def parse(self, plugins: Plugins, url: yarl.URL, data: str):
        """
        parse the downloaded document as json or yaml

        :param plugins: collection of `aiopenapi3.plugin.Document` plugins
        :param url: location of the description document
        :param data: decoded data of the description document
        :return:
        """
        file = Path(url.path)
        if file.suffix not in (".yaml", ".json"):
            try:
                return self.parse(plugins, url.with_path("/test.yaml"), data)
            except Exception as e:
                pass
            try:
                return self.parse(plugins, url.with_path("/test.json"), data)
            except Exception as e:
                pass

        if file.suffix == ".yaml":
            data = yaml.load(data, Loader=self.yload)
        elif file.suffix == ".json":
            data = json.loads(data)
        else:
            raise ValueError(f"{file.name} is not yaml/json")

        data = plugins.document.parsed(url=url, document=data).document
        return data

    def get(self, plugins: Plugins, url: yarl.URL):
        """
        load & parse the description document
        :param plugins: collection of `aiopenapi3.plugin.Document` plugins
        :param url: location of the description document
        :return:
        """
        data = self.load(plugins, url)
        return self.parse(plugins, url, data)

    def __repr__(self):
        return f"{self.__class__.__qualname__}"


class NullLoader(Loader):
    """
    Loader does not load anything
    """

    def load(self, plugins: Plugins, url: yarl.URL, codec: str = None):
        raise NotImplementedError("load")


class WebLoader(Loader):
    """
    Loader downloads data via http/s using the supplied session_factory
    """

    def __init__(self, baseurl: yarl.URL, session_factory=httpx.Client, yload: yaml.Loader = YAML12Loader):
        super().__init__(yload)
        assert isinstance(baseurl, yarl.URL)
        self.baseurl: yarl.URL = baseurl
        self.session_factory = session_factory

    def load(self, plugins: Plugins, url: yarl.URL, codec: str = None):
        url = self.baseurl.join(url)
        with self.session_factory() as session:
            data = session.get(str(url))
            assert 200 <= data.status_code <= 299, data
            data = data.content
        data = self.decode(data, codec)
        data = plugins.document.loaded(url=url, document=data).document
        return data

    def __repr__(self):
        return f"{self.__class__.__qualname__}(baseurl={self.baseurl})"


class FileSystemLoader(Loader):
    """
    Loader to use the local filesystem
    """

    def __init__(self, base: Path, yload: yaml.Loader = YAML12Loader):
        """
        :param base: basedir - lookups are relative to this
        :param yload:
        """
        super().__init__(yload)
        assert isinstance(base, Path)
        self.base = base

    def load(self, plugins: Plugins, url: yarl.URL, codec: str = None):
        assert isinstance(url, yarl.URL)
        assert plugins
        file = Path(url.path)
        path = self.base / file
        assert path.is_relative_to(self.base), f"{path} is not relative to {self.base}"
        with path.open("rb") as f:
            data = f.read()
        data = self.decode(data, codec)
        data = plugins.document.loaded(url=url, document=data).document
        return data

    def __repr__(self):
        return f"{self.__class__.__qualname__}(base={self.base})"


class RedirectLoader(FileSystemLoader):
    """
    Loader to redirect web-requests to a local directory
    everything but the "name" is stripped of the url
    """

    def load(self, plugins: "Plugins", url: yarl.URL, codec: str = None):
        return super().load(plugins, yarl.URL(url.name), codec)


class ChainLoader(Loader):
    """
    Loader to chain different Loaders: succeed or raise trying
    """

    def __init__(self, *loaders, yload: yaml.Loader = YAML12Loader):
        """

        :param loaders: loaders to use
        :param yload: YAML loader to use
        """
        Loader.__init__(self, yload)
        self.loaders = loaders

    def load(self, plugins: "Plugins", url: yarl.URL, codec: str = None):
        log.debug(f"load {url}")
        errors = []
        for i in self.loaders:
            try:
                r = i.load(plugins, url, codec)
                log.debug(f"using {i}")
                return r
            except Exception as e:
                errors.append((i, str(e)))
        for l, e in errors:
            log.debug(f"{l} {e}")
        raise FileNotFoundError(url)
