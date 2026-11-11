from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Callable, cast

from Ast import (
    Assign,
    Block,
    Expr,
    If,
    Literal,
    Module,
    Opt,
    ProcCall,
    Procedure,
    Return,
    Statement,
    Var,
    While,
)
from Types import (
    ClearenceLabel,
    InputType,
    NominalType,
    OutputType,
    VarDeriv,
)

_INDENT = "    "

_PREC = {
    "||": 1,
    "&&": 2,
    "=": 3,
    "<>": 3,
    "<": 4,
    "<=": 4,
    ">": 4,
    ">=": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "/": 6,
    "%/": 6,
}
_ATOM_PREC = 8
_UNARY_PREC = 7


class Printer[T]:
    """Pretty-print an AST whose nodes carry type information T.

    ``ty`` decides how to render a T; ``label`` is used for module variables
    only, since their visibility label is part of the declaration syntax.
    """

    def __init__(
        self,
        ty: Callable[[T], str],
        label: Callable[[T], str] | None = None,
    ):
        self.ty = ty
        self.label = label or (lambda _: "")

    # ------------------------------------------------------------------
    # source-like rendering
    # ------------------------------------------------------------------

    def program(self, modules: list[Module[T]]) -> str:
        return "\n\n".join(self.module(m) for m in modules)

    def module(self, m: Module[T]) -> str:
        body = [
            f"var {d.name} : {self.ty(d.t)}{self.label(d.t)};" for d in m.defns
        ]
        if body and m.procs:
            body.append("")
        for i, p in enumerate(m.procs):
            if i:
                body.append("")
            body.extend(self.procedure(p))
        return "\n".join([f"module {m.name.name} = {{", *self._indent(body), "}"])

    def procedure(self, p: Procedure[T]) -> list[str]:
        args = ", ".join(f"{a.name} : {self.ty(a.t)}" for a in p.args)
        lines = [f"proc {p.name.name}({args}) : {self.ty(p.rt)} = {{"]
        lines.extend(self._indent(self._block_body(p.body)))
        lines.append("}")
        return lines

    def block(self, b: Block[T]) -> list[str]:
        return ["{", *self._indent(self._block_body(b)), "}"]

    def _block_body(self, b: Block[T]) -> list[str]:
        lines = [f"var {d.name} : {self.ty(d.t)};" for d in b.localDefs]
        for s in b.statements:
            lines.extend(self.statement(s))
        return lines

    def statement(self, s: Statement[T]) -> list[str]:
        if isinstance(s, Assign):
            return [f"{s.left.name} <- {self.expression(s.right)};"]
        if isinstance(s, Return):
            return [f"return {self.expression(s.val)};"]
        if isinstance(s, ProcCall):
            args = ", ".join(self.expression(a) for a in s.args)
            return [f"{s.dst.name} <@ {s.func.name}({args});"]
        if isinstance(s, While):
            return [
                f"while ({self.expression(s.condition)}) {{",
                *self._indent(self._block_body(s.body)),
                "}",
            ]
        return self._if(s, "if")

    def _if(self, s: If[T], keyword: str) -> list[str]:
        lines = [
            f"{keyword} ({self.expression(s.condition)}) {{",
            *self._indent(self._block_body(s.tArm)),
            "}",
        ]
        self._if_tail(s.fArm, lines)
        return lines

    def _if_tail(self, arm: Block[T], lines: list[str]) -> None:
        if not arm.localDefs and not arm.statements:
            return
        if (
            not arm.localDefs
            and len(arm.statements) == 1
            and isinstance(arm.statements[0], If)
        ):
            nested = arm.statements[0]
            lines[-1] += f" elif ({self.expression(nested.condition)}) {{"
            lines.extend(self._indent(self._block_body(nested.tArm)))
            lines.append("}")
            self._if_tail(nested.fArm, lines)
            return
        lines[-1] += " else {"
        lines.extend(self._indent(self._block_body(arm)))
        lines.append("}")

    def expression(self, e: Expr[T]) -> str:
        if isinstance(e, Literal):
            if isinstance(e.value, bool):
                return "true" if e.value else "false"
            return str(e.value)
        if isinstance(e, Var):
            return e.name

        if e.left is None:
            inner = self.expression(e.right)
            if isinstance(e.right, Opt):
                inner = f"({inner})"
            return e.name + inner

        prec = _PREC.get(e.name, 0)
        left = self._expr_at(e.left, prec, right=False)
        right = self._expr_at(e.right, prec, right=True)
        return f"{left} {e.name} {right}"

    def _expr_at(self, e: Expr[T], parent: int, right: bool) -> str:
        text = self.expression(e)
        prec = self._prec(e)
        if prec < parent or (right and prec == parent):
            return f"({text})"
        return text

    def _prec(self, e: Expr[T]) -> int:
        if isinstance(e, (Literal, Var)):
            return _ATOM_PREC
        if e.left is None:
            return _UNARY_PREC
        return _PREC.get(e.name, 0)

    @staticmethod
    def _indent(lines: list[str]) -> list[str]:
        return [_INDENT + line if line else "" for line in lines]

    # ------------------------------------------------------------------
    # maximal / debug rendering
    # ------------------------------------------------------------------

    def debug(self, modules: list[Module[T]]) -> str:
        return "\n\n".join(self._debug(m, 0) for m in modules)

    def _debug(self, value: object, level: int, trail: str = "") -> str:
        pad = _INDENT * level
        if not is_dataclass(value) or isinstance(value, type):
            return f"{pad}{value!r}{trail}"

        lines = [f"{pad}{type(value).__name__}("]
        for f in fields(value):
            v = getattr(value, f.name)
            field_pad = _INDENT * (level + 1)
            if f.name in ("t", "rt"):
                lines.append(f"{field_pad}{f.name}={self.ty(cast(T, v))},")
            elif f.name == "argts":
                lines.append(f"{field_pad}{f.name}=[")
                for item in v:
                    lines.append(f"{_INDENT * (level + 2)}{self.ty(cast(T, item))},")
                lines.append(f"{field_pad}],")
            elif isinstance(v, list):
                if not v:
                    lines.append(f"{field_pad}{f.name}=[],")
                else:
                    lines.append(f"{field_pad}{f.name}=[")
                    for item in v:
                        lines.append(self._debug(item, level + 2, ","))
                    lines.append(f"{field_pad}],")
            elif is_dataclass(v):
                lines.append(f"{field_pad}{f.name}=")
                lines.append(self._debug(v, level + 2, ","))
            else:
                lines.append(f"{field_pad}{f.name}={v!r},")
        lines.append(f"{pad}){trail}")
        return "\n".join(lines)


def _input_type(t: InputType) -> str:
    return t.t.pt if isinstance(t, NominalType) else "?"


def _input_label(t: InputType) -> str:
    if isinstance(t, NominalType):
        return " :: public" if t.label.public else " :: private"
    return ""


def _output_min_type(t: OutputType) -> str:
    return t.t.pt if t.t else "?"


def _output_min_label(t: OutputType) -> str:
    if isinstance(t.d, VarDeriv) and isinstance(t.d.l, ClearenceLabel):
        return " :: public" if t.d.l.public else " :: private"
    return ""


def print_program[T](
    modules: list[Module[T]],
    ty: Callable[[T], str],
    label: Callable[[T], str] | None = None,
) -> str:
    return Printer(ty, label).program(modules)


def print_input(modules: list[Module[InputType]]) -> str:
    return print_program(modules, _input_type, _input_label)


def print_output_min(modules: list[Module[OutputType]]) -> str:
    return print_program(modules, _output_min_type, _output_min_label)


def print_output_max(modules: list[Module[OutputType]]) -> str:
    return Printer[OutputType](repr).debug(modules)
