import argparse
import sys

import yaml
import yarl

if sys.version_info >= (3, 9):
    from pathlib import Path
else:
    from pathlib3x import Path

from .openapi import OpenAPI

from .loader import FileSystemLoader, YAMLCompatibilityLoader, remove_implicit_resolver


class DefaultLoader(yaml.SafeLoader):
    @classmethod
    def remove_implicit_resolver(cls, tag_to_remove):
        remove_implicit_resolver(cls, tag_to_remove)


def main(argv=None):
    parser = argparse.ArgumentParser("aiopenapi3", description="Swagger 2.0, OpenAPI 3.0, OpenAPI 3.1 validator")
    parser.add_argument("name")
    parser.add_argument(
        "-C",
        "--yaml-compatibility",
        action="store_true",
        default=False,
        help="disables type coercion for yaml types such as datetime, bool …",
    )
    parser.add_argument(
        "-D",
        "--yaml-disable-tag",
        nargs="?",
        type=str,
        action="append",
        default=[],
        help="disable this tag from the YAML loader",
    )
    parser.add_argument("-l", "--yaml-list-tags", action="store_true", default=False, help="list tags")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="be verbose")

    if argv:
        args = parser.parse_args(argv)
    else:
        args = parser.parse_args()

    def log(s):
        if args.verbose:
            print(s, file=sys.stderr)

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

    try:
        OpenAPI.load_file(args.name, yarl.URL(args.name), loader=FileSystemLoader(Path().cwd(), yload=ylc))
    except ValueError as e:
        print(e)
    else:
        print("OK")
