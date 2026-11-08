from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Final


class TokenKind(Enum):
    # keywords (in the BNF)
    MODULE = auto()
    VAR = auto()
    PROC = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    RETURN = auto()
    WHILE = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    TRUE = auto()
    FALSE = auto()
    INT = auto()
    BOOL = auto()
    LIST = auto()

    # punctuation
    LBRACE = auto()
    RBRACE = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    SEMICOLON = auto()
    COLON = auto()
    COLONCOLON = auto()   # ::
    ARROW = auto()        # <-
    CALL = auto()         # <@
    DOT = auto()          # .
    EQ = auto()           # =

    # operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT_SLASH = auto()  # %/
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    NEQ = auto()          # <>
    AND = auto()
    OR = auto()
    NOT = auto()

    # literals / identifiers
    INTEGER_LITERAL = auto()
    IDENTIFIER = auto()

    # recognized but unsupported EasyCrypt keywords
    UNSUPPORTED_KEYWORD = auto()

    EOF = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    line: int
    column: int


class LexError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.line = line
        self.column = column


KEYWORDS: Final[dict[str, TokenKind]] = {
    "module": TokenKind.MODULE,
    "var": TokenKind.VAR,
    "proc": TokenKind.PROC,
    "public": TokenKind.PUBLIC,
    "private": TokenKind.PRIVATE,
    "return": TokenKind.RETURN,
    "while": TokenKind.WHILE,
    "if": TokenKind.IF,
    "elif": TokenKind.ELIF,
    "else": TokenKind.ELSE,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "int": TokenKind.INT,
    "bool": TokenKind.BOOL,
    "list": TokenKind.LIST,
}


# EasyCrypt-specific words the parser does not accept.  Listing them here
# lets the parser give a targeted diagnostic instead of "unexpected token".
UNSUPPORTED_KEYWORDS: Final[dict[str, str]] = {
    "theory":  "theory blocks are not supported (the parser only accepts module definitions)",
    "end":     "'end' markers are not supported (the parser only accepts module definitions)",
    "section": "section blocks are not supported",
    "require": "'require' / 'require import' is not supported "
               "(the parser only accepts module definitions)",
    "import":  "'import' is not supported (the parser only accepts module definitions)",
    "axiom":   "'axiom' declarations are not supported "
               "(the parser only accepts module definitions)",
    "lemma":   "'lemma' declarations are not supported "
               "(the parser only accepts module definitions)",
    "op":      "'op' declarations are not supported "
               "(the parser only accepts module definitions)",
    "pred":    "'pred' declarations are not supported "
               "(the parser only accepts module definitions)",
    "type":    "'type' declarations are not supported "
               "(the BNF has no type-declaration construct)",
    "realize": "'realize' is not supported",
    "clone":   "'clone' is not supported",
    "proof":   "'proof' blocks are not supported "
               "(the parser only reads the module definitions, not the proof)",
    "qed":     "'qed' is not supported "
               "(the parser only reads the module definitions, not the proof)",
    "hoare":   "Hoare judgments are not supported "
               "(the parser only reads the module definitions)",
    "phoare":  "pHoare judgments are not supported "
               "(the parser only reads the module definitions)",
    "equiv":   "equiv judgments are not supported "
               "(the parser only reads the module definitions)",
    "print":   "'print' is not supported",
    "prove":   "'prove' is not supported",
}


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1

    def advance(n: int = 1) -> None:
        nonlocal i, line, column
        for _ in range(n):
            if i < len(source) and source[i] == "\n":
                line += 1
                column = 1
            else:
                column += 1
            i += 1

    def peek(offset: int = 0) -> str:
        j = i + offset
        return source[j] if j < len(source) else ""

    while i < len(source):
        ch = source[i]

        # whitespace
        if ch in " \t\r\n":
            advance()
            continue

        # line comment (not in BNF, but useful and harmless)
        if ch == "/" and peek(1) == "/":
            while i < len(source) and source[i] != "\n":
                advance()
            continue

        start_line, start_col = line, column

        # multi-character punctuation / operators
        two = source[i : i + 2]
        if two == "::":
            tokens.append(Token(TokenKind.COLONCOLON, "::", start_line, start_col))
            advance(2); continue
        if two == "<-":
            tokens.append(Token(TokenKind.ARROW, "<-", start_line, start_col))
            advance(2); continue
        if two == "<@":
            tokens.append(Token(TokenKind.CALL, "<@", start_line, start_col))
            advance(2); continue
        if two == "%/":
            tokens.append(Token(TokenKind.PERCENT_SLASH, "%/", start_line, start_col))
            advance(2); continue
        if two == "<=":
            tokens.append(Token(TokenKind.LE, "<=", start_line, start_col))
            advance(2); continue
        if two == ">=":
            tokens.append(Token(TokenKind.GE, ">=", start_line, start_col))
            advance(2); continue
        if two == "<>":
            tokens.append(Token(TokenKind.NEQ, "<>", start_line, start_col))
            advance(2); continue
        if two == "&&":
            tokens.append(Token(TokenKind.AND, "&&", start_line, start_col))
            advance(2); continue
        if two == "||":
            tokens.append(Token(TokenKind.OR, "||", start_line, start_col))
            advance(2); continue

        # single-character punctuation / operators
        single = {
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            ",": TokenKind.COMMA,
            ";": TokenKind.SEMICOLON,
            ":": TokenKind.COLON,
            ".": TokenKind.DOT,
            "=": TokenKind.EQ,
            "+": TokenKind.PLUS,
            "-": TokenKind.MINUS,
            "*": TokenKind.STAR,
            "/": TokenKind.SLASH,
            "<": TokenKind.LT,
            ">": TokenKind.GT,
            "!": TokenKind.NOT,
        }
        if ch in single:
            tokens.append(Token(single[ch], ch, start_line, start_col))
            advance(); continue

        # integer literal
        if ch.isdigit():
            j = i
            while i < len(source) and source[i].isdigit():
                advance()
            tokens.append(
                Token(TokenKind.INTEGER_LITERAL, source[j:i], start_line, start_col)
            )
            continue

        # identifier / keyword
        if ch.isalpha() or ch == "_":
            j = i
            while i < len(source) and (source[i].isalnum() or source[i] == "_"):
                advance()
            lexeme = source[j:i]
            if lexeme in KEYWORDS:
                kind = KEYWORDS[lexeme]
            elif lexeme in UNSUPPORTED_KEYWORDS:
                kind = TokenKind.UNSUPPORTED_KEYWORD
            else:
                kind = TokenKind.IDENTIFIER
            tokens.append(Token(kind, lexeme, start_line, start_col))
            continue

        # Give a targeted hint for common EasyCrypt operators we don't accept.
        unsupported_ops = {
            "=>": "implication '=>'",
            "==>": "implication '==>'",
            "<=>": "iff '<=>'",
            "^":   "exponentiation '^'",
            "~":   "negation '~'",
            "@":   "'@'",
            "#":   "'#'",
            "`":   "backtick",
        }
        for op, name in unsupported_ops.items():
            if source.startswith(op, i):
                raise LexError(
                    f"{name} is not part of the BNF; "
                    f"the parser only accepts the LE-language operators",
                    start_line, start_col,
                )

        raise LexError(
            f"unexpected character {ch!r}",
            start_line, start_col,
        )

    tokens.append(Token(TokenKind.EOF, "", line, column))
    return tokens