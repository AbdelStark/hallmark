# 0058 — Specialized inference and trained MLP proof integration

Date: 2026-10-22. Status: owner-directed research implementation; no operational
backend adoption or reuse of historical experiments as qualification.

The owner requests specialized classifier verification, using a complete
commit-and-audit scheme or model-specific proofs, with no general-purpose zkVM.
The Mac and existing Modal, Vast.ai and HF Jobs credits are authorized for bounded
foreground work. GCP is not a dependency of classifier proving. Genuine hardware
provenance remains a separate extension; an ordinary GPU rental is not attestation.
Private account details and credentials stay outside this repository.

The proof library then in use (removed by 0087) supplied dedicated circuits; it
does not execute a VM here. Keep those circuits as correctness baselines rather
than assuming their maximum-size synthetic cost is a scalable encoder design.
Use the specialized-path review
to choose the next complete relation. Do not port a decoder prover to an encoder
by changing only weights, or claim a complete audit while skipping attention.

## Selected gate

The existing three-seed MLP trainer/exporter has no connection to an actual proof.
Test whether its exact learned integer exports can be proved by specializing the
first affine to byte-indexed weight lookups and integer sums. For a fixed row,
`sum_b weight[b] * count[b]` equals `sum_i weight[byte_i]` over active input bytes.
Conservative int32 envelopes cover both summation orders. This removes the
256-dimensional count-vector multiplication from the relation without changing
the classifier, rescaling, ReLU, chunk maximum or strict threshold semantics.

Mutable paths are the new trained-MLP circuit/controller/tests and its explicit
commands. Reuse the existing input-commitment circuit, indexed lookup, signed
rounding, bounded batch prover, trainer/exporter and separate pairing checker.
The original ten circuits, native evaluator, dataset, seeds and quality protocol
are unchanged. No new dependencies, architecture search or model-selection loop.

Freeze `fixtures/mlp-training.json`, seeds 17/29/43, all training settings and
threshold zero. This is an authored synthetic arithmetic/training fixture, not
an injection-quality study or calibrated policy. The exact trained exports must
become circuit constants; swapping in hand-authored marker weights fails the gate.
Store source, export, circuit and setup-key pins before proving.

First prove empty, `A` and `B` at capacity eight for all three seeds. Then prove
512 `A` bytes, 512 `B` bytes and 512 `A` followed by 512 `B` at capacity 1,024.
Require both decisions under the unchanged threshold in the larger native roster
before spending on larger proofs. Input capacity is an explicit rejection bound,
not truncation and not the native profile's 32,768-byte maximum.

For each model/capacity, a shared-key batch must produce three real proofs and
reject altered final units, hidden states and a threshold that changes the
decision. Rejection must be an unsatisfied constraint, not a dependency error.
An independent process using the separate pairing implementation checks the
actual proofs and the complete existing malformed/public-input/key/proof corpus.
Repeat from fresh training and setup directories; compare model exports,
decisions and rejection rosters, while retaining different fresh keys and all
failures. Timings are diagnostic observations, not performance distributions.

Each foreground run is bounded to 7,200 seconds, four worker threads, one research
worker, 8 GiB worker RSS and 8 GiB output; total retained checkout stays below
256 GiB. New compute spend is zero. New runs never overwrite failed attempts.

Qualification, hiding/security review, hardware provenance and real classifier
quality remain separate. Commit-and-audit would be a separately named evidence
class with trace disclosure; it cannot silently satisfy the ZK gate. No old
result is promoted or old experiment retuned by this decision.
