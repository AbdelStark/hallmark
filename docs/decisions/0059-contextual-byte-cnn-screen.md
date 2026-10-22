# 0059 — A frozen contextual byte CNN screen

Date: 2026-10-22. Status: bounded synthetic research, under standing owner
implementation/data authority. No policy adoption or reuse of historical quality
results. This new experiment does not change the existing evaluator or its gates.

The next gate in STATE is a useful compact contextual candidate with a complete
operator/binding map. Start with local scope discrimination before a transformer
port: the previous byte-count MLP cannot distinguish equal-histogram order pairs.
This is a necessary structural screen, not sufficient safety quality evidence.

## Frozen hypothesis and protocol

The hypothesis is that a small trained byte CNN distinguishes a forbidden action
in an active `run` clause from the identical action in an inert `quote` clause,
including action combinations held out from fitting. The artificial grammar and
action lists define labels; they do not model arbitrary natural-language intent.
The [source review](../../fixtures/contextual-source.json) records agent review,
purpose, licence and the approved synthetic-data authority. No external data or
model download is needed; no private text informs the authored examples.

The [protocol](../../fixtures/contextual-protocol.json) pins all 200 records and
three seeds, 17/29/43. Each of 100 action-pair groups has two opposite labels and
identical byte histograms. Hash-sort whole groups into 60 train, 20 calibration,
20 test. Templates and action vocabulary are shared: this measures compositional
recombination within one grammar, not unseen-language or attack-family quality.
Both descendants stay in their group. A byte-count MLP assigns each pair the same
score, so its TPR equals its FPR on this paired screen at any threshold.

Train the single fixed candidate for 200 full-batch Adam epochs in CPU float64,
without candidate selection, early stopping or test feedback. Save parameters,
optimizer moments, epoch, loss history, source/runtime/data/config identity.
Repeat uninterrupted and 100+100 resumed training for every seed. Initialization
uses a fixed PCG64 seed; full-batch training consumes no later randomness.

Export before calibration. Use the existing integer calibration function at
target FPR 0.01 (zero allowed errors with 20 benign calibration examples). Retain
the threshold and complete export enrollment before the first test score.
The prespecified engineering screen requires test TPR >= 0.8 and FPR <= 0.1 for
all three seeds. Preserve failures; do not tune this candidate on the test.
Repeat the exact experiment in fresh directories and compare substantive bytes.
Repetition checks software reproduction, not a second independent quality sample.

## Complete numerical relation

`UTF-8 bytes -> embedding -> masked causal windows -> affine -> ReLU -> masked
global max -> affine integer score -> strict threshold`.

The profile admits 0–96 bytes and rejects longer inputs, with no truncation or
multiple chunks. Four-dimensional learned embeddings feed eight learned
24-byte causal filters. Every active byte is the end of one window; missing
left context is zero. Token zero remains a real byte when its mask is active.
Padding embeddings are masked before window extraction, and inactive positions
are excluded from pooling. Empty input pools to zero. This local receptive field
does not represent arbitrary long-range scope. There are 1,809 learned parameters.

Embedding/kernel/head values use separately selected power-of-two int8 scales,
without clipping. Biases are int32; hidden activations have eight fractional bits.
All rescaling uses nearest ties to even. The final score is an integer in units
of 1/256 float logit; multiplying the derived head constants and bias by 256
converts its declared output fraction to zero without changing those units.
The existing graph validator must establish every conservative int32 envelope.

The export uses ten existing nodes: embedding gather, mask reshape, embedding
mask multiply, window gather, causal-mask multiply, flatten reshape, convolution
affine, ReLU, masked maximum and score affine. The saved arithmetic profile binds
every producer/consumer edge, constant shape/range/scale and parameter file.
The existing native encoder binds exact tokenizer, weights, profile and complete
opening bytes; a separate NumPy integer oracle checks every calibration/test score.
Floating parent drift and threshold disagreements are reported separately.

This is a software candidate. Backend/key/setup fields are explicitly zero in
the research manifest, never operational enrollment. A later specialized proof
must bind the same bytes, all ten nodes, every window, maximum and threshold to
an independently enrolled model/key. No proof or hiding claim follows from export.

## Scope and acceptance

Mutable paths: new CNN research scripts/tests, authored fixture/protocol/source
records and their evidence/docs. Reuse the locked train extra and existing DAG,
encoder, opening, calibration and metrics code unchanged. No new dependency.

Before full runs, check numerical gradients, exact resume and identity rejection,
float/int export ranges, independently calculated integer scores, empty/NUL/UTF-8,
maximum byte length, threshold equality, altered weights and overlength rejection.
Require all three quality-screen gates, byte-identical training/export repetition
and unchanged runtime source hashes, or retain an explicit failed result.

Mac first: each run <=7,200 seconds, one thread/worker, 8 GiB RSS and 1 GiB output;
total checkout <=256 GiB, new compute spend zero. Resource sampling/kill conditions
are retained with the local execution plan. No cloud job is necessary for this
candidate. Issue #17 remains open until qualified-graph acceptance is satisfied;
this screen does not supply backend, privacy, hardware or operational qualification.
