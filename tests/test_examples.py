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
from Pretty import print_input, print_output_max, print_output_min
from Typecheck import ClearanceError, TypeMismatchError, check_program


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
    assert call.dst.name == "result"
    assert call.func.name == "helper"
    assert len(call.args) == 1
    assert isinstance(call.args[0], Literal)
    assert call.args[0].value == 5

    assert isinstance(ret, Return)
    assert isinstance(ret.val, Var) and ret.val.name == "result"


# ---------------------------------------------------------------------------
# pretty printing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", ["good_simple.le", "good_full.le"])
def test_input_printer_round_trips(filename):
    rendered = print_input(_parse_good(filename))
    assert print_input(parse(rendered)) == rendered


def test_output_printer_matches_input():
    parsed = _parse_good("good_full.le")
    rendered = print_input(parsed)

    checked = check_program(parsed)
    assert print_output_min(checked) == rendered
    assert print_output_min(check_program(parse(rendered))) == rendered


def test_deriv_printer_includes_derivation_tree():
    parsed = _parse_good("good_full.le")
    rendered = print_output_max(check_program(parsed))
    assert "ModuleDeriv" in rendered
    assert "WhileDeriv" in rendered
    assert "IfDeriv" in rendered


# ---------------------------------------------------------------------------
# typechecking
# ---------------------------------------------------------------------------

def test_typecheck_rejects_private_to_public_assignment():
    with pytest.raises(ClearanceError):
        check_program(_parse_good("good_simple.le"))


def test_typecheck_rejects_mismatched_assignment_types():
    parsed = parse("""
module M = {
    proc f() : int = {
        var x : int;
        var b : bool;
        x <- b;
        return x;
    }
}
""")
    with pytest.raises(TypeMismatchError):
        check_program(parsed)


def test_typecheck_rejects_mismatched_call_destination():
    parsed = parse("""
module M = {
    proc f() : bool = {
        return true;
    }
    proc g() : int = {
        var x : int;
        x <@ f();
        return x;
    }
}
""")
    with pytest.raises(TypeMismatchError):
        check_program(parsed)


def test_typecheck_allows_public_to_private_assignment():
    parsed = parse("""
module M = {
    var secret : int :: private;
    var pub : int :: public;
    proc f() : int = {
        secret <- pub;
        return secret;
    }
}
""")
    check_program(parsed)


def test_typecheck_rejects_low_to_low_assignment_in_high_if():
    parsed = parse("""
module M = {
    var secret : int :: private;
    proc f() : int = {
        var x : int;
        if (secret > 0) {
            x <- 1;
        }
        return x;
    }
}
""")
    with pytest.raises(ClearanceError):
        check_program(parsed)


def test_typecheck_rejects_low_to_low_assignment_in_high_while():
    parsed = parse("""
module M = {
    var secret : int :: private;
    proc f() : int = {
        var x : int;
        while (secret > 0) {
            x <- 1;
        }
        return x;
    }
}
""")
    with pytest.raises(ClearanceError):
        check_program(parsed)


def test_typecheck_rejects_low_to_low_assignment_in_high_elif():
    parsed = parse("""
module M = {
    var secret : int :: private;
    var pub : int :: public;
    proc f() : int = {
        var x : int;
        if (secret > 0) {
            secret <- 1;
        } elif (pub > 0) {
            x <- 1;
        }
        return x;
    }
}
""")
    with pytest.raises(ClearanceError):
        check_program(parsed)


def test_typecheck_rejects_call_in_high_pc():
    parsed = parse("""
module M = {
    var secret : int :: private;
    proc g() : int = {
        return 1;
    }
    proc f() : int = {
        var x : int;
        if (secret > 0) {
            x <@ g();
        }
        return x;
    }
}
""")
    with pytest.raises(ClearanceError):
        check_program(parsed)


def test_typecheck_uses_pc_adjust_and_resets_pc_after_control_flow():
    parsed = parse("""
module M = {
    var secret : int :: private;
    var pub : int :: public;
    proc f() : int = {
        var x : int;
        if (secret > 0) {
            secret <- pub;
        }
        x <- 1;
        while (secret > 0) {
            secret <- pub;
        }
        x <- 2;
        return x;
    }
}
""")
    checked = check_program(parsed)
    assert "PCAdjust" in print_output_max(checked)


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