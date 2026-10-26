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

## General path

We need:

- Parse the language into an AST
- check the AST for basic sanity
- check the AST for low equivalence (disallow high to low assignment,
    more to come)
- produce a record of the checking process as a concrete piece of data
    (likely a recursive proof tree-ish value)
- consume AST and produce easycrypt module definition of the same
    program
- consume record check and produce a lemma for low equivlanece for
    said module