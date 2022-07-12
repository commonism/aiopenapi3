import abc
import json


import yaml
import httpx
import yarl

import sys

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from .plugin import Plugins

"""
https://stackoverflow.com/questions/34667108/ignore-dates-and-times-while-parsing-yaml
"""


def remove_implicit_resolver(cls, tag_to_remove):
    """
    Remove implicit resolvers for a particular tag

    Takes care not to modify resolvers in super classes.

    We want to load datetimes as strings, not dates, because we
    go on to serialise as json which doesn't have the advanced types
    of yaml, and leads to incompatibilities down the track.
    """
    if not "yaml_implicit_resolvers" in cls.__dict__:
        cls.yaml_implicit_resolvers = cls.yaml_implicit_resolvers.copy()

    for first_letter, mappings in cls.yaml_implicit_resolvers.items():
        cls.yaml_implicit_resolvers[first_letter] = [(tag, regexp) for tag, regexp in mappings if tag != tag_to_remove]


class YAMLCompatibilityLoader(yaml.SafeLoader):
    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        remove_implicit_resolver(cls, tag_to_remove)


YAMLCompatibilityLoader.remove_implicit_resolver("tag:yaml.org,2002:timestamp")

"""
example: =
"""
YAMLCompatibilityLoader.remove_implicit_resolver("tag:yaml.org,2002:value")

"""
18_24: test
"""
YAMLCompatibilityLoader.remove_implicit_resolver("tag:yaml.org,2002:int")

"""
name: on
"""
YAMLCompatibilityLoader.remove_implicit_resolver("tag:yaml.org,2002:bool")


class Loader(abc.ABC):
    def __init__(self, yload: yaml.Loader = yaml.SafeLoader):
        self.yload = yload

    @abc.abstractmethod
    def load(self, plugins, url: yarl.URL, codec=None):
        raise NotImplementedError("load")

    @classmethod
    def decode(cls, data, codec):
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

    def parse(self, plugins, url: yarl.URL, data):
        file = Path(url.path)
        if file.suffix == ".yaml":
            data = yaml.load(data, Loader=self.yload)
        elif file.suffix == ".json":
            data = json.loads(data)
        else:
            raise ValueError(f"{file.name} is not yaml/json")
        return data

    def get(self, plugins, url: yarl.URL):
        data = self.load(plugins, url)
        return self.parse(plugins, url, data)

    def __repr__(self):
        return f"{self.__class__.__qualname__}"


class NullLoader(Loader):
    def load(self, plugins, url: yarl.URL, codec=None):
        raise NotImplementedError("load")


class WebLoader(Loader):
    def __init__(self, baseurl, session_factory=httpx.Client, yload=yaml.SafeLoader):
        super().__init__(yload)
        self.baseurl = baseurl
        self.session_factory = session_factory

    def load(self, plugins, url: yarl.URL, codec=None):
        url = self.baseurl.join(url)
        with self.session_factory() as session:
            data = session.get(str(url))
            data = data.content
        data = self.decode(data, codec)
        data = plugins.document.loaded(url=url, document=data).document
        return data

    def parse(self, plugins, url: yarl.URL, data):
        data = super().parse(plugins, url, data)
        data = plugins.document.parsed(url=url, document=data).document
        return data

    def __repr__(self):
        return f"{self.__class__.__qualname__}(baseurl={self.baseurl})"


class FileSystemLoader(Loader):
    def __init__(self, base: Path, yload: yaml.Loader = yaml.SafeLoader):
        super().__init__(yload)
        assert isinstance(base, Path)
        self.base = base

    def load(self, plugins: Plugins, url: yarl.URL, codec=None):
        assert isinstance(url, yarl.URL)
        assert plugins
        file = Path(url.path)
        path = self.base / file
        assert path.is_relative_to(self.base)
        with path.open("rb") as f:
            data = f.read()
        data = self.decode(data, codec)
        data = plugins.document.loaded(url=url, document=data).document
        return data

    def parse(self, plugins, url: yarl.URL, data):
        data = super().parse(plugins, url, data)
        data = plugins.document.parsed(url=url, document=data).document
        return data

    def __repr__(self):
        return f"{self.__class__.__qualname__}(base={self.base})"
