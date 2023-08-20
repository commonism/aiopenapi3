# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import importlib
import inspect
from pathlib import Path
import sys
import datetime


sys.path.append(str(p := (Path(".").absolute() / "_ext")))
assert p.exists(), f"{p} {os.getcwd()}"

sys.path.append(str(p := Path(".").absolute().parent.parent))
assert p.exists(), f"{p} {os.getcwd()}"
"""
this is the basedir of the project
allows to import tests/
required for use with linkcode_resolve/aioai3
"""

project = "aiopenapi3"
copyright = f"{datetime.datetime.now().date().year}, Markus Kötter"
author = "Markus Kötter"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.linkcode",
    "sphinx.ext.inheritance_diagram",
    "aioai3",
]

root_doc = "toc"

# Make sure the target is unique
autosectionlabel_prefix_document = True


import aiopenapi3.version

release = aiopenapi3.version.__version__

linkcode_commit = os.environ.get("READTHEDOCS_VERSION", "next")
if linkcode_commit == "stable":
    linkcode_commit = f"v{aiopenapi3.version.__version__}"
else:
    linkcode_commit = os.environ.get("READTHEDOCS_GIT_COMMIT_HASH") or linkcode_commit

linkcode_url = f"https://github.com/commonism/aiopenapi3/blob/{linkcode_commit}"


def debug(msg=""):
    print(f"{__file__} {sys._getframe().f_back.f_lineno}: {msg}")


def linkcode_resolve(domain, info):
    """
    idea: https://github.com/readthedocs/sphinx-autoapi/issues/202
    """
    assert domain == "py", "expected only Python objects"
    try:
        obj = mod = importlib.import_module(info["module"])
    except ImportError as e:
        print(e)
        debug(info)
        return None
    except ValueError as v:
        raise ValueError(info, *v.args) from v

    *objname, attrname = info["fullname"].split(".")

    # resolve obj
    if objname:
        try:
            for i in objname:
                obj = getattr(obj, i)
        except AttributeError:
            debug(info)
            raise ValueError(f"could not resolve {objname} ")

    # resolve attr
    try:
        # object is a method of a class
        obj = getattr(obj, attrname)
    except AttributeError:
        # object is an attribute of a class
        return None

    try:
        file = inspect.getsourcefile(obj)
        lines = inspect.getsourcelines(obj)
    except TypeError:
        # e.g. object is a typing.Union
        debug(info)
        return None

    import site

    f = Path(file)
    if f.is_relative_to(srcdir := (Path(__file__).parent.parent.parent)):
        linkcode_file = f.relative_to(srcdir)
    else:
        for s in site.getsitepackages():
            if f.is_relative_to(s):
                linkcode_file = f.relative_to(s)
                break
        else:
            debug(info)
            return None
    if linkcode_file.parts[0] not in ("aiopenapi3", "tests"):
        debug(info)
        return None
    linkcode_file = str(linkcode_file)
    start, end = lines[1], lines[1] + len(lines[0]) - 1
    return f"{linkcode_url}/{linkcode_file}#L{start}-L{end}"


templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_js_files = [
    "my_custom.js",
]

sections = """
https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#sections

    # with overline, for parts
    * with overline, for chapters
    = for sections
    - for subsections
    ^ for subsubsections
    " for paragraphs
"""
