from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any
from Ast import *
from Types import *

type goal = str
type proof = str

def _match(publics: list[str]) -> str:
    s = ""
    for p in publics:
        s += p + ", "
    return f"={{ {s[:-2]} }}"

def _equiv(procName: str, publics: list[str]) -> str:
    s = _match(publics)
    return f"equiv [{procName} ~ {procName} : {s} ==> {s} ]"

def prove_proc(procName: str, module_publics: list[str], tree: ProcedureDeriv) -> proof:
    # TODO include arugements here
    goal = _match(module_publics)
    body = f"proc.\n{_prove_block(goal, tree.body)}"
    safeName = procName.replace(".", "_")
    return f"""lemma {safeName}_LE :
{_equiv(procName, module_publics)}.
proof.
{body}
qed.
"""

def _prove_block(top_goal: goal, block: BlockDeriv) -> proof:
    # TODO append to goal based on local var labels
    return _prove_statement(top_goal, block.statements)

def _prove_statement(top_goal: goal, stmt: StatementDeriv) -> proof:
    if isinstance(stmt,AssignsDeriv):
        p = _prove_statement(top_goal, stmt.tail)
        n = len(stmt.asns)
        if stmt.before:
            return f"sp {n} {n}.\n{p}"
        else:
            return f"wp {n} {n}.\n{p}"
    elif isinstance(stmt,ReturnDeriv):
        return "(* TODO return statments *)"
    elif isinstance(stmt,IfDeriv):
        l = _prove_block(top_goal, stmt.ld)
        r = _prove_block(top_goal, stmt.rd)
        if isinstance(stmt.then, SkipDeriv):
            t = "(* elided skip for an empty tail for if rule  *)"
        else: 
            t = _prove_statement(top_goal, stmt.then)
        return f"if. (* if sync condition *) progress.\n(* if left *)\n{l}\n{t}\n(* if right *)\n{r}\n{t}"
    elif isinstance(stmt,WhileDeriv):
        b = _prove_block(top_goal, stmt.bd)
        p = _prove_statement(top_goal, stmt.prior)
        # if isinstance(stmt.prior, SkipDeriv):
        #     p = "(* elided skip for an empty prior for while rule *)"
        # else: 
        #     p = _prove_statement(top_goal, stmt.prior)
        return f"while ({top_goal}).\n(* while inv. holds *)\n{b}\n(* while prefix *)\n{p}"
    elif isinstance(stmt,ProcCallDeriv):
        p = _prove_statement(top_goal, stmt.tail)
        return f"(* TODO procedure calls *)\n{p}"
    elif isinstance(stmt,SkipDeriv):
        return "skip; progress."
    elif isinstance(stmt,OrderDeriv):
        f = _prove_statement(top_goal, stmt.first)
        s = _prove_statement(top_goal, stmt.second)
        return f"seq 1 1 : ({top_goal}).\n(* seq first half *)\n{f}\n(* seq second half *)\n{s}"
    else:
        return ""


