from dataclasses import dataclass, field
from typing import Optional, Any
from __future__ import annotations
from Ast import *
from Types import *

type goal = str
type proof = str

def prove_proc(top_goal: goal, proc: ProcedureDeriv) -> proof :
    # append to goal based on argument labels
    p = prove_block(top_goal, proc.body)
    return p

def prove_block(top_goal: goal, block: BlockDeriv) -> proof:
    # append to goal based on local var labels
    g = top_goal
    ps = []
    p = prove_statement(g, block.statements)
    ps.append(p)
    return "\n".join(ps)

def prove_statement(top_goal: goal, stmt: StatementDeriv) -> proof:
    if isinstance(stmt,AssignsDeriv):
        p = prove_statement(top_goal, stmt.tail)
        if stmt.after:
            return f"wp.\n{p}"
        else:
            return f"sp.\n{p}"
    elif isinstance(stmt,ReturnDeriv):
        return "(* TODO return statments *)"
    elif isinstance(stmt,IfDeriv):
        l = prove_block(top_goal, stmt.ld)
        r = prove_block(top_goal, stmt.rd)
        t = prove_statement(top_goal, stmt.then)
        return f"if.\n{l}\n{r}\n{t}"
    elif isinstance(stmt,WhileDeriv):
        p = prove_statement(top_goal, stmt.prior)
        b = prove_block(top_goal, stmt.bd)
        return f"while ({top_goal}).\n{b}\n{p}"
    elif isinstance(stmt,ProcCallDeriv):
        return "(* TODO procedure calls *)"


