from dataclasses import dataclass, field
from typing import Optional, Any
from __future__ import annotations

@dataclass
class PrimType:
    pt: str                     # TODO

@dataclass
class ClearenceLabel:
    public: bool                # just 2 values for now

@dataclass
class NominalType:
    t: PrimType
    label: ClearenceLabel

######################################################################

@dataclass
class PCAdjust:
    pcl: ClearenceLabel
    l: Label

type Label = ClearenceLabel | PCAdjust

@dataclass
class LiteralDeriv:
    t: PrimType

type CheckedType = PrimType

@dataclass
class CheckedLT:
    l: Label
    t: CheckedType
    
@dataclass
class VarDeriv:
    t: CheckedType
    l: Label
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
    # must match t and <= l

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
    ld: Deriv
    rd: Deriv
    rt: Optional[ReturnDeriv]

@dataclass
class WhileDeriv:
    cd: Deriv
    bd: Deriv
    rt: Optional[ReturnDeriv]

type StatementDeriv = AssignDeriv | ReturnDeriv | IfDeriv | WhileDeriv | ProcCallDeriv
    
@dataclass
class BlockDeriv:
    rt: Optional[ReturnDeriv]
    localDefs: list[VarDeriv]
    statements: list[StatementDeriv]

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
