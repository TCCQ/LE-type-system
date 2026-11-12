# LE Type System

This repo contains work on a small language for deterministic
programs, and a typechecker for said language that enforces low
equivalence, as well as generates an easycrypt proof for said program
of the same property.

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

### Run a single file

The CLI entry point is `__main__.py`. By default it parses,
typechecks, writes the EasyCrypt-compatible typechecked modules to a
generated `.ec` temporary file, and prints the path. 

The EasyCrypt printer currently emits a TODO comment for some constructs.

```bat
.venv\Scripts\python.exe __main__.py tests\good_full.le
:: C:\Users\...\Temp\le-xxxx.ec
```

Pass `--dump-ast` to also pretty-print the parsed modules in source
syntax. `--dump-output-ast` prints the typechecked AST in the same source
syntax (using minimal types), so its output matches the parsed input.
`--dump-deriv-ast` prints the typechecked AST with the full derivation
trees attached, which is useful for debugging the typechecker:

These flags print to stdout in addition to the generated file; the
generated path is printed last. All success paths exit with code `0`.

