from __future__ import annotations

import pathlib
import sys
from collections.abc import Iterator

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
from Pretty import print_input, print_output_ec, print_output_max, print_output_min
from Typecheck import (
    ClearanceError,
    DuplicateNameError,
    TypeMismatchError,
    UnknownTypeError,
    check_program,
)
from Types import (
    AssignsDeriv,
    BlockDeriv,
    IfDeriv,
    OrderDeriv,
    SkipDeriv,
    StatementDeriv,
    WhileDeriv,
)


# ---------------------------------------------------------------------------
# inline example sources
# ---------------------------------------------------------------------------

GOOD_SIMPLE = """\
module Crypto = {
    var key : int :: private;
    var counter : int :: public;

    proc encrypt(m : int) : int = {
        var out : int;
        out <- m + key;
        return out;
    }
}
"""

GOOD_FULL = """\
module M = {
    var g : int :: public;
    var result : int :: private;

    proc compute(n : int) : int = {
        var acc : int;
        var i : int;
        acc <- 0;
        i <- 0;
        while (i < n) {
            acc <- acc + i;
            i <- i + 1;
        }

        if (acc > 100) {
            return acc;
        } elif (acc > 50) {
            return acc * 2;
        } else {
            return 0;
        }
    }

    proc helper(x : int) : int = {
        var tmp : int;
        tmp <- x - 1;
        return tmp;
    }

    proc go() : int = {
        result <@ helper(5);
        return result;
    }
}
"""

BAD_THEORY = """theory Example.
require import Int.
module M = {
    var x : int :: private;
}
end Example.
"""

BAD_OPERATOR = """module M = {
    var x : int :: public;
    proc f(y : int) : int = {
        x <- y ^ 1;
        return x;
    }
}
"""

BAD_SYNTAX = """module M = {
    var x : int :: public
    proc f(y : int) : int = { return y; }
}
"""

COUNTEREXAMPLE_ASSIGN_THEN_IF = """\
module M = {
    var a : int :: public;
    var b : int :: public;
    var c : int :: public;

    proc f() : unit = {
        a <- 0;
        if (a < b) {
            c <- 1;
        }
    }
}
"""

COUNTEREXAMPLE_DUPLICATE_MODULE = """\
module M = {
    var a : int :: public;

    proc f() : unit = {
        a <- 1;
    }
}

module M = {
    var b : int :: public;

    proc g() : unit = {
        b <- 1;
    }
}
"""

COUNTEREXAMPLE_DUPLICATE_MODULE_VAR = """\
module M = {
    var a : int :: public;
    var a : int :: public;

    proc f() : unit = {
        a <- 1;
    }
}
"""

COUNTEREXAMPLE_DUPLICATE_PROC = """\
module M = {
    var a : int :: public;

    proc f() : unit = {
        a <- 1;
    }

    proc f() : unit = {
        a <- 2;
    }
}
"""

COUNTEREXAMPLE_IF_THEN_ASSIGN = """\
module M = {
    var a : int :: public;
    var b : int :: public;
    var c : int :: public;

    proc f() : unit = {
        if (a < b) {
            c <- 1;
        }
        a <- 0;
    }
}
"""

COUNTEREXAMPLE_MISSING_RETURN = """\
module M = {
    var a : int :: public;

    proc f() : int = {
    }
}
"""

COUNTEREXAMPLE_NO_PUBLIC_VARS = """\
module M = {
    proc f() : unit = {
    }
}
"""

COUNTEREXAMPLE_PROC_CALL = """\
module M = {
    var a : int :: public;

    proc g() : int = {
        return a + 1;
    }

    proc f() : unit = {
        a <@ g();
    }
}
"""

COUNTEREXAMPLE_UNKNOWN_TYPE = """\
module M = {
    var u : mystery :: public;

    proc f() : unit = {
    }
}
"""

COUNTEREXAMPLE_WHILE_ASSIGN_IF = """\
module M = {
    var a : int :: public;
    var b : int :: public;
    var c : int :: public;

    proc f() : unit = {
        while (a < b) {
            a <- a + 1;
        }
        a <- 0;
        if (a < b) {
            c <- 1;
        }
    }
}
"""

COUNTEREXAMPLE_WRONG_RETURN_TYPE = """\
module M = {
    var a : int :: public;

    proc f() : unit = {
        return a;
    }
}
"""


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _parse_single(source: str) -> list[Module]:
    mods = parse(source)
    assert isinstance(mods, list) and len(mods) == 1, \
        f"expected exactly one module, got {mods!r}"
    return mods


def _assignment_derivations(stmt: StatementDeriv) -> Iterator[AssignsDeriv]:
    if isinstance(stmt, AssignsDeriv):
        yield stmt
        yield from _assignment_derivations(stmt.tail)
    elif isinstance(stmt, IfDeriv):
        yield from _assignment_derivations(stmt.ld.statements)
        yield from _assignment_derivations(stmt.rd.statements)
        yield from _assignment_derivations(stmt.then)
    elif isinstance(stmt, WhileDeriv):
        yield from _assignment_derivations(stmt.prior)
        yield from _assignment_derivations(stmt.bd.statements)
    elif isinstance(stmt, OrderDeriv):
        yield from _assignment_derivations(stmt.first)
        yield from _assignment_derivations(stmt.second)


# ---------------------------------------------------------------------------
# good_simple
# ---------------------------------------------------------------------------

def test_good_simple_module_shape():
    [mod] = _parse_single(GOOD_SIMPLE)

    assert isinstance(mod.name, Var)
    assert mod.name.name == "Crypto"
    assert [d.name for d in mod.defns] == ["key", "counter"]
    assert [p.name.name for p in mod.procs] == ["encrypt"]


def test_good_simple_encrypt_body():
    [mod] = _parse_single(GOOD_SIMPLE)
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
# good_full
# ---------------------------------------------------------------------------

def test_good_full_module_shape():
    [mod] = _parse_single(GOOD_FULL)

    assert mod.name.name == "M"
    assert [d.name for d in mod.defns] == ["g", "result"]
    assert [p.name.name for p in mod.procs] == ["compute", "helper", "go"]


def test_good_full_compute_statement_layout():
    [mod] = _parse_single(GOOD_FULL)
    compute = next(p for p in mod.procs if p.name.name == "compute")

    # source: acc<-0; i<-0; while(...); if(...)
    kinds = [type(s).__name__ for s in compute.body.statements]
    assert kinds == ["Assign", "Assign", "While", "If"]
    assert [d.name for d in compute.body.localDefs] == ["acc", "i"]


def test_good_full_elif_is_desugared_into_nested_if():
    """`elif` in the source becomes a nested `If` in the outer `If`'s fArm."""
    [mod] = _parse_single(GOOD_FULL)
    compute = next(p for p in mod.procs if p.name.name == "compute")
    outer_if = compute.body.statements[-1]

    assert isinstance(outer_if, If)
    assert isinstance(outer_if.fArm, Block)
    assert len(outer_if.fArm.statements) == 1
    assert isinstance(outer_if.fArm.statements[0], If)


def test_good_full_helper_and_go():
    [mod] = _parse_single(GOOD_FULL)
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

@pytest.mark.parametrize(
    "source",
    [
        pytest.param(GOOD_SIMPLE, id="good_simple"),
        pytest.param(GOOD_FULL, id="good_full"),
    ],
)
def test_input_printer_round_trips(source):
    rendered = print_input(_parse_single(source))
    assert print_input(parse(rendered)) == rendered


def test_output_printer_matches_input():
    parsed = _parse_single(GOOD_FULL)
    rendered = print_input(parsed)

    checked = check_program(parsed)
    assert print_output_min(checked) == rendered
    assert print_output_min(check_program(parse(rendered))) == rendered


def test_ec_printer_matches_easycrypt_module_syntax():
    parsed = parse("""
module M = {
    var x : int :: private;
    var y : int :: public;
    var z : int :: public;
    proc f() : unit = {
        if (y < z) {
            x <- x + y;
        } elif (y = z) {
        } else {
            while (z < y) {
                x <- x + y;
                y <- y - 1;
            }
        }
    }
}
""")
    rendered = print_output_ec(check_program(parsed))

    assert "var x : int  (* private *)" in rendered
    assert "var y : int  (* public *)" in rendered
    assert ":: " not in rendered
    assert "elif (y = z)" in rendered
    assert rendered.endswith("}.")


def test_ec_printer_respells_operators():
    parsed = parse("""
module N = {
    var a : int :: public;
    var b : int :: public;
    var c : int :: public;
    proc f() : unit = {
        var x : int;
        x <- (a / b) + (a %/ b);
        if (b > c && a >= c || !(b = c)) {
            c <- x;
        }
    }
}
""")
    rendered = print_output_ec(check_program(parsed))

    assert "x <- a %/ b + a %% b;" in rendered
    assert "if (c < b /\\ c <= a \\/ !(b = c)) {" in rendered


def test_ec_printer_marks_unsupported_early_return():
    parsed = parse("""
module M = {
    proc f() : int = {
        if (true) {
            return 1;
        }
        return 0;
    }
}
""")
    rendered = print_output_ec(check_program(parsed))

    assert "TODO: EasyCrypt only allows a single return" in rendered
    assert rendered.endswith("return 0;\n    }\n}.")


def test_assignment_before_if_uses_before_true_with_empty_if_tail():
    parsed = parse(COUNTEREXAMPLE_ASSIGN_THEN_IF)
    [mod] = check_program(parsed)
    body = mod.procs[0].body.t.d
    assert isinstance(body, BlockDeriv)

    stmt = body.statements
    assert isinstance(stmt, AssignsDeriv)
    assert stmt.before is True
    assert isinstance(stmt.tail, IfDeriv)
    assert isinstance(stmt.tail.then, SkipDeriv)


def test_single_assignment_while_body_uses_sp():
    parsed = parse("""
module M = {
    var a : int :: public;
    var b : int :: public;
    proc f() : unit = {
        while (a < b) {
            a <- a + 1;
        }
    }
}
""")
    rendered = print_output_max(check_program(parsed))

    # before=True is the `sp` branch in Proof._prove_statement.
    assert "AssignsDeriv(" in rendered
    assert "before=True" in rendered
    assert "before=False" not in rendered


def test_deriv_printer_includes_derivation_tree():
    parsed = _parse_single(GOOD_FULL)
    rendered = print_output_max(check_program(parsed))
    assert "ModuleDeriv" in rendered
    assert "WhileDeriv" in rendered
    assert "IfDeriv" in rendered


# ---------------------------------------------------------------------------
# typechecking
# ---------------------------------------------------------------------------

def test_typecheck_rejects_private_to_public_assignment():
    with pytest.raises(ClearanceError):
        check_program(_parse_single(GOOD_SIMPLE))


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


def test_typecheck_rejects_duplicate_module_variable():
    parsed = parse("""
module M = {
    var a : int :: public;
    var a : bool :: private;
    proc f() : unit = {
    }
}
""")
    with pytest.raises(DuplicateNameError):
        check_program(parsed)


def test_typecheck_rejects_duplicate_procedure():
    parsed = parse("""
module M = {
    proc f() : unit = {
    }
    proc f() : unit = {
    }
}
""")
    with pytest.raises(DuplicateNameError):
        check_program(parsed)


def test_typecheck_rejects_duplicate_module():
    parsed = parse("""
module M = {
    proc f() : unit = {
    }
}
module M = {
    proc g() : unit = {
    }
}
""")
    with pytest.raises(DuplicateNameError):
        check_program(parsed)


def test_typecheck_rejects_duplicate_arguments():
    parsed = parse("""
module M = {
    proc f(x : int, x : int) : unit = {
    }
}
""")
    with pytest.raises(DuplicateNameError):
        check_program(parsed)


def test_typecheck_rejects_duplicate_local_variables():
    parsed = parse("""
module M = {
    proc f() : unit = {
        var x : int;
        var x : int;
    }
}
""")
    with pytest.raises(DuplicateNameError):
        check_program(parsed)


def test_typecheck_rejects_local_variable_shadowing_argument():
    parsed = parse("""
module M = {
    proc f(x : int) : unit = {
        var x : int;
    }
}
""")
    with pytest.raises(DuplicateNameError):
        check_program(parsed)


@pytest.mark.parametrize(
    "source",
    [
        """
module M = {
    var x : mystery :: public;
    proc f() : unit = {
    }
}
""",
        """
module M = {
    proc f(x : mystery) : unit = {
    }
}
""",
        """
module M = {
    proc f() : mystery = {
    }
}
""",
        """
module M = {
    proc f() : unit = {
        var x : mystery;
    }
}
""",
        """
module M = {
    var x : M.mystery :: public;
    proc f() : unit = {
    }
}
""",
    ],
)
def test_typecheck_rejects_unknown_type_names(source):
    with pytest.raises(UnknownTypeError):
        check_program(parse(source))


def test_typecheck_accepts_known_and_list_types():
    parsed = parse("""
module M = {
    var xs : int list :: public;
    var ys : bool list list :: private;
    proc f(x : int list) : unit = {
        var u : unit;
    }
}
""")
    check_program(parsed)


@pytest.mark.parametrize(
    "source, error",
    [
        pytest.param(
            COUNTEREXAMPLE_DUPLICATE_MODULE_VAR,
            DuplicateNameError,
            id="duplicate_module_var",
        ),
        pytest.param(
            COUNTEREXAMPLE_DUPLICATE_PROC,
            DuplicateNameError,
            id="duplicate_proc",
        ),
        pytest.param(
            COUNTEREXAMPLE_DUPLICATE_MODULE,
            DuplicateNameError,
            id="duplicate_module",
        ),
        pytest.param(
            COUNTEREXAMPLE_UNKNOWN_TYPE,
            UnknownTypeError,
            id="unknown_type",
        ),
    ],
)
def test_counterexample_sources_are_rejected_by_typechecker(source, error):
    with pytest.raises(error):
        check_program(parse(source))


TYPECHECK_OK_SOURCES = [
    ("good_full", GOOD_FULL),
    ("assign_then_if", COUNTEREXAMPLE_ASSIGN_THEN_IF),
    ("if_then_assign", COUNTEREXAMPLE_IF_THEN_ASSIGN),
    ("missing_return", COUNTEREXAMPLE_MISSING_RETURN),
    ("no_public_vars", COUNTEREXAMPLE_NO_PUBLIC_VARS),
    ("proc_call", COUNTEREXAMPLE_PROC_CALL),
    ("while_assign_if", COUNTEREXAMPLE_WHILE_ASSIGN_IF),
    ("wrong_return_type", COUNTEREXAMPLE_WRONG_RETURN_TYPE),
]


@pytest.mark.parametrize("label, source", TYPECHECK_OK_SOURCES)
def test_inline_examples_parse_and_typecheck(label, source):
    check_program(parse(source))


@pytest.mark.parametrize("label, source", TYPECHECK_OK_SOURCES)
def test_assignments_with_empty_tail_never_use_before_false(label, source):
    [mod] = check_program(parse(source))
    for proc in mod.procs:
        for d in _assignment_derivations(proc.body.t.d):
            assert not (isinstance(d.tail, SkipDeriv) and d.before is False), (
                f"{label}: assignment has tail=SkipDeriv and before=False: {d!r}"
            )


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
# bad sources
# ---------------------------------------------------------------------------
# NOTE: we assert on `line` and on a substring of the message, but not on the
# column.  Line numbers are stable across the source; columns are cheap to
# get wrong in a hand-written test and would make the suite brittle for
# very little diagnostic value.  Print `err.column` once when adding a new
# case if you want to check it, then add it here.

@pytest.mark.parametrize(
    "source, exc_type, line, message_substr",
    [
        pytest.param(
            BAD_THEORY,
            ParseError,
            1,
            "theory blocks are not supported",
            id="bad_theory",
        ),
        pytest.param(
            BAD_OPERATOR,
            LexError,
            4,
            "exponentiation '^'",
            id="bad_operator",
        ),
        pytest.param(
            BAD_SYNTAX,
            ParseError,
            3,
            "expected ';' after module variable definition",
            id="bad_syntax",
        ),
    ],
)
def test_bad_source(source, exc_type, line, message_substr):
    with pytest.raises(exc_type) as exc_info:
        parse(source)

    err = exc_info.value
    assert err.line == line, (
        f"expected error on line {line}, got line {err.line} ({err})"
    )
    assert message_substr in str(err), (
        f"expected {message_substr!r} in message {str(err)!r}"
    )
