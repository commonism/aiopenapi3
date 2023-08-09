import argparse
import datetime
import sys
import json
import itertools
from typing import List
from pstats import SortKey
import pstats
import io
import importlib.util
import cProfile
import tracemalloc
import linecache
import logging

import jmespath
import yaml
import yarl
import httpx

import aiopenapi3.plugin

logg = logging.getLogger()
logging.basicConfig()

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from .openapi import OpenAPI

from .loader import ChainLoader, RedirectLoader, WebLoader
import aiopenapi3.loader


log = None


def loader_prepare(args, session_factory):
    path = yarl.URL(args.input)
    if path.scheme in ["http", "https"]:
        loader = WebLoader(baseurl=path.with_path("/").with_query({}), session_factory=session_factory)
    else:
        locations = args.locations or [Path(args.input).parent]
        loader = ChainLoader(*[RedirectLoader(Path(l).expanduser()) for l in locations])

    return loader


def plugins_load(baseurl, plugins: List[str]) -> List[aiopenapi3.plugin.Plugin]:
    """
    load Plugins from python files
    :param args:
    :return:
    """
    r = []
    for p in plugins:
        file, _, cls = p.partition(":")
        cls = cls.split(",")

        spec = importlib.util.spec_from_file_location("extra", file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for c in cls:
            plugin = getattr(module, c)
            varnames = plugin.__init__.__code__.co_varnames
            if len(varnames) == 1:
                obj = plugin()
            elif varnames == ("self", "url"):
                obj = plugin(baseurl)
            else:
                raise TypeError("Can't __init__ plugin - unknown args")
            r.append(obj)
    return r


def tm_display_top(snapshot, key_type="lineno", limit=10):
    """
    copied from
    https://docs.python.org/3/library/tracemalloc.html
    """
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            #                tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print("#%s: %s:%s: %.1f KiB" % (index, frame.filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def pr_display_top(pr):
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())


def schema_display_stats(api, duration):
    operations = list(
        itertools.chain.from_iterable(
            map(
                lambda x: list(filter(lambda x: x, [x.delete, x.get, x.head, x.options, x.patch, x.post, x.put])),
                api.paths._paths.values(),
            )
        )
    )
    print(f"…  {duration} (processing time)")
    print(f"… {len(operations)} #operations")
    operations = list(filter(lambda x: x.operationId, operations))
    print(f"… {len(operations)} #operations (with operationId)")

    def schemaof(x):
        if isinstance(api._root, aiopenapi3.v20.Root):
            return x.definitions
        else:
            return x.components.schemas

    ss = 0
    for idx, (name, v) in enumerate(api._documents.items()):
        ss += len(schemaof(v))
        print(f"… {idx} {name}: {len(schemaof(v))}")
    print(f"… {ss} schemas total")


def main(argv=None):
    global log
    plugins = []
    parser = argparse.ArgumentParser("aiopenapi3", description="Swagger 2.0, OpenAPI 3.0, OpenAPI 3.1 validator")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="be verbose")
    parser.add_argument("-p", "--profile", action="store_true", default=False)
    parser.add_argument("--profile-file", type=str, default=None)
    parser.add_argument("-t", "--tracemalloc", action="store_true", default=False)
    parser.add_argument("-P", "--plugins", action="append")
    parser.add_argument("-L", "--locations", action="append")
    parser.add_argument("-C", "--cache")
    parser.add_argument("--disable-ssl-validation", action="store_true", default=False)
    sub = parser.add_subparsers()

    cmd = sub.add_parser("convert")
    cmd.add_argument("input")
    cmd.add_argument("output")
    cmd.add_argument("-f", "--format", choices=["yaml", "json"], default=None)

    def cmd_convert(args):
        output = Path(args.output)
        loader = loader_prepare(args, session_factory)
        input_ = yarl.URL(args.input)
        data = loader.get(aiopenapi3.plugin.Plugins([]), input_)

        format = args.format or output.suffix[1:]
        assert format in ["yaml", "json"], f"f:{format} a:{args.format} s:{output.suffix}"

        with output.open("wt") as f:
            if format == "yaml":
                yaml.safe_dump(data, f)
            elif format == "json":
                json.dump(data, f)

    cmd.set_defaults(func=cmd_convert)

    cmd = sub.add_parser("call")
    cmd.add_argument("input")
    cmd.add_argument("operationId")
    cmd.add_argument("-m", "--method")
    cmd.add_argument("-b", "--base-url")
    cmd.add_argument("-a", "--authenticate")
    cmd.add_argument("-p", "--parameters")
    cmd.add_argument("-d", "--data")
    cmd.add_argument("-f", "--format")

    def cmd_call(args):
        loader = loader_prepare(args, session_factory)

        def prepare_arg(value):
            if value:
                if value[0] == "@":
                    with Path(value[1:]).open("rt") as f:
                        data = json.load(f)
                else:
                    data = json.loads(value)
            else:
                data = None
            return data

        auth = prepare_arg(args.authenticate)
        parameters = prepare_arg(args.parameters)
        data = prepare_arg(args.data)

        if args.format:
            expr = jmespath.compile(args.format)
        else:
            expr = None

        if args.cache:
            try:
                cache = Path(args.cache)
                api = OpenAPI.cache_load(cache, plugins, session_factory)
            except FileNotFoundError:
                api = OpenAPI.load_file(
                    args.input, yarl.URL(args.input), loader=loader, plugins=plugins, session_factory=session_factory
                )
                api.cache_store(cache)
        else:
            api = OpenAPI.load_file(
                args.input, yarl.URL(args.input), loader=loader, plugins=plugins, session_factory=session_factory
            )

        if args.base_url:
            api._base_url = yarl.URL(args.base_url)

        if auth:
            api.authenticate(**auth)

        if args.method:
            req = api.createRequest((args.operationId, args.method))
        else:
            req = api.createRequest(args.operationId)

        # validate the body
        if req.data:
            req.data.get_type().model_validate(data)

        try:
            headers, ret, response = req.request(parameters=parameters, data=data)
        except aiopenapi3.errors.ResponseSchemaError as e:
            print(e.response.json())
            print(e.response.headers)
            return

        obj = response.json()
        if args.format:
            obj = expr.search(obj)

        print(json.dumps(obj, indent=2, sort_keys=True))

    cmd.set_defaults(func=cmd_call)

    cmd = sub.add_parser("validate")
    cmd.add_argument("input")

    def cmd_validate(args):
        loader = loader_prepare(args, session_factory)

        try:
            begin = datetime.datetime.now()
            try:
                api = OpenAPI.load_file(args.input, yarl.URL(args.input), plugins=plugins, loader=loader)
            except aiopenapi3.errors.ReferenceResolutionError as e0:
                print(f"{e0} {e0.document} {e0.element}")
                return
            end = datetime.datetime.now()
            duration = end - begin
        except ValueError as e:
            logg.exception(e)
        else:
            if args.verbose:
                schema_display_stats(api, duration)
            print("OK")

    cmd.set_defaults(func=cmd_validate)

    if argv:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    plugins = plugins_load(args.input, args.plugins or [])

    def log_(s):
        if args.verbose:
            print(s, file=sys.stderr)

    log = log_

    if args.profile:
        pr = cProfile.Profile()
        pr.enable()

    if args.tracemalloc:
        tracemalloc.start()

    def session_factory(*args_, **kwargs) -> httpx.Client:
        return httpx.Client(*args_, verify=args.disable_ssl_validation is False, **kwargs)

    if args.func:
        args.func(args)
    else:
        parser.show_help()

    if args.tracemalloc:
        tm = tracemalloc.take_snapshot()
        tracemalloc.stop()
        tm_display_top(tm, limit=25)

    if args.profile:
        pr.disable()
        pr_display_top(pr)
        if args.profile_file:
            pr.dump_stats(args.profile_file)
