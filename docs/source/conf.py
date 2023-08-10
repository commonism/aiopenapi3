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

project = "aiopenapi3"
copyright = "2022, Markus Kötter"
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
]

# Make sure the target is unique
autosectionlabel_prefix_document = True

import aiopenapi3.version

release = aiopenapi3.version.__version__

linkcode_commit = os.environ.get("READTHEDOCS_VERSION", "next")
if linkcode_commit == "stable":
    linkcode_commit = f"v{aiopenapi3.version.__version__}"
elif linkcode_commit == "latest":
    linkcode_commit = "master"
elif linkcode_commit == "next":
    pass
linkcode_url = f"https://github.com/commonism/aiopenapi3/blob/{linkcode_commit}"


def linkcode_resolve(domain, info):
    """
    idea: https://github.com/readthedocs/sphinx-autoapi/issues/202
    """
    assert domain == "py", "expected only Python objects"

    mod = importlib.import_module(info["module"])
    if "." in info["fullname"]:
        *objname, attrname = info["fullname"].split(".")
        obj = mod
        try:
            for i in objname:
                obj = getattr(obj, i)
        except AttributeError:
            return None
        try:
            # object is a method of a class
            obj = getattr(obj, attrname)
        except AttributeError:
            # object is an attribute of a class
            return None
    else:
        obj = getattr(mod, info["fullname"])

    try:
        file = inspect.getsourcefile(obj)
        lines = inspect.getsourcelines(obj)
    except TypeError:
        # e.g. object is a typing.Union
        return None

    import site

    f = Path(file)
    for s in site.getsitepackages():
        if f.is_relative_to(s):
            linkcode_file = f.relative_to(s)
            break
    else:
        return None
    if linkcode_file.parts[0] != "aiopenapi3":
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

sections = """
https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#sections

    # with overline, for parts
    * with overline, for chapters
    = for sections
    - for subsections
    ^ for subsubsections
    " for paragraphs
"""
