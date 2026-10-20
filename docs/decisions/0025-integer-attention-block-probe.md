# 0025 — Integer attention and feed-forward operator block

Date: 2026-10-20. Scope: W18 / issue #19, after the bounded MLP probe.

Test the next qualification stage before choosing an encoder. The candidate is
a fixed two-token, two-feature attention/feed-forward block. It exercises
embedding gather, affine maps, transpose, matrix and elementwise multiplication,
bounded lookup, broadcast masks, signed rescaling, residual addition, ReLU and
masked sum/max pooling together. It is not a complete encoder, tokenizer,
trained classifier, Hallmark input commitment or operational proof adapter.

The embedding vocabulary has four entries. Each token and each Boolean mask
bit is a public input; the fifth public value is the signed output score encoded
as `score + 2^31`. A separate Python arithmetic oracle freezes every intermediate
tensor. Prove all 64 combinations of the two token IDs and two mask bits,
including empty and noncontiguous masks. Check that changing a masked token
does not change the output. No input or threshold is chosen from test results.

Attention scores range from -2 to 2. A fixed table maps them to powers of two.
Masked row sums index a fixed table of ties-to-even `256 / denominator`;
zero maps to zero. The weighted value sum rounds from eight fractional bits.
The feed-forward and final affine outputs divide by two with signed
ties-to-even rounding. The tables and rounding rules define this candidate;
no equivalence to a floating pretrained transformer is claimed. Layer
normalization and a complete multi-block encoder remain untested.

The circuit constrains lookup indices/values and all 89 private intermediate
values. Every recorded value is int32. The fixed small weights, input ranges
and graph bound all partial sums; this is not arbitrary-graph overflow handling.
A malicious prover cannot choose a different trace to satisfy the same inputs.
Negative cases mutate each intermediate, each public field, input/mask/score
ranges, proof bytes and setup key. Expected rejection requires a well-formed
backend failure report; crashes do not count as successful rejection.

The public fixture is a standalone block relation with five public fields.
It does not use or weaken Hallmark's 100-field proof-input layout. Its separately
pinned setup key identifies the exact circuit; a key supplied only by a proof
is not an enrollment. The shared checked setup/prove/verify code is reused,
and earlier rule/MLP examples must still verify under the rebuilt binary.

Use the already reviewed gnark/toolchain/modules, a new source snapshot and
fresh local setup under the owner-approved Mac envelope. Record the exact
case roster, wall/CPU/memory/storage caps and consumed prior budget before
execution. Keep failures and stop on a violated bound. No new dependency,
download, HF token, GPU job or private input is required.

Success supports only this fixed operator block. The existing backend security,
setup and shared-verifier limitations remain; `qualified_backend` stays false.
The qualification runner and full admitted encoder gate must still be completed
before backend selection or merging W18.
