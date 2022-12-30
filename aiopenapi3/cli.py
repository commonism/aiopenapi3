import argparse
import sys
import json

import yaml
import yarl

import aiopenapi3.plugin

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from .openapi import OpenAPI

from .loader import FileSystemLoader, WebLoader, YAMLCompatibilityLoader, remove_implicit_resolver


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
        loader = WebLoader(baseurl=path.with_path("/").with_query({}), yload=ylc)
    else:
        loader = FileSystemLoader(Path().cwd(), yload=ylc)

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

    def cmd_validate(argv):
        loader, ylc = loader_prepare()

        try:
            OpenAPI.load_file(args.name, yarl.URL(args.name), loader=loader)
        except ValueError as e:
            print(e)
        else:
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

    if args.func:
        args.func(args)
    else:
        parser.show_help()
