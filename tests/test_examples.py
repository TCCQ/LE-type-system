from __future__ import annotations

import pathlib
import sys

import pytest

# Ensure the project root is importable regardless of where pytest is launched from.
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Ast import (
    Assign,
    Block,
    If,
    Literal,
    Module,
    Opt,
    ProcCall,
    Return,
    Var,
    While,
)
from Lexer import LexError
from Parser import ParseError, parse


EXAMPLES = PROJECT_ROOT / "tests"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load(name: str) -> str:
    path = EXAMPLES / name
    assert path.is_file(), f"missing example file: {path}"
    return path.read_text(encoding="utf-8")


def _parse_good(name: str) -> list[Module]:
    mods = parse(_load(name))
    assert isinstance(mods, list) and len(mods) == 1, \
        f"{name}: expected exactly one module, got {mods!r}"
    return mods


# ---------------------------------------------------------------------------
# good_simple.le
# ---------------------------------------------------------------------------

def test_good_simple_module_shape():
    [mod] = _parse_good("good_simple.le")

    assert isinstance(mod.name, Var)
    assert mod.name.name == "Crypto"
    assert [d.name for d in mod.defns] == ["key", "counter"]
    assert [p.name.name for p in mod.procs] == ["encrypt"]


def test_good_simple_encrypt_body():
    [mod] = _parse_good("good_simple.le")
    [proc] = mod.procs

    assert [a.name for a in proc.args] == ["m"]

    block = proc.body
    assert isinstance(block, Block)
    assert [d.name for d in block.localDefs] == ["out"]
    assert len(block.statements) == 2

    # out <- m + key;
    assign, ret = block.statements
    assert isinstance(assign, Assign)
    assert isinstance(assign.left, Var) and assign.left.name == "out"
    assert isinstance(assign.right, Opt) and assign.right.name == "+"
    assert isinstance(assign.right.left, Var) and assign.right.left.name == "m"
    assert isinstance(assign.right.right, Var) and assign.right.right.name == "key"

    # return out;
    assert isinstance(ret, Return)
    assert isinstance(ret.val, Var) and ret.val.name == "out"


# ---------------------------------------------------------------------------
# good_full.le
# ---------------------------------------------------------------------------

def test_good_full_module_shape():
    [mod] = _parse_good("good_full.le")

    assert mod.name.name == "M"
    assert [d.name for d in mod.defns] == ["g", "result"]
    assert [p.name.name for p in mod.procs] == ["compute", "helper", "go"]


def test_good_full_compute_statement_layout():
    [mod] = _parse_good("good_full.le")
    compute = next(p for p in mod.procs if p.name.name == "compute")

    # source: acc<-0; i<-0; while(...); if(...)
    kinds = [type(s).__name__ for s in compute.body.statements]
    assert kinds == ["Assign", "Assign", "While", "If"]
    assert [d.name for d in compute.body.localDefs] == ["acc", "i"]


def test_good_full_elif_is_desugared_into_nested_if():
    """`elif` in the source becomes a nested `If` in the outer `If`'s fArm."""
    [mod] = _parse_good("good_full.le")
    compute = next(p for p in mod.procs if p.name.name == "compute")
    outer_if = compute.body.statements[-1]

    assert isinstance(outer_if, If)
    assert isinstance(outer_if.fArm, Block)
    assert len(outer_if.fArm.statements) == 1
    assert isinstance(outer_if.fArm.statements[0], If)


def test_good_full_helper_and_go():
    [mod] = _parse_good("good_full.le")
    helper = next(p for p in mod.procs if p.name.name == "helper")
    go = next(p for p in mod.procs if p.name.name == "go")

    # helper: var tmp; tmp<-x-1; return tmp;
    assert [d.name for d in helper.body.localDefs] == ["tmp"]
    assert [type(s).__name__ for s in helper.body.statements] == ["Assign", "Return"]

    # go: result <@ helper(5); return result;
    assert go.body.localDefs == []
    assert [type(s).__name__ for s in go.body.statements] == ["ProcCall", "Return"]

    call, ret = go.body.statements
    assert isinstance(call, ProcCall)
    assert call.func.name == "helper"
    assert len(call.args) == 1
    assert isinstance(call.args[0], Literal)
    assert call.args[0].value == 5

    assert isinstance(ret, Return)
    assert isinstance(ret.val, Var) and ret.val.name == "result"


# ---------------------------------------------------------------------------
# bad files
# ---------------------------------------------------------------------------
# NOTE: we assert on `line` and on a substring of the message, but not on the
# column.  Line numbers are stable across the source; columns are cheap to
# get wrong in a hand-written test and would make the suite brittle for
# very little diagnostic value.  Print `err.column` once when adding a new
# case if you want to check it, then add it here.

@pytest.mark.parametrize(
    "filename, exc_type, line, message_substr",
    [
        ("bad_theory.le",   ParseError, 1, "theory blocks are not supported"),
        ("bad_operator.le", LexError,   4, "exponentiation '^'"),
        ("bad_syntax.le",   ParseError, 3,
         "expected ';' after module variable definition"),
    ],
)
def test_bad_file(filename, exc_type, line, message_substr):
    with pytest.raises(exc_type) as exc_info:
        parse(_load(filename))

    err = exc_info.value
    assert err.line == line, (
        f"{filename}: expected error on line {line}, got line {err.line} "
        f"({err})"
    )
    assert message_substr in str(err), (
        f"{filename}: expected {message_substr!r} in message {str(err)!r}"
    )