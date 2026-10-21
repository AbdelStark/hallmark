# 0038 — Test a compact Boolean-wire compiler cache

Date: 2026-10-21. Scope: W18 / issue #19, optional compiler research candidate.

The prefix-coverage candidate still cannot compile the 32,768-byte commitment
inside the local memory envelope. An earlier sampled heap attributes substantial
allocation to gnark's Boolean-expression cache. Hypothesis: a bitmap for individual
unit-coefficient wires can remove their hash/expression allocation while preserving
the exact compiled relations. This is a separately modified dependency candidate,
not unchanged upstream gnark or a qualified backend.

The patch targets only `frontend/cs/r1cs/builder.go` from the reviewed gnark
v0.16.4 commit `e974abb44722dd201a7f1949baeabca0fef5866e`. The upstream module cache
stays untouched; a fresh copy retains its Apache-2.0 licence and full original/
patched inventories. One of 1,264 files changes. No dependency is added. The
original module, probe module and package defaults remain pinned to upstream.

After upstream constant handling, a one-term expression with positive wire ID
and coefficient exactly one uses a packed bitmap. Every other expression keeps
the original sorted/hash/bucket path. Public variables, then secret variables,
then internal variables receive distinct wire IDs in this compiler's allocation
order. Wire zero is the constant-one wire and never enters the bitmap.
`MarkBoolean` still records metadata only; it does not add a constraint.

The smallest fixture checks constants, repeated marks/assertions, zero aliases,
non-unit/negative coefficients, general expressions and public/private/internal
wire separation across bitmap words. It accepts an all-zero witness and rejects
a value of two in each of 132 input wires. Compare the full serialized R1CS bytes
for installation, rule, MLP, attention block and input capacities 8/32/256 across
both builds; equal counts alone do not pass. This establishes fixture equivalence,
not a proof of compiler correctness for arbitrary circuits.

Freeze the patch, source copies, builds, worker, controller and existing native
vectors before fresh setup/proving. Repeat the eight small proofs, 18 invalid
prover witnesses, public-field mutations, alias, changed proof and wrong key.
Then retain one bounded maximum compile, including a failure or cutoff. Do not
reuse historical proofs as qualification of the patched compiler. Complete encoder,
operational enrollment and independent verifier/security/setup/hiding gates remain.

Reserve 550 of the 580 remaining unreserved seconds in the existing 7,200-second
local proving allocation, leaving 30. The frozen controller copy reduces its
resource deadline from 420 to 330 seconds; evaluator semantics and test roster are
unchanged. Maximum compilation keeps its 90-second cap. Use one foreground job,
four threads, 16 GiB peak ceiling with a 14 GiB sampled cutoff, 4 GiB new artifacts,
40 GiB total retained storage and zero spend. All failures and software validation
count. No token, HF job, private input, contact or scheduler is involved.
