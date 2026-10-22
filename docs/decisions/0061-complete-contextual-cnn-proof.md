# 0061 — Prove the screened CNN without changing its model or threshold

Date: 2026-10-22. Status: bounded specialized proof experiment under standing owner
authority; no general-purpose VM or operational backend qualification.

The [second contextual screen](../../research/evidence/w16-contextual-screen-v2-2026-10-22.json)
passes its synthetic all-seed gate. Its protocol selected seed 17 before test for
proof integration. Freeze that exact export: quantization SHA-256
`8de31ae0215178f5c74aa43e58dd63511bc3b6a881c2045cc96def9e149b8f0b`, program
`ef90bf45331d2f9287090ab48c4eb9166a7d9c712efc1c2f5cf92b797640cc16`, threshold -3733.
No retraining, threshold adjustment, capacity expansion or new quality experiment.

Hypothesis: the complete learned byte-to-verdict relation produces real proofs,
rejects malformed computation witnesses and passes the separately implemented
pairing checker against independently pinned public inputs and keys. The baseline
is the existing native integer CNN export and its validated arithmetic DAG.

## Relation and binding map

The dedicated circuit uses the pinned Gnark library; it executes no VM. Constant
byte-embedding lookups feed every 24-byte causal window and all 32 convolution
channels. Active-byte masks apply before window extraction. Missing left context
is zero; inactive windows cannot enter global maximum pooling. Every affine,
nearest-even rescale, ReLU, per-channel maximum, output score and strict threshold
is constrained. Empty input pools to zero. The embedding and window layout match
the ten-node native graph; derived head scaling is algebraically removed while
retaining the native int32 envelopes and exactly the same integer score units.

The existing typed SHA-256 input-commitment circuit binds salt, profile, complete
byte count, canonical byte encoding and all active/padding positions. There is
one chunk. The existing 100-scalar layout carries caller-bound context, classifier,
input digest, counts, threshold and verdict. The controller derives these from
the complete opening and independently retains them before proving. Model
constants, native graph/program/profile, circuit and actual key are pinned before
the worker sees an assignment. The external verifier uses those pins, not
prover-supplied trust roots. Loader metadata alone is not an authenticated compiler.

Conservative embedding/kernel/head bounds must fit signed int32, including the
native graph's 256-scaled final affine. Numeric witness traces include all 96
positions, even when the admitted proof capacity is smaller. No learned weight,
checkpoint or raw trace enters git. Public model hashes are not proof of quality.

## Frozen experiment

Smallest fixture: authored Go arithmetic/mutation tests and native statement tests,
then real capacity-eight proofs of empty, NUL and UTF-8 inputs under the selected
learned model. Only after separate verification succeeds, run capacity 96 on the
lexically first held-out action-pair group (benign then positive) and that positive
prompt left-padded with spaces to exactly 96 bytes. This is a proof/cost roster,
not new task-quality evidence. Require the original pair's pass/block contrast at
the unchanged threshold before the larger setup.

Each capacity produces three proofs and rejects nine altered witnesses: final
byte, mask, convolution accumulator, rounded hidden value, ReLU, pooled value,
score, decision-changing threshold, and a consistently re-encoded different input
with the old neural trace. The last case tests input-to-network binding after
the commitment has been updated. Rejection must be an unsatisfied constraint,
not a parser/dependency failure. The separate py-ecc checker runs its full
malformed/public-input/key/proof corpus against actual proof bytes.

Repeat from two fresh setup/run directories. Require identical model/circuit
identities, original scores/decisions and negative outcomes; fresh keys must
differ. Preserve every failed run. Existing fixed circuit fingerprints and trained
MLP tests must remain unchanged/passing. No result promotes setup custody,
hiding, independent review, hardware evidence or the artificial grammar to a
qualified safety backend.

Mutable paths: the new circuit/tests/controller and explicit command dispatch,
plus evidence/operations/STATE/ledger. Native runtime/evaluator and trained model
are frozen. Per run: 7,200s, four proof threads, one research worker, 8 GiB RSS,
8 GiB output, total checkout <=256 GiB; new compute spend zero. Mac first; no
cloud job is necessary unless a separately recorded bounded fallback is needed.
