from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
from Lexer import (
    UNSUPPORTED_KEYWORDS,
    LexError,
    Token,
    TokenKind,
    tokenize,
)


class ParseError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.line = line
        self.column = column


T = Any


@dataclass
class Parser:
    tokens: list[Token]
    pos: int = 0

    # ------------------------------------------------------------------
    # token helpers
    # ------------------------------------------------------------------

    def peek(self, offset: int = 0) -> Token:
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[idx]

    def check(self, kind: TokenKind) -> bool:
        return self.peek().kind == kind

    def match(self, *kinds: TokenKind) -> Token | None:
        if self.peek().kind in kinds:
            tok = self.peek()
            self.pos += 1
            return tok
        return None

    def _unexpected(self, expected: str) -> ParseError:
        tok = self.peek()
        if tok.kind == TokenKind.UNSUPPORTED_KEYWORD:
            hint = UNSUPPORTED_KEYWORDS.get(
                tok.lexeme, f"unsupported construct {tok.lexeme!r}"
            )
            return ParseError(f"{hint}", tok.line, tok.column)
        return ParseError(
            f"expected {expected}, got {tok.kind.name} ({tok.lexeme!r})",
            tok.line,
            tok.column,
        )

    def expect(self, kind: TokenKind, message: str = "") -> Token:
        tok = self.peek()
        if tok.kind != kind:
            raise self._unexpected(message or kind.name)
        self.pos += 1
        return tok

    # ------------------------------------------------------------------
    # program / module
    # ------------------------------------------------------------------

    def parse_program(self) -> list[Module[T]]:
        modules: list[Module[T]] = []
        while not self.check(TokenKind.EOF):
            modules.append(self.parse_module())
        return modules

    def parse_module(self) -> Module[T]:
        self.expect(TokenKind.MODULE, "'module'")

        # Special-case `module type T = ...` so it does not get parsed as
        # a module literally named `type`.
        nxt = self.peek()
        if nxt.kind == TokenKind.UNSUPPORTED_KEYWORD and nxt.lexeme == "type":
            raise ParseError(
                "module type declarations are not supported; "
                "the parser only accepts concrete `module` definitions",
                nxt.line,
                nxt.column,
            )

        name_tok = self.expect(TokenKind.IDENTIFIER, "module name")
        name: Var[T] = Var(t=None, name=name_tok.lexeme)

        self.expect(TokenKind.EQ, "'=' after module name")
        self.expect(TokenKind.LBRACE, "'{' to begin module body")

        defns: list[Var[T]] = []
        procs: list[Procedure[T]] = []

        while not self.check(TokenKind.RBRACE) and not self.check(TokenKind.EOF):
            if self.check(TokenKind.VAR):
                defns.extend(self.parse_module_var_defn())
            elif self.check(TokenKind.PROC):
                procs.append(self.parse_proc_defn())
            else:
                raise self._unexpected("'var' or 'proc' in module body")

        self.expect(TokenKind.RBRACE, "'}' to close module body")
        return Module(t=None, name=name, defns=defns, procs=procs)

    # ------------------------------------------------------------------
    # module-level definitions
    # ------------------------------------------------------------------

    def parse_module_var_defn(self) -> list[Var[T]]:
        self.expect(TokenKind.VAR, "'var'")
        names = self.parse_name_list()
        self.expect(TokenKind.COLON, "':' after variable name list")
        self.parse_type()
        self.expect(TokenKind.COLONCOLON, "'::' after type")
        self.parse_visibility()
        self.expect(TokenKind.SEMICOLON, "';' after module variable definition")
        return [Var(t=None, name=n) for n in names]

    def parse_visibility(self) -> str:
        tok = self.peek()
        if tok.kind in (TokenKind.PUBLIC, TokenKind.PRIVATE):
            self.pos += 1
            return tok.lexeme
        raise self._unexpected("'public' or 'private'")

    def parse_proc_defn(self) -> Procedure[T]:
        self.expect(TokenKind.PROC, "'proc'")
        name_tok = self.expect(TokenKind.IDENTIFIER, "procedure name")
        name: Var[T] = Var(t=None, name=name_tok.lexeme)

        self.expect(TokenKind.LPAREN, "'(' after procedure name")
        args = self.parse_p_args()
        self.expect(TokenKind.RPAREN, "')' after procedure arguments")

        self.expect(TokenKind.COLON, "':' after procedure signature")
        rt = self.parse_type()

        self.expect(TokenKind.EQ, "'=' before procedure body")
        body = self.parse_block()
        return Procedure(t=None, name=name, argts=[], rt=rt, args=args, body=body)

    def parse_p_args(self) -> list[Var[T]]:
        args: list[Var[T]] = []
        if self.check(TokenKind.RPAREN):
            return args
        args.append(self.parse_p_arg())
        while self.match(TokenKind.COMMA):
            args.append(self.parse_p_arg())
        return args

    def parse_p_arg(self) -> Var[T]:
        name_tok = self.expect(TokenKind.IDENTIFIER, "argument name")
        self.expect(TokenKind.COLON, "':' after argument name")
        self.parse_type()
        return Var(t=None, name=name_tok.lexeme)

    # ------------------------------------------------------------------
    # types
    # ------------------------------------------------------------------

    def parse_type(self) -> Any:
        self.parse_base_type()
        while self.match(TokenKind.LIST):
            pass
        return None

    def parse_base_type(self) -> Any:
        if self.match(TokenKind.INT):
            return None
        if self.match(TokenKind.BOOL):
            return None
        if self.check(TokenKind.IDENTIFIER):
            self.pos += 1
            if self.match(TokenKind.DOT):
                self.expect(TokenKind.IDENTIFIER, "type name after '.'")
            return None
        raise self._unexpected("type")

    # ------------------------------------------------------------------
    # blocks and statements
    # ------------------------------------------------------------------

    def parse_block(self) -> Block[T]:
        self.expect(TokenKind.LBRACE, "'{' to begin block")
        local_defs = self.parse_local_var_decls()
        statements = self.parse_stmts()
        self.expect(TokenKind.RBRACE, "'}' to close block")
        return Block(t=None, localDefs=local_defs, statements=statements)

    def parse_local_var_decls(self) -> list[Var[T]]:
        defs: list[Var[T]] = []
        while self.check(TokenKind.VAR):
            self.expect(TokenKind.VAR)
            names = self.parse_name_list()
            self.expect(TokenKind.COLON, "':' after local variable name list")
            self.parse_type()
            self.expect(TokenKind.SEMICOLON, "';' after local variable declaration")
            defs.extend(Var(t=None, name=n) for n in names)
        return defs

    def parse_name_list(self) -> list[str]:
        names = [self.expect(TokenKind.IDENTIFIER, "variable name").lexeme]
        while self.match(TokenKind.COMMA):
            names.append(self.expect(TokenKind.IDENTIFIER, "variable name").lexeme)
        return names

    def parse_stmts(self) -> list[Statement[T]]:
        stmts: list[Statement[T]] = []
        while not self.check(TokenKind.RBRACE) and not self.check(TokenKind.EOF):
            if self.check(TokenKind.IF):
                stmts.append(self.parse_if_stmt())
            elif self.check(TokenKind.WHILE):
                stmts.append(self.parse_while_stmt())
            else:
                # assign | return | call  — all are <simple-stmt> and all need ';'
                stmts.append(self.parse_simple_stmt())
                self.expect(TokenKind.SEMICOLON, "';' after statement")
        return stmts

    def parse_simple_stmt(self) -> Statement[T]:
        if self.check(TokenKind.IDENTIFIER) and self.peek(1).kind == TokenKind.CALL:
            return self.parse_call_stmt()
        if self.check(TokenKind.RETURN):
            return self.parse_return_stmt()
        left = self.parse_lvalue()
        self.expect(TokenKind.ARROW, "'<-' in assignment")
        right = self.parse_expr()
        return Assign(t=None, left=left, right=right)

    def parse_lvalue(self) -> Var[T]:
        name = self.expect(TokenKind.IDENTIFIER, "lvalue name").lexeme
        if self.match(TokenKind.DOT):
            name = self.expect(TokenKind.IDENTIFIER, "field name after '.'").lexeme
        return Var(t=None, name=name)

    def parse_call_stmt(self) -> ProcCall[T]:
        dst_name = self.expect(TokenKind.IDENTIFIER, "destination variable").lexeme
        dst: Var[T] = Var(t=None, name=dst_name)  # ← see note below
        self.expect(TokenKind.CALL, "'<@'")
        func_name = self.expect(TokenKind.IDENTIFIER, "procedure name").lexeme
        func: Var[T] = Var(t=None, name=func_name)
        self.expect(TokenKind.LPAREN, "'(' after procedure name")
        args = self.parse_c_args()
        self.expect(TokenKind.RPAREN, "')' after call arguments")
        return ProcCall(t=None, func=func, args=args)

    def parse_c_args(self) -> list[Expr[T]]:
        args: list[Expr[T]] = []
        if self.check(TokenKind.RPAREN):
            return args
        args.append(self.parse_expr())
        while self.match(TokenKind.COMMA):
            args.append(self.parse_expr())
        return args

    def parse_return_stmt(self) -> Return[T]:
        self.expect(TokenKind.RETURN, "'return'")
        val = self.parse_expr()
        return Return(t=None, val=val)

    def parse_while_stmt(self) -> While[T]:
        self.expect(TokenKind.WHILE, "'while'")
        self.expect(TokenKind.LPAREN, "'(' after 'while'")
        cond = self.parse_expr()
        self.expect(TokenKind.RPAREN, "')' after while condition")
        body = self.parse_block()
        return While(t=None, condition=cond, body=body)

    def parse_if_stmt(self) -> If[T]:
        self.expect(TokenKind.IF, "'if'")
        self.expect(TokenKind.LPAREN, "'(' after 'if'")
        cond = self.parse_expr()
        self.expect(TokenKind.RPAREN, "')' after if condition")
        then_arm = self.parse_block()
        else_arm = self.parse_if_tail()
        return If(t=None, condition=cond, tArm=then_arm, fArm=else_arm)

    def parse_if_tail(self) -> Block[T]:
        if self.check(TokenKind.ELIF):
            self.expect(TokenKind.ELIF)
            self.expect(TokenKind.LPAREN)
            cond = self.parse_expr()
            self.expect(TokenKind.RPAREN)
            then_arm = self.parse_block()
            rest = self.parse_if_tail()
            nested = If(t=None, condition=cond, tArm=then_arm, fArm=rest)
            return Block(t=None, localDefs=[], statements=[nested])
        if self.check(TokenKind.ELSE):
            self.expect(TokenKind.ELSE)
            return self.parse_block()
        return Block(t=None, localDefs=[], statements=[])

    # ------------------------------------------------------------------
    # expressions (C-like precedence, left-associative)
    # ------------------------------------------------------------------

    def parse_expr(self) -> Expr[T]:
        return self.parse_or()

    def parse_or(self) -> Expr[T]:
        left = self.parse_and()
        while self.match(TokenKind.OR):
            left = Opt(t=None, name="||", left=left, right=self.parse_and())
        return left

    def parse_and(self) -> Expr[T]:
        left = self.parse_equality()
        while self.match(TokenKind.AND):
            left = Opt(t=None, name="&&", left=left, right=self.parse_equality())
        return left

    def parse_equality(self) -> Expr[T]:
        left = self.parse_comparison()
        while self.peek().kind in (TokenKind.EQ, TokenKind.NEQ):
            op = self.peek().lexeme
            self.pos += 1
            left = Opt(t=None, name=op, left=left, right=self.parse_comparison())
        return left

    def parse_comparison(self) -> Expr[T]:
        left = self.parse_term()
        while self.peek().kind in (TokenKind.LT, TokenKind.LE, TokenKind.GT, TokenKind.GE):
            op = self.peek().lexeme
            self.pos += 1
            left = Opt(t=None, name=op, left=left, right=self.parse_term())
        return left

    def parse_term(self) -> Expr[T]:
        left = self.parse_factor()
        while self.peek().kind in (TokenKind.PLUS, TokenKind.MINUS):
            op = self.peek().lexeme
            self.pos += 1
            left = Opt(t=None, name=op, left=left, right=self.parse_factor())
        return left

    def parse_factor(self) -> Expr[T]:
        left = self.parse_unary()
        while self.peek().kind in (
            TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT_SLASH,
        ):
            op = self.peek().lexeme
            self.pos += 1
            left = Opt(t=None, name=op, left=left, right=self.parse_unary())
        return left

    def parse_unary(self) -> Expr[T]:
        if self.check(TokenKind.MINUS):
            self.pos += 1
            return Opt(t=None, name="-", left=None, right=self.parse_unary())
        if self.check(TokenKind.NOT):
            self.pos += 1
            return Opt(t=None, name="!", left=None, right=self.parse_unary())
        return self.parse_atom()

    def parse_atom(self) -> Expr[T]:
        tok = self.peek()

        if tok.kind == TokenKind.INTEGER_LITERAL:
            self.pos += 1
            return Literal(t=None, value=int(tok.lexeme))

        if tok.kind in (TokenKind.TRUE, TokenKind.FALSE):
            self.pos += 1
            return Literal(t=None, value=(tok.kind == TokenKind.TRUE))

        if tok.kind == TokenKind.LPAREN:
            self.pos += 1
            expr = self.parse_expr()
            self.expect(TokenKind.RPAREN, "')' after parenthesised expression")
            return expr

        if tok.kind == TokenKind.IDENTIFIER:
            self.pos += 1
            if self.match(TokenKind.DOT):
                field = self.expect(TokenKind.IDENTIFIER, "field name after '.'")
                return Var(t=None, name=field.lexeme)
            return Var(t=None, name=tok.lexeme)

        raise self._unexpected("expression")


# ----------------------------------------------------------------------
# convenience entry point
# ----------------------------------------------------------------------

def parse(source: str) -> list[Module[T]]:
    tokens = tokenize(source)
    return Parser(tokens).parse_program()