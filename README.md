# LE Type System

This repo contains work on a small language for deterministic
programs, and a typechecker for said language that enforces low
equivalence, as well as generates an easycrypt proof for said program
of the same property.
   
## Remaining TODOs:
   
Currently the works for leaf proccedures which take synchronous
(public) control flow and only manipulate module level globals.

So it works for Q1 of Assignment 3 but not Q2 basically.
   
Approximetely in suggested order:

Fairly mechanical extensions to what works now:
- Procedure locals, arguments, and return values need explicit labels in
the grammar
- We need to include said variables in the proof goals (just append to
top_goal in the Proof.py functions)
- We need to tighten up the rules around returns to match the easycrypt
rules (ie only appear at the end), and include them in the proof goals
      
More conceptual:
### Subcalls
We have a procedure call rule, so we should be able to prove LE for
basic non-recursive programs. I think we can do that with the call
tactic and the prior proof for LE on the called procedure (maybe with
some slip by smt to do rearranging proof terms?)
     
### Async control flow (A3 Q2 style)

I think we can augment the current proof printers to take a side
parameter (of type bool|None), and emit one sided versions of the same
proof tree. 

If we are currently in sync mode and see an if that is not sync, then
produce subcalls to each side in async mode like:
if{1};if{2}.
{sync branch 1 proof}
{async left branch 1, followed by async right branch 2}
{async left branch 2, followed by async right branch 1}
{sync branch 2 proof}

I think once in async mode we shouldn't try to do any sync style
proofs, even if we could, since it's too much state to track. Better
to just exhaust one side and then the other, since the properties are
relatively simple. Except for....

Async whiles I am less sure about. In order to use async whiles, you
need to give a strictly decreasing integer expression (to prove
termination), and I don't see how to synthesize that in general. We
could add it as an explicit annotationn by the programmer maybe?

One alternative is to try hard to stay syncronous on structurally
similar inputs, like what we could do on A3 Q2. If the program
skeleton is the same but just with different variables, then we could
keep a version of the top goal for left and right and re-use the proof
tree traversal, mostly.
     
The other is to disallow these programs. Basically just allow public
while conditions. If we can't emit a proof, the program shouldn't type
check at all.
      
## Running the checker

All commands below are run from the project root
(`~\LE-type-system`). The examples assume the
project virtual environment lives at `.venv\`; adjust the interpreter
path if yours is elsewhere.

### Run the test suite

```bat
.venv\Scripts\python.exe -m pytest tests
```

### Run a single file

```bat
.venv\Scripts\python.exe __main__.py tests\examples\good_full.le
```
