"""command line entry point for research and protocol sealing."""

from __future__ import annotations

import argparse

from .protocol import seal
from .report import generate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("report", "seal", "paper", "paper-status"))
    parser.add_argument("--dev-only", action="store_true")
    args = parser.parse_args()
    if args.command == "seal":
        seal()
        print("sealed protocol.json")
    elif args.command == "paper":
        import json

        from .paper import record_once

        print(json.dumps(record_once(), sort_keys=True))
    elif args.command == "paper-status":
        import json

        from .paper import status

        print(json.dumps(status(), sort_keys=True))
    else:
        print(generate(development_only=args.dev_only))


if __name__ == "__main__":
    main()
