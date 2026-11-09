from dataclasses import dataclass, field
from typing import Optional, Any
from __future__ import annotations

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
class AssignDeriv:
    left: VarDeriv
    right: Deriv
    then: StatementDeriv
    # must match t and <= l
    # seq at start, child after

@dataclass
class ReturnDeriv:
    v: Deriv
    # TODO need label?

@dataclass
class ProcCallDeriv:
    func: VarDeriv
    ads: list[Deriv]
    
@dataclass
class IfDeriv:
    cd: Deriv
    ld: BlockDeriv
    rd: BlockDeriv
    rt: Optional[ReturnDeriv]
    then: StatementDeriv
    # appies at start, have child after

@dataclass
class WhileDeriv:
    # applies at end, have child before
    prior: StatementDeriv
    cd: Deriv
    bd: BlockDeriv
    rt: Optional[ReturnDeriv]

type StatementDeriv = AssignDeriv | ReturnDeriv | IfDeriv | WhileDeriv | ProcCallDeriv
    
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
    t: PrimType
    d: Deriv | StatementDeriv | TopDeriv
type OutputType = CheckedType

