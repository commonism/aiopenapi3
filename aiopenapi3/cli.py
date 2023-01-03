import argparse
import datetime
import sys
import json
import itertools

from pstats import SortKey
import pstats
import io
import importlib.util
import cProfile
import tracemalloc
import linecache

import yaml
import yarl
import httpx

import aiopenapi3.plugin


if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from .openapi import OpenAPI

from .loader import ChainLoader, RedirectLoader, WebLoader, YAMLCompatibilityLoader, remove_implicit_resolver
import aiopenapi3.loader


class DefaultLoader(yaml.SafeLoader):
    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        remove_implicit_resolver(cls, tag_to_remove)


log = None


def loader_prepare(args):
    ylc = DefaultLoader

    if args.yaml_compatibility:
        ylc = YAMLCompatibilityLoader

    for t in args.yaml_disable_tag:
        log(f"removing {t}")
        ylc.remove_implicit_resolver(t)

    if args.yaml_list_tags:
        tags = set()
        for v in ylc.yaml_implicit_resolvers.values():
            tags |= set([i[0] for i in v])
        log("tags:")
        log("\t" + "\n\t".join(sorted(tags)) + "\n")

    path = yarl.URL(args.input)
    if path.scheme in ["http", "https"]:

        def session_factory(*args, **kwargs) -> httpx.Client:
            return httpx.Client(*args, verify=False, **kwargs)

        loader = WebLoader(baseurl=path.with_path("/").with_query({}), yload=ylc, session_factory=session_factory)
    else:
        loader = ChainLoader([RedirectLoader(Path(l).expanduser(), yload=ylc) for l in args.locations])

    return loader, ylc


def loader_args(cmd):
    cmd.add_argument(
        "-C",
        "--yaml-compatibility",
        action="store_true",
        default=False,
        help="disables type coercion for yaml types such as datetime, bool …",
    )
    cmd.add_argument(
        "-D",
        "--yaml-disable-tag",
        nargs="?",
        type=str,
        action="append",
        default=[],
        help="disable this tag from the YAML loader",
    )
    cmd.add_argument("-l", "--yaml-list-tags", action="store_true", default=False, help="list tags")


def main(argv=None):
    global log
    parser = argparse.ArgumentParser("aiopenapi3", description="Swagger 2.0, OpenAPI 3.0, OpenAPI 3.1 validator")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="be verbose")
    parser.add_argument("-p", "--profile", action="store_true", default=False)
    parser.add_argument("-t", "--tracemalloc", action="store_true", default=False)
    parser.add_argument("-L", "--locations", action="append")
    sub = parser.add_subparsers()

    cmd = sub.add_parser("convert")
    cmd.add_argument("input")
    cmd.add_argument("output")
    cmd.add_argument("-f", "--format", choices=["yaml", "json"], default=None)
    loader_args(cmd)

    def cmd_convert(args):
        output = Path(args.output)
        loader, ylc = loader_prepare(args)
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
    cmd.add_argument("operationId")
    cmd.add_argument("-a", "--authenticate")
    cmd.add_argument("-p", "--parameters")
    cmd.add_argument("-d", "--data")
    cmd.add_argument("-f", "--format")

    def cmd_call(args):
        loader, _ = loader_prepare(args)

        def prepare_arg(value):
            if value:
                if value[0] == "@":
                    with Path(value[1:]).open("rt") as f:
                        data = json.load(f)
                else:
                    data = json.loads(args.authenticate)
            else:
                data = None
            return data

        auth = prepare_arg(args.authenticate)
        parameters = prepare_arg(args.parameters)
        data = prepare_arg(args.data)

        api = OpenAPI.load_file(args.name, yarl.URL(args.name), loader=loader)
        if auth:
            api.authenticate(**auth)

        req = api.createRequest(args.operationId)
        headers, ret, response = req.request(parameters=parameters, data=data)
        print(ret)

    cmd.set_defaults(func=cmd_call)

    cmd = sub.add_parser("validate")
    loader_args(cmd)
    cmd.add_argument("input")

    def cmd_validate(args):
        loader, ylc = loader_prepare(args)

        try:
            begin = datetime.datetime.now()
            api = OpenAPI.load_file(args.input, yarl.URL(args.input), plugins=plugins, loader=loader)
            end = datetime.datetime.now()
            duration = end - begin
        except ValueError as e:
            print(e)
        else:
            if args.verbose:
                operations = list(
                    itertools.chain.from_iterable(
                        map(
                            lambda x: list(
                                filter(lambda x: x, [x.delete, x.get, x.head, x.options, x.patch, x.post, x.put])
                            ),
                            api.paths._paths.values(),
                        )
                    )
                )
                print(f"…  {duration} (processing time)")
                print(f"… {len(operations)=}")
                operations = list(filter(lambda x: x.operationId, operations))
                print(f"… {len(operations)=} (with operationId)")

                def schemaof(x):
                    if isinstance(api._root, aiopenapi3.v20.Root):
                        return x.definitions
                    else:
                        return x.components.schemas

                ss = 0
                for idx, (name, v) in enumerate(api._documents.items()):
                    ss += len(schemaof(v))
                    print(f"… {idx} {name}: {len(schemaof(v))}")
                print(f"… {ss=}")

            print("OK")

    cmd.set_defaults(func=cmd_validate)

    if argv:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    def log_(s):
        if args.verbose:
            print(s, file=sys.stderr)

    log = log_

    if args.profile:
        pr = cProfile.Profile()
        pr.enable()

    if args.tracemalloc:
        tracemalloc.start()

    if args.func:
        args.func(args)
    else:
        parser.show_help()

    if args.tracemalloc:
        tm = tracemalloc.take_snapshot()
        tracemalloc.stop()

        def display_top(snapshot, key_type="lineno", limit=10):
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

        display_top(tm, limit=25)

    if args.profile:
        pr.disable()
        s = io.StringIO()
        sortby = SortKey.CUMULATIVE
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
