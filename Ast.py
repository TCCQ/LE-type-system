from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class Literal[T]:
    t: T
    value: Any

@dataclass
class Var[T]:
    t: T
    name: str

@dataclass
class Opt[T]:
    t: T
    name: str
    left: Optional[Expr[T]]
    right: Expr[T]

type Expr[T] = Literal[T] | Var[T] | Opt[T]

@dataclass
class Assign[T]:
    t: T
    left: Var[T]
    right: Expr[T]

@dataclass
class Return[T]:
    t: T
    val: Expr[T]

@dataclass
class ProcCall[T]:
    t: T
    dst: Var[T]
    func: Var[T]
    args: list[Expr[T]]
    
@dataclass
class If[T]:
    t: T
    condition: Expr[T]
    tArm: Block[T]
    fArm: Block[T]

@dataclass
class While[T]:
    t: T
    condition: Expr[T]
    body: Block[T]
    
type Statement[T] = Assign[T] | If[T] | While[T] | ProcCall[T] | Return[T]

@dataclass 
class Block[T]:
    t: T
    localDefs: list[Var[T]]
    statements: list[Statement[T]]

@dataclass
class Procedure[T]:
    t: T
    name: Var[T]
    argts: list[T]
    rt: T
    args: list[Var[T]]
    body: Block[T]

@dataclass
class Module[T]:
    t: T
    name: Var[T]
    defns: list[Var[T]]
    procs: list[Procedure[T]]
    # module types / scoping not included
