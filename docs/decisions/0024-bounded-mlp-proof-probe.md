# 0024 — Bounded integer MLP proof experiment

Date: 2026-10-20. Scope: W18 / issue #19. This extends the
[local proof probes](0022-local-proof-probes.md); it does not select a backend.
Historical rule results retain their original source, circuit and setup identities.

The candidate proves the fixed synthetic MLP exported by the native W11 fixture,
with an eight-byte input limit and two four-byte chunk slots. Its three hidden
units compute byte-count affine expressions, divide by two with nearest
ties-to-even rounding, apply ReLU, then apply the output affine expression and
the same rounding. The final score is the maximum over actual chunks; equality
to threshold two blocks. Empty input has one empty chunk. A second inactive slot
computes an empty chunk but cannot enter the maximum.

The circuit constrains all 22 private intermediate values against the native
fixture: three accumulators, three rounded values, three activated values,
the output accumulator and score for each slot. Signed values are range checked
as int32; witness transport uses `value + 2^31`. Rounding separates sign and
magnitude and increments an odd quotient at a half tie. The exact fixed weights
and count bound make every affine partial sum fit int32. This is not an
implementation of arbitrary imported MLPs or a general overflow strategy.

`input.go` contains the shared complete-input commitment and public field
constraints. The input is 0–8 bytes with explicit zero padding, exact canonical
CBOR and SHA-256. `graph.go` shares setup, checked artifact decoding, assignment
parsing, proving and fresh-process verification between the rule and MLP.
The refactor changes constraint order and therefore circuit/key identity; the
rule experiment must run again under a fresh setup. Prior proofs are not reused
with the new circuit.

The evaluator freezes nine native vectors before proving: empty input, one byte,
threshold equality, negative arithmetic, exact chunk length, a positive late
chunk, real zero bytes, maximum length and a UTF-8 boundary. An independent
arithmetic formula checks each native intermediate value when building the
fixture. Actual proof checks distinguish this from a witness-only comparison.
The controller adds one invalid prover assignment for each of the 22 layer
values, in addition to the rule probe's public-input, private-byte, padding,
coverage, proof-byte and setup-key mutations.

The recorded local protocol admits one process at a time, four Go threads,
120 seconds of wall and measured CPU per case, 1,800 seconds per graph,
16 GiB measured peak process RSS and 4 GiB measured output per graph. These
limits fit the current owner authority. Aggregate storage and RSS checks happen
after each process; Go's memory limit is soft, and the macOS CPU-limit request
is not a reliable hard boundary. Network and fork denial remain enabled.
Failures and their raw costs are preserved; no automatic retry changes a result.

The same source, licence, setup and gadget limitations as decision 0022 apply.
The classifier enrollment is synthetic, salt derivation and the B1 transcript
connection remain outside this circuit, setup is local, and the verifier shares
gnark with the prover. Neither hiding nor independent security review is
established. `qualified_backend` remains false. The
[backend declaration](0023-backend-declaration-contract.md) is a separate
structural record and cannot convert these experiments into qualification.
Operator-block and complete admitted encoder evidence remain necessary.
