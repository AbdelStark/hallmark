# 0035 — Measure complete-input commitment scaling

Date: 2026-10-21. Scope: W18 / issue #19, new component experiment.

Hypothesis: an indexed lookup argument removes the quadratic CBOR-packing loop
in the eight-byte probe and permits measuring the full 32,768-byte commitment
component. Baseline: the existing rule/MLP relation supports eight bytes only.
The new circuit, optional runner, tests and evidence are mutable. Historical
rule/MLP/block circuits, fixtures and qualification results remain unchanged.

This component has 33 public fields: unit count and 32 digest bytes. It proves
the existing `H(input, [salt, profile, count, byte-list])` relation for a synthetic
fixed profile pin. It does not implement a classifier, tokenization, input-salt
derivation, context binding, chunk verdict or operational enrollment. It is not
the 100-field Hallmark proof statement. No protocol/evaluator semantics change,
backend selection or prior scientific result reuse follows from this experiment.

Canonical CBOR count/list headers handle the 23/24 and 255/256 transitions.
An explicit prefix witness advances by exactly one or two encoded bytes for
each active uint8. Inactive input and encoded padding must be zero. All dynamic
reads constrain both their index and value with gnark's existing pinned
`std/lookup/logderivlookup` argument. Every encoded byte is range-checked, and
the salted preimage is passed to the existing SHA-256 gadget. Explicit prefix
witnesses avoid repeatedly expanding a growing linear expression in the builder.

The pinned Apache-2.0 gnark v0.16.4 source at
`e974abb44722dd201a7f1949baeabca0fef5866e` implements
[indexed tuple lookup](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/std/lookup/logderivlookup/logderivlookup.go)
and a deferred log-derivative multiset argument. Review covers query/table tuple
commitment before challenge derivation, hint-result constraints and bounded
indices. It is a source inspection, not independent cryptographic review. The
existing BLS12-381/Groth16, Fiat–Shamir, hiding and local setup limitations apply.
No new dependency or network execution is needed; source hashes travel with the run.

Pass criterion: independent canonical codec/hash checks at empty/header/max
boundaries, eight actual proofs across eight-byte and 256-byte profiles, changed public fields/key/proof rejection,
invalid byte/header/prefix/padding prover rejection and retained real maximum-size
compilation costs. Compilation is not a proof. An interrupted
maximum compile is a failed feasibility observation, never qualification success.
Run the smallest profile before the larger profile. Keep failure directories.

The existing conservative 4,955.640-second accounting and entire 1,500-second
staged reservation are retained. Of the remaining 744.360 seconds, reserve 700
for this increment, retaining the initial failed 118.892-second command and
allowing at most 420 seconds for the corrected sequential experiment. Each setup
or batch is capped at 120 wall seconds / 480 CPU seconds; maximum compilation
remains capped at 90 wall seconds / 360 CPU seconds. Use four
threads and the existing 1 GiB Go soft memory limit. Measured RSS must stay below
16 GiB; new artifacts below 4 GiB and total retained storage below approved 40 GiB.
No token, paid compute or scheduler is involved. Full input proofs, layer
normalization, full encoder and independent qualification remain separate gates.


The first candidate's three small proofs verified, but direct `IsSolved` rejected
valid empty input on the 256-byte circuit: gnark requires the prover's actual
commitment hint. Its invalid solver outcomes are not admissible negative evidence.
The failed source/controller identities and outputs are retained. The corrected
candidate removes solver-only commands entirely, batches real `groth16.Prove`
attempts after one proving-key load, and verifies every successful proof in a
fresh process. It records each completed batch outcome before the next attempt.
No placeholder hint, dummy setup or simulated cryptographic success is introduced.
