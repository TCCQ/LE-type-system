from __future__ import annotations

import argparse
import sys
import tempfile

from Ast import Module
from Lexer import LexError
from Parser import ParseError, parse
from Pretty import print_input, print_output_ec, print_output_max, print_output_min
from Proof import prove_proc
from Typecheck import TypecheckError, check_program
from Types import ClearenceLabel, OutputType, VarDeriv, ProcedureDeriv


class IllFormedTree(Exception):
    pass


def _format_location(filename: str, line: int, column: int) -> str:
    return f"{filename}:{line}:{column}"


def _public_module_vars(m: Module[OutputType]) -> list[str]:
    mod = m.name.name
    return [
        f"{mod}.{v.name}"
        for v in m.defns
        if isinstance(v.t.d, VarDeriv)
        and isinstance(v.t.d.l, ClearenceLabel)
        and v.t.d.l.public
    ]


def _render_output(modules: list[Module[OutputType]]) -> str:
    sections: list[str] = []
    for m in modules:
        body = print_output_ec([m])
        publics = _public_module_vars(m)
        equivs: list[str] = []
        for p in m.procs:
            if isinstance(p.t.d, ProcedureDeriv):
                equivs.append(prove_proc(f"{m.name.name}.{p.name.name}", publics, p.t.d))
            else:
                raise IllFormedTree
        sections.append("\n".join([body, *equivs]))
    return (
        "prover [].\nrequire import AllCore.\nrequire import IntDiv.\n\n"
        + "\n\n".join(sections) + "\n" if sections else ""
    )


def _write_temp(content: str) -> str:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ec", prefix="le-", delete=False, encoding="utf-8"
    ) as f:
        f.write(content)
        return f.name


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="le-parser",
        description="Parse and typecheck an LE-language program.",
    )
    ap.add_argument("file", help="source file, or '-' for stdin")
    ap.add_argument(
        "--dump-ast",
        action="store_true",
        help="pretty-print the parsed AST in source syntax",
    )
    ap.add_argument(
        "--dump-output-ast",
        action="store_true",
        help="pretty-print the typechecked AST in source syntax",
    )
    ap.add_argument(
        "--dump-deriv-ast",
        action="store_true",
        help="pretty-print the typechecked AST with full derivation trees",
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
        print(print_input(modules))

    try:
        checked = check_program(modules)
    except TypecheckError as e:
        print(f"{filename}: error: {e}", file=sys.stderr)
        return 1

    try:
        path = _write_temp(_render_output(checked))
    except OSError as e:
        print(f"{filename}: error: cannot write temporary output: {e}",
              file=sys.stderr)
        return 1

    dumps: list[str] = []
    if args.dump_output_ast:
        dumps.append(print_output_min(checked))
    if args.dump_deriv_ast:
        dumps.append(print_output_max(checked))
    if dumps:
        if args.dump_ast:
            print()
        print("\n\n".join(dumps))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
