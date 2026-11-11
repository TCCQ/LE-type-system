from __future__ import annotations

import argparse
import sys
from pprint import pprint

from Lexer import LexError
from Parser import ParseError, parse
from Typecheck import TypecheckError, check_program


def _format_location(filename: str, line: int, column: int) -> str:
    return f"{filename}:{line}:{column}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="le-parser",
        description="Parse and typecheck an LE-language program.",
    )
    ap.add_argument("file", help="source file, or '-' for stdin")
    ap.add_argument(
        "--dump-ast", action="store_true", help="pretty-print the parsed AST"
    )
    ap.add_argument(
        "--dump-output-ast",
        action="store_true",
        help="pretty-print the typechecked AST",
    )
    args = ap.parse_args(argv)

    if args.file == "-":
        source = sys.stdin.read()
        filename = "<stdin>"
    else:
        filename = args.file
        try:
            with open(args.file, "r") as f:
                source = f.read()
        except OSError as e:
            print(f"{filename}: error: cannot read file: {e}", file=sys.stderr)
            return 1

    try:
        modules = parse(source)
    except (LexError, ParseError) as e:
        print(f"{_format_location(filename, e.line, e.column)}: error: {e}",
              file=sys.stderr)
        return 1

    if args.dump_ast:
        pprint(modules)

    try:
        checked = check_program(modules)
    except TypecheckError as e:
        print(f"{filename}: error: {e}", file=sys.stderr)
        return 1

    if args.dump_output_ast:
        pprint(checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())