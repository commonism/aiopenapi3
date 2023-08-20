from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode

from docutils import nodes, utils


def resolve_url(env, name):
    resolve_target = getattr(env.config, "linkcode_resolve", None)
    module, _, name = name.rpartition(".")
    uri = resolve_target("py", {"module": module, "fullname": name})
    return uri


class aiopenapi3Domain(Domain):
    name = "aioai3"
    label = "aiopenapi3 code linker"

    roles = {
        "ref": XRefRole(),
    }

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # print(f"{env=} {fromdocname=}, {builder=} {typ=} {target=} {node=} {contnode=}")
        title = contnode.astext()
        full_url = resolve_url(env, target)
        pnode = nodes.reference(title, title, internal=False, refuri=full_url)
        return pnode


def setup(app):
    app.add_domain(aiopenapi3Domain)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
