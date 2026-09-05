import argparse
import sys

from .parser import YamlError, load
from .path import PathError, parse_path, resolve


def _format_value(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="strictpath",
        description="Print the value at a dotted path inside a YAML file.",
    )
    parser.add_argument("file", help="path to the YAML file")
    parser.add_argument("query", help="dotted path, e.g. server.hosts[0].name")
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="tolerate duplicate keys and ambiguous scalars instead of failing",
    )
    parser.add_argument(
        "-d", "--default",
        default=None,
        help="print this instead of failing when the path is missing",
    )
    args = parser.parse_args(argv)

    try:
        with open(args.file, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print("strictpath: {}".format(exc), file=sys.stderr)
        return 2

    try:
        data = load(text, lenient=args.lenient)
    except YamlError as exc:
        print("strictpath: {}".format(exc), file=sys.stderr)
        return 2

    try:
        ops = parse_path(args.query)
    except ValueError as exc:
        print("strictpath: bad path: {}".format(exc), file=sys.stderr)
        return 2

    try:
        value = resolve(data, ops)
    except PathError as exc:
        if args.default is not None:
            print(args.default)
            return 0
        print("strictpath: {}".format(exc), file=sys.stderr)
        return 1

    if isinstance(value, (dict, list)):
        kind = "mapping" if isinstance(value, dict) else "sequence"
        print(
            "strictpath: value at {!r} is a {}, not a scalar".format(args.query, kind),
            file=sys.stderr,
        )
        return 3

    print(_format_value(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
