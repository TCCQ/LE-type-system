# LE Type System

This repo contains work on a small language for deterministic
programs, and a typechecker for said language that enforces low
equivalence, as well as generates an easycrypt proof for said program
of the same property.

## BNF Grammar (tentative)

```BNF
<program>          ::= <module> | <module> <program>

<module>           ::= "module" <m-name> "=" "{" <defns> "}"
<defns>            ::= ε | <defn> <defns>
<defn>             ::= <module-var-defn> | <proc-defn>

<module-var-defn>  ::= "var" <name-list> ":" <type> "::" <visibility> ";"
<visibility>       ::= "public" | "private"

<proc-defn>        ::= "proc" <p-name> "(" <p-args> ")" ":" <type> "=" "{"
                       <block> "}"

<p-args>           ::= ε | <p-arg> <p-args-tail>
<p-args-tail>      ::= ε | "," <p-arg> <p-args-tail>
<p-arg>            ::= <v-name> ":" <type>

<block>            ::= <local-var-decls> <stmts>
<local-var-decls>  ::= ε | <local-var-decl> <local-var-decls>
<local-var-decl>   ::= "var" <name-list> ":" <type> ";"
<name-list>        ::= <v-name> | <v-name> "," <name-list>

<stmts>            ::= ε
                     | <simple-stmt> ";" <stmts>
                     | <compound-stmt> <stmts>

<simple-stmt>      ::= <assign-stmt> | <return-stmt> | <call-stmt>
<compound-stmt>    ::= <if-stmt> | <while-stmt>

<assign-stmt>      ::= <lvalue> "<-" <expr>
<lvalue>           ::= <v-name> | <m-name> "." <v-name>

<return-stmt>      ::= "return" <expr>

<while-stmt>       ::= "while" "(" <expr> ")" "{" <block> "}"

<if-stmt>          ::= "if" "(" <expr> ")" "{" <block> "}" <if-tail>
<if-tail>          ::= ε
                     | "elif" "(" <expr> ")" "{" <block> "}" <if-tail>
                     | "else" "{" <block> "}"

<call-stmt>        ::= <v-name> "<@" <p-name> "(" <c-args> ")"
<c-args>           ::= ε | <expr> <c-args-tail>
<c-args-tail>      ::= ε | "," <expr> <c-args-tail>

<type>             ::= <base-type> <list-tail>
<list-tail>        ::= ε | "list" <list-tail>
<base-type>        ::= "int" | "bool" | <type-name> | <m-name> "." <type-name>

<expr>             ::= <bin-expr>

<bin-expr>         ::= <unary-expr>
                     | <bin-expr> <binop> <unary-expr>

<binop>            ::= "+" | "-" | "*" | "/" | "%/"
                     | "<" | "<=" | ">" | ">=" | "=" | "<>"
                     | "&&" | "||"

<unary-expr>       ::= <u-opt> <unary-expr> | <atom>
<u-opt>            ::= "-" | "!"

<atom>             ::= <literal> | <v-expr> | "(" <expr> ")"

<literal>          ::= <integer-literal> | "true" | "false"

<v-expr>           ::= <v-name> | <m-name> "." <v-name>

<v-name>           ::= <identifier>
<m-name>           ::= <identifier>
<p-name>           ::= <identifier>
<type-name>        ::= <identifier>

<identifier>       ::= <letter> <id-tail>
<id-tail>          ::= ε
                     | <letter> <id-tail>
                     | <digit> <id-tail>
                     | "_" <id-tail>

<integer-literal>  ::= <digit> <digits>
<digits>           ::= ε | <digit> <digits>

<letter>           ::= "a" | ... | "z" | "A" | ... | "Z"
<digit>            ::= "0" | ... | "9"
```

## Implementation

We are writing this in python with static types enforced by
mypy. Language projects are a very good match for algebraic data
types, so I would suggest we follow the general style like this:

https://stackoverflow.com/a/71519690

There a lot of ways of encoding this but as far as I can see this is
the cleanest.

## Running the Parser and Test Suite

All commands below are run from the project root
(`~\LE-type-system`). The examples assume the
project virtual environment lives at `.venv\`; adjust the interpreter
path if yours is elsewhere.

### Run the test suite

```bat
.venv\Scripts\python.exe -m pytest tests -v
```

The suite in `tests/test_examples.py` parses every file in `tests/`
and asserts on the resulting AST (for the well-formed programs) or on
the specific error and its source line (for the malformed ones). A green
run looks like:

```
tests/test_examples.py::test_good_simple_module_shape PASSED
tests/test_examples.py::test_good_simple_encrypt_body PASSED
tests/test_examples.py::test_good_full_module_shape PASSED
tests/test_examples.py::test_good_full_compute_statement_layout PASSED
tests/test_examples.py::test_good_full_elif_is_desugared_into_nested_if PASSED
tests/test_examples.py::test_good_full_helper_and_go PASSED
tests/test_examples.py::test_bad_file[bad_theory.le-...] PASSED
tests/test_examples.py::test_bad_file[bad_operator.le-...] PASSED
tests/test_examples.py::test_bad_file[bad_syntax.le-...] PASSED

============================== 9 passed in 0.05s ==============================
```

### Run a single file through the parser

Any source file can be fed to the parser directly to see the AST it
produces. The CLI entry point is `__main__.py`; pass `--dump-ast` to
pretty-print the parsed modules in source syntax:

```bat
.venv\Scripts\python.exe __main__.py tests\good_simple.le --dump-ast
```

`--dump-output-ast` prints the typechecked AST in the same source syntax
(using minimal types), so its output matches the parsed input.
`--dump-deriv-ast` prints the typechecked AST with the full derivation
trees attached, which is useful for debugging the typechecker:

```bat
.venv\Scripts\python.exe __main__.py tests\good_full.le --dump-output-ast
.venv\Scripts\python.exe __main__.py tests\good_full.le --dump-deriv-ast
```

All three flags exit with code `0` on success.

For a malformed or unsupported input the parser instead writes a single
`file:line:column: error: …` line to **stderr** and exits with code
`1`:

```bat
.venv\Scripts\python.exe __main__.py tests\bad_theory.le
:: tests\bad_theory.le:1:1: error: theory blocks are not supported (...)

.venv\Scripts\python.exe __main__.py tests\bad_operator.le
:: tests\bad_operator.le:4:16: error: exponentiation '^' is not part of the BNF (...)

.venv\Scripts\python.exe __main__.py tests\bad_syntax.le
:: tests\bad_syntax.le:3:5: error: expected ';' after module variable definition (...)
```

### Example files

The `tests/` directory holds one file per behavior the parser is
expected to handle, and each is wired into `tests/test_examples.py`:

| File | Parses? | Demonstrates |
|------|---------|--------------|
| `good_simple.le`        | yes | Minimal module: two global vars, one proc with a local var, an assignment, and a `return`. |
| `good_full.le`          | yes | `while`, `if`/`elif`/`else` (desugared to nested `If`), local variables, and a `dst <@ proc(args)` call. |
| `bad_theory.le`         | no  | EasyCrypt `theory` / `require` / `end` preamble — rejected by the lexer. |
| `bad_operator.le`       | no  | An operator outside the BNF (`^`) — rejected by the lexer. |
| `bad_syntax.le`         | no  | A missing `;` after a module variable — rejected by the parser. |

To add a new case, drop a file in `tests/` and register it in
`tests/test_examples.py` (as a new `test_...` function for well-formed
inputs, or as a new row in the `@pytest.mark.parametrize` table for
inputs that must fail).

## General path

We need:

- Parse the language into an AST (Done!)
- check the AST for basic sanity
- check the AST for low equivalence (disallow high to low assignment,
    more to come)
- produce a record of the checking process as a concrete piece of data
    (likely a recursive proof tree-ish value)
- consume AST and produce easycrypt module definition of the same
    program
- consume record check and produce a lemma for low equivlanece for
    said module