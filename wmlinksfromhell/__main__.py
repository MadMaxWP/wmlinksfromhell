import argparse
import json

from .resolver import Resolver

parser = argparse.ArgumentParser(prog="python -m wmlinksfromhell")
subparsers = parser.add_subparsers(dest="command", required=True)
resolve_parser = subparsers.add_parser("resolve")
resolve_parser.add_argument("value")
resolve_parser.add_argument("--source")
resolve_parser.add_argument("--json", action="store_true")
args = parser.parse_args()

if args.command == "resolve":
    result = Resolver().resolve(args.value, source=args.source)
    print(json.dumps(result.as_dict(), sort_keys=True, ensure_ascii=False) if args.json else result.as_dict())
