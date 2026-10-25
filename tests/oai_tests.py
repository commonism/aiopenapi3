import io
import zipfile
from pathlib import Path

import httpx2
import pytest
import yarl
from pydantic import ValidationError

from aiopenapi3 import OpenAPI
from aiopenapi3.loader import Loader, YAML12Loader, YAMLLoaderType
from aiopenapi3.plugin import Plugins


class ZipFileLoader(Loader):
    """
    Loader to use the local filesystem
    """

    def __init__(self, archive: zipfile.ZipFile, base: Path, yload: "YAMLLoaderType" = YAML12Loader):
        """
        :param base: basedir - lookups are relative to this
        :param yload:
        """
        super().__init__(yload)
        assert isinstance(base, Path)
        self.base = base
        self.z = archive

    def load(self, plugins: Plugins, url: yarl.URL, codec: str | None = None):
        assert isinstance(url, yarl.URL)
        assert plugins
        file = Path(url.path)
        path = self.base / file
        assert path.is_relative_to(self.base), f"{path} is not relative to {self.base}"
        data: bytes
        data = self.z.read(str(self.base / url.name))
        data: str = self.decode(data, codec)
        data = plugins.document.loaded(url=url, document=data).document
        return data

    def __repr__(self):
        return f"{self.__class__.__qualname__}(base={self.base})"


def get() -> tuple[list[tuple[Path, str, zipfile.ZipFile]], list[tuple[Path, str, zipfile.ZipFile]]]:
    pass_ = []
    fail = []
    for v in ["v3.1-dev", "v3.2-dev"]:
        base = ""
        r = httpx2.get(
            f"https://github.com/OAI/OpenAPI-Specification/archive/refs/heads/{v}.zip", follow_redirects=True
        )
        data = io.BytesIO(r.read())
        data.seek(0, io.SEEK_SET)
        z = zipfile.ZipFile(data)
        for name in z.namelist():
            if not base and name.endswith("tests/schema/"):
                base = name
            if not base:
                continue
            #            if not name.endswith("mega.yaml"):
            #                continue
            if name.startswith(f"{base}pass/") and name.endswith(".yaml"):
                pass_.append((Path(name), v, z))
            if name.startswith(f"{base}fail/") and name.endswith(".yaml"):
                fail.append((Path(name), v, z))
    return (pass_, fail)


def pytest_generate_tests(metafunc):
    pass_, fail = get()

    if "xpass" in metafunc.fixturenames:
        metafunc.parametrize("xpass", pass_, ids=[f"{i[1]}@{i[0].name}" for i in pass_])

    if "xfail" in metafunc.fixturenames:
        metafunc.parametrize("xfail", fail, ids=[f"{i[1]}@{i[0].name}" for i in fail])


@pytest.mark.xfail
def test_oai_pass(xpass: tuple[Path, zipfile.ZipFile]):
    file, _, z = xpass
    api = OpenAPI.load_file(file.name, file.name, loader=ZipFileLoader(z, file.parent))


@pytest.mark.xfail
def test_oai_fail(xfail: tuple[Path, str, zipfile.ZipFile]):
    file, _, z = xfail
    with pytest.raises(ValidationError):
        api = OpenAPI.load_file(file.name, file.name, loader=ZipFileLoader(z, file.parent))
