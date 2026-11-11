from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class PrimType:
    pt: str                     # TODO

@dataclass
class ClearenceLabel:
    public: bool                # just 2 values for now

# type + label as given in the source program. Parsed directly
@dataclass
class NominalType:
    t: PrimType
    label: ClearenceLabel

# Blocks etc have no type, variables have nominal 
type InputType = NominalType | None

######################################################################

@dataclass
class PCAdjust:
    pcl: ClearenceLabel         # label from control flow
    l: CheckedLabel

type CheckedLabel = ClearenceLabel | PCAdjust

@dataclass
class LiteralDeriv:
    t: PrimType

# @dataclass
# class CheckedLT:
#     l: CheckedLabel
#     t: CheckedType
    
@dataclass
class VarDeriv:
    t: CheckedType
    l: CheckedLabel
    n: str

@dataclass
class OptDeriv:
    name: str
    left: Optional[Deriv]
    right: Deriv
    # TODO include primitive patterns for combining types and labels
    # all label combiners can be min left right ?
    # type combiner can share with the nominal rules

type Deriv = LiteralDeriv | VarDeriv | OptDeriv

@dataclass
class AssignsDeriv:
    asns: list[tuple[VarDeriv, Deriv]]
    after: bool                 # true for tail then asns, false for asns then tail
    tail: StatementDeriv

@dataclass
class ReturnDeriv:
    v: Deriv
    # TODO need label?

@dataclass
class ProcCallDeriv:
    func: VarDeriv
    ads: list[Deriv]
    tail: StatementDeriv

@dataclass
class SkipDeriv:
    pass
    
@dataclass
class IfDeriv:
    cd: Deriv
    ld: BlockDeriv
    rd: BlockDeriv
    rt: Optional[ReturnDeriv]
    then: StatementDeriv
    # appies at start, have child after

@dataclass
class OrderDeriv:
    # produces seq 1. [first] [second]
    # we need this to make the if and while rules available with their
    # relative ordering requirements
    first: StatementDeriv
    second: StatementDeriv

@dataclass
class WhileDeriv:
    # applies at end, have child before
    prior: StatementDeriv
    cd: Deriv
    bd: BlockDeriv
    rt: Optional[ReturnDeriv]

type StatementDeriv = AssignsDeriv | ReturnDeriv | IfDeriv | OrderDeriv | WhileDeriv | ProcCallDeriv | SkipDeriv
    
@dataclass
class BlockDeriv:
    rt: Optional[ReturnDeriv]
    localDefs: list[VarDeriv]
    statements: StatementDeriv

@dataclass
class ProcedureDeriv:
    name: str
    args: list[VarDeriv]
    rt: Deriv
    body: BlockDeriv

@dataclass
class ModuleDeriv:
    name: str
    defns: list[VarDeriv]
    procs: list[ProcedureDeriv]

type TopDeriv = BlockDeriv | ProcedureDeriv | ModuleDeriv

# all Ast contructions have CheckedType
@dataclass
class CheckedType:
    t: PrimType | None
    d: Deriv | StatementDeriv | TopDeriv
type OutputType = CheckedType

