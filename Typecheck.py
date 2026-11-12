from __future__ import annotations
from dataclasses import replace
from typing import cast

from Ast import *
from Types import *

# TODO: clearance labels / pc tracking
_PUBLIC = ClearenceLabel(public=True)
_UNKNOWN = PrimType("?")

type Env = dict[str, VarDeriv]
type ProcEnv = dict[str, Procedure[InputType]]


class TypecheckError(Exception):
    pass


class TypeMismatchError(TypecheckError):
    pass


class ClearanceError(TypecheckError):
    pass


class UnknownTypeError(TypecheckError):
    pass


class DuplicateNameError(TypecheckError):
    pass


_KNOWN_BASE_TYPES = {"int", "bool", "unit"}


def _check_prim_type(t: PrimType) -> None:
    """Reject type names that have no declaration in the language."""
    parts = t.pt.split()
    if (
        not parts
        or parts[0] not in _KNOWN_BASE_TYPES
        or any(part != "list" for part in parts[1:])
    ):
        raise UnknownTypeError(f"unknown type name: {t.pt}")


def _ty(t: PrimType | None) -> CheckedType:
    return CheckedType(t=t, d=LiteralDeriv(t or _UNKNOWN))


def _nom(t: InputType) -> tuple[PrimType | None, ClearenceLabel]:
    if isinstance(t, NominalType):
        _check_prim_type(t.t)
        return t.t, t.label
    return None, _PUBLIC


def _decl(v: Var[InputType]) -> tuple[Var[OutputType], VarDeriv]:
    t, l = _nom(v.t)
    d = VarDeriv(t=_ty(t), l=l, n=v.name)
    return Var(t=CheckedType(t=t, d=d), name=v.name), d


def _name(n: str) -> Var[OutputType]:
    return Var(t=CheckedType(t=None, d=VarDeriv(t=_ty(None), l=_PUBLIC, n=n)), name=n)


def _expr(e: Expr[OutputType]) -> Deriv:
    return cast(Deriv, e.t.d)


def _var(v: Var[OutputType]) -> VarDeriv:
    return cast(VarDeriv, v.t.d)


def _join(a: ClearenceLabel, b: ClearenceLabel) -> ClearenceLabel:
    # public is low, private is high; join keeps the higher label.
    return ClearenceLabel(public=a.public and b.public)


def _checked_label(l: CheckedLabel) -> ClearenceLabel:
    if isinstance(l, ClearenceLabel):
        return l
    return _join(_checked_label(l.pcl), _checked_label(l.l))


def _deriv_label(d: Deriv) -> ClearenceLabel:
    if isinstance(d, LiteralDeriv):
        return _PUBLIC
    if isinstance(d, VarDeriv):
        return _checked_label(d.l)
    left = _deriv_label(d.left) if d.left is not None else _PUBLIC
    return _join(left, _deriv_label(d.right))


def _expr_label(e: Expr[OutputType]) -> ClearenceLabel:
    return _deriv_label(_expr(e))


def _check_assignable(
    target: Var[OutputType],
    source_t: PrimType | None,
    source_l: CheckedLabel,
    where: str,
) -> None:
    target_t = target.t.t
    if target_t is not None and source_t is not None and target_t.pt != source_t.pt:
        raise TypeMismatchError(
            f"{where}: expected type {target_t.pt}, got {source_t.pt}"
        )
    # Reject high (private) -> low (public).
    if not _checked_label(source_l).public and _checked_label(_var(target).l).public:
        raise ClearanceError(
            f"{where}: private value or control flow cannot flow to public target"
        )


def _block(b: Block[OutputType]) -> BlockDeriv:
    return cast(BlockDeriv, b.t.d)


_ARITH = {"+", "-", "*", "/", "%/"}
_COMP = {"<", "<=", ">", ">=", "=", "<>"}
_LOGIC = {"&&", "||"}


def _opt_type(op: str, l: PrimType | None, r: PrimType | None) -> PrimType | None:
    if op in _ARITH:
        return PrimType("int")
    if op in _COMP or op in _LOGIC or op == "!":
        return PrimType("bool")
    return r or l


def check_literal(e: Literal[InputType]) -> Literal[OutputType]:
    t, _ = _nom(e.t)
    if isinstance(e.value, bool):
        t = PrimType("bool")
    elif isinstance(e.value, int):
        t = PrimType("int")
    return Literal(t=CheckedType(t=t, d=LiteralDeriv(t or _UNKNOWN)), value=e.value)


def check_var(
    v: Var[InputType], env: Env, pc: ClearenceLabel | None = None
) -> Var[OutputType]:
    decl = env.get(v.name)
    if decl is None:
        t0, l0 = _nom(v.t)
        decl = VarDeriv(t=_ty(t0), l=l0, n=v.name)
    t = decl.t.t
    l: CheckedLabel = decl.l
    if pc is not None and not pc.public:
        l = PCAdjust(pc, l)
    d = VarDeriv(t=CheckedType(t=t, d=decl), l=l, n=v.name)
    return Var(t=CheckedType(t=t, d=d), name=v.name)


def check_opt(e: Opt[InputType], env: Env, pc: ClearenceLabel) -> Opt[OutputType]:
    l = check_expr(e.left, env, pc) if e.left is not None else None
    r = check_expr(e.right, env, pc)
    t = _opt_type(e.name, l.t.t if l else None, r.t.t)
    d = OptDeriv(name=e.name, left=_expr(l) if l else None, right=_expr(r))
    return Opt(t=CheckedType(t=t, d=d), name=e.name, left=l, right=r)


def check_expr(e: Expr[InputType], env: Env, pc: ClearenceLabel) -> Expr[OutputType]:
    if isinstance(e, Literal):
        return check_literal(e)
    if isinstance(e, Var):
        return check_var(e, env, pc)
    return check_opt(e, env, pc)


def check_assign(
    s: Assign[InputType], env: Env, pc: ClearenceLabel
) -> tuple[Assign[OutputType], StatementDeriv]:
    left = check_var(s.left, env)
    right = check_expr(s.right, env, pc)
    _check_assignable(
        left,
        right.t.t,
        PCAdjust(pc, _expr_label(right)),
        f"assignment to '{left.name}'",
    )
    d = AssignsDeriv(asns=[(_var(left), _expr(right))], before=True, tail=SkipDeriv())
    return Assign(t=CheckedType(t=None, d=d), left=left, right=right), d


def check_if(
    s: If[InputType], env: Env, procs: ProcEnv, pc: ClearenceLabel
) -> tuple[If[OutputType], StatementDeriv]:
    cond = check_expr(s.condition, env, pc)
    body_pc = _join(pc, _expr_label(cond))
    tArm = check_block(s.tArm, env, procs, body_pc)
    fArm = check_block(s.fArm, env, procs, body_pc)
    d = IfDeriv(
        cd=_expr(cond), ld=_block(tArm), rd=_block(fArm), rt=None, then=SkipDeriv()
    )
    return If(t=CheckedType(t=None, d=d), condition=cond, tArm=tArm, fArm=fArm), d


def check_while(
    s: While[InputType], env: Env, procs: ProcEnv, pc: ClearenceLabel
) -> tuple[While[OutputType], StatementDeriv]:
    cond = check_expr(s.condition, env, pc)
    body_pc = _join(pc, _expr_label(cond))
    body = check_block(s.body, env, procs, body_pc)
    d = WhileDeriv(prior=SkipDeriv(), cd=_expr(cond), bd=_block(body), rt=None)
    return While(t=CheckedType(t=None, d=d), condition=cond, body=body), d


def check_call(
    s: ProcCall[InputType], env: Env, procs: ProcEnv, pc: ClearenceLabel
) -> tuple[ProcCall[OutputType], StatementDeriv]:
    dst = check_var(s.dst, env)
    func = check_var(s.func, env)
    args = [check_expr(a, env, pc) for a in s.args]
    sig = procs.get(s.func.name)
    rt, rl = _nom(sig.rt) if sig is not None else (None, _PUBLIC)
    _check_assignable(
        dst,
        rt,
        PCAdjust(pc, rl),
        f"call to '{s.func.name}' destination '{dst.name}'",
    )
    d = ProcCallDeriv(func=_var(func), ads=[_expr(a) for a in args], tail=SkipDeriv())
    return ProcCall(t=CheckedType(t=None, d=d), dst=dst, func=func, args=args), d


def check_return(
    s: Return[InputType], env: Env, pc: ClearenceLabel
) -> tuple[Return[OutputType], StatementDeriv]:
    # TODO: returns are ignored for now
    val = check_expr(s.val, env, pc)
    return Return(t=CheckedType(t=None, d=SkipDeriv()), val=val), SkipDeriv()


def check_statement(
    s: Statement[InputType], env: Env, procs: ProcEnv, pc: ClearenceLabel
) -> tuple[Statement[OutputType], StatementDeriv]:
    if isinstance(s, Assign):
        return check_assign(s, env, pc)
    if isinstance(s, If):
        return check_if(s, env, procs, pc)
    if isinstance(s, While):
        return check_while(s, env, procs, pc)
    if isinstance(s, ProcCall):
        return check_call(s, env, procs, pc)
    return check_return(s, env, pc)


def _asns(d: StatementDeriv) -> list[tuple[VarDeriv, Deriv]]:
    return cast(AssignsDeriv, d).asns


def _build(
    stmts: list[Statement[InputType]],
    ds: list[StatementDeriv],
    lo: int,
    hi: int,
    nodes: list[StatementDeriv],
) -> StatementDeriv:
    if lo >= hi:
        return SkipDeriv()

    seen_while = False
    for j in range(lo, hi-1):
        if isinstance(stmts[j], While):
            first = _build(stmts, ds, lo, j+1, nodes)
            second = _build(stmts, ds, j+1, hi, nodes)
            return OrderDeriv(first=first, second=second)
  
    if isinstance(stmts[hi - 1], While):
        prior = _build(stmts, ds, lo, hi - 1, nodes)
        wlocal = cast(WhileDeriv, ds[hi - 1])
        wd = WhileDeriv(prior=prior, cd=wlocal.cd, bd=wlocal.bd, rt=wlocal.rt)
        nodes[hi - 1] = wd
        return wd

    k = hi
    while k > lo and isinstance(stmts[k - 1], Assign):
        k -= 1
    if k < hi and k > lo and isinstance(stmts[k - 1], While):
        prior = _build(stmts, ds, lo, k - 1, nodes)
        wlocal = cast(WhileDeriv, ds[k - 1])
        wd = WhileDeriv(prior=prior, cd=wlocal.cd, bd=wlocal.bd, rt=wlocal.rt)
        nodes[k - 1] = wd
        after_asns: list[tuple[VarDeriv, Deriv]] = []
        for i in range(k, hi):
            after_asns.extend(_asns(ds[i]))
        ad = AssignsDeriv(asns=after_asns, before=False, tail=wd)
        for i in range(k, hi):
            nodes[i] = ad
        return ad

    if isinstance(stmts[lo], If):
        tail = _build(stmts, ds, lo + 1, hi, nodes)
        if_local = cast(IfDeriv, ds[lo])
        idd = IfDeriv(
            cd=if_local.cd,
            ld=if_local.ld,
            rd=if_local.rd,
            rt=if_local.rt,
            then=tail,
        )
        nodes[lo] = idd
        return idd

    if isinstance(stmts[lo], ProcCall):
        tail = _build(stmts, ds, lo + 1, hi, nodes)
        call_local = cast(ProcCallDeriv, ds[lo])
        cd = ProcCallDeriv(func=call_local.func, ads=call_local.ads, tail=tail)
        nodes[lo] = cd
        return cd

    if isinstance(stmts[lo], Assign):
        j = lo
        leading_asns: list[tuple[VarDeriv, Deriv]] = []
        while j < hi and isinstance(stmts[j], Assign):
            leading_asns.extend(_asns(ds[j]))
            j += 1
        tail = _build(stmts, ds, j, hi, nodes)
        ad = AssignsDeriv(
            asns=leading_asns, before=True, tail=tail
        )
        for i in range(lo, j):
            nodes[i] = ad
        return ad

    raise TypecheckError("unsupported statement order")


def _compose(
    stmts: list[Statement[InputType]], ds: list[StatementDeriv]
) -> tuple[StatementDeriv, list[StatementDeriv]]:
    nodes: list[StatementDeriv] = [SkipDeriv() for _ in stmts]
    return _build(stmts, ds, 0, len(stmts), nodes), nodes


def check_statements(
    stmts: list[Statement[InputType]],
    env: Env,
    procs: ProcEnv,
    pc: ClearenceLabel,
) -> tuple[list[Statement[OutputType]], StatementDeriv]:
    outs: list[Statement[OutputType]] = []
    ds: list[StatementDeriv] = []
    for s in stmts:
        out, d = check_statement(s, env, procs, pc)
        outs.append(out)
        ds.append(d)

    keep = [i for i, s in enumerate(stmts) if not isinstance(s, Return)]
    chain, nodes = _compose([stmts[i] for i in keep], [ds[i] for i in keep])
    mapped: list[StatementDeriv] = [SkipDeriv() for _ in stmts]
    for j, i in enumerate(keep):
        mapped[i] = nodes[j]
    outs = [replace(s, t=CheckedType(t=None, d=mapped[i])) for i, s in enumerate(outs)]
    return outs, chain


def check_block(
    b: Block[InputType], env: Env, procs: ProcEnv, pc: ClearenceLabel
) -> Block[OutputType]:
    local = dict(env)
    defs: list[Var[OutputType]] = []
    ds: list[VarDeriv] = []
    seen: set[str] = set()
    for v in b.localDefs:
        if v.name in seen:
            raise DuplicateNameError(f"duplicate local variable '{v.name}'")
        seen.add(v.name)
        out, d = _decl(v)
        defs.append(out)
        ds.append(d)
        local[v.name] = d
    stmts, chain = check_statements(b.statements, local, procs, pc)
    # TODO: returns
    bd = BlockDeriv(rt=None, localDefs=ds, statements=chain)
    return Block(t=CheckedType(t=None, d=bd), localDefs=defs, statements=stmts)


def check_proc(
    p: Procedure[InputType], env: Env, procs: ProcEnv
) -> Procedure[OutputType]:
    local = dict(env)
    args: list[Var[OutputType]] = []
    ads: list[VarDeriv] = []
    arg_names: set[str] = set()
    for a in p.args:
        if a.name in arg_names:
            raise DuplicateNameError(
                f"procedure '{p.name.name}': duplicate argument '{a.name}'"
            )
        arg_names.add(a.name)
        out, d = _decl(a)
        args.append(out)
        ads.append(d)
        local[a.name] = d
    for v in p.body.localDefs:
        if v.name in arg_names:
            raise DuplicateNameError(
                f"procedure '{p.name.name}': local variable '{v.name}' "
                "duplicates an argument"
            )
    body = check_block(p.body, local, procs, _PUBLIC)
    t, _ = _nom(p.rt)
    pd = ProcedureDeriv(
        name=p.name.name, args=ads, rt=LiteralDeriv(t or _UNKNOWN), body=_block(body)
    )
    return Procedure(
        t=CheckedType(t=None, d=pd),
        name=_name(p.name.name),
        argts=[a.t for a in args],
        rt=_ty(t),
        args=args,
        body=body,
    )


def check_module(m: Module[InputType]) -> Module[OutputType]:
    env: Env = {}
    defs: list[Var[OutputType]] = []
    ds: list[VarDeriv] = []
    for v in m.defns:
        if v.name in env:
            raise DuplicateNameError(
                f"module '{m.name.name}': duplicate variable '{v.name}'"
            )
        out, d = _decl(v)
        defs.append(out)
        ds.append(d)
        env[v.name] = d
    proc_names: set[str] = set()
    for p in m.procs:
        if p.name.name in proc_names:
            raise DuplicateNameError(
                f"module '{m.name.name}': duplicate procedure '{p.name.name}'"
            )
        proc_names.add(p.name.name)
    proc_env: ProcEnv = {p.name.name: p for p in m.procs}
    checked_procs = [check_proc(p, env, proc_env) for p in m.procs]
    md = ModuleDeriv(
        name=m.name.name,
        defns=ds,
        procs=[cast(ProcedureDeriv, p.t.d) for p in checked_procs],
    )
    return Module(
        t=CheckedType(t=None, d=md),
        name=_name(m.name.name),
        defns=defs,
        procs=checked_procs,
    )


def check_program(ms: list[Module[InputType]]) -> list[Module[OutputType]]:
    seen: set[str] = set()
    for m in ms:
        if m.name.name in seen:
            raise DuplicateNameError(f"duplicate module '{m.name.name}'")
        seen.add(m.name.name)
    return [check_module(m) for m in ms]
