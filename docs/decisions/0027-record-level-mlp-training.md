# 0027 — Record-level byte MLP training

Date: 2026-10-20. Scope: W15 / issue #16, beginning with the learned byte MLP.

Hypothesis: a bounded, deterministic CPU fit can preserve record-level labels
across complete inputs, resume exactly on the same locked environment, and export
the existing native integer MLP. The baseline is a synthetic-weight MLP runtime
and a byte-logistic trainer that rejects multi-chunk training records. Mutable
paths are the new training/config/checkpoint code, the shared MLP export builder,
fixture/check commands, tests and research documentation. The historical logistic
trainer, assay, data, thresholds and results retain their identities.

Fit accepts only explicitly supplied training records. It rejects calibration
or test rows before feature extraction or optional-library import; no implicit
filtering is allowed. The trainer has no dataset path, calibration set or test
callback. It validates provenance fields, unique record IDs, one prompt policy,
complete byte limits, both labels and a declared dense-feature budget.

Each record is split contiguously into the fixed byte chunk size, including an
empty chunk for empty input. Inputs are byte counts divided by chunk size. A
single hidden affine/ReLU layer produces one logit per chunk. The record logit
is their maximum. Binary cross-entropy is applied once per record; the first
maximizing chunk receives its subgradient on ties. Positive records do not label
every chunk positive. L2 regularizes weight matrices only. Training uses explicit
float64 full-batch SGD with momentum, a fixed seed and no dropout or shuffle.
NumPy contractions disable the optimizer so they do not dispatch to BLAS.

The finite configuration fixes width, chunk/input sizes, learning rate, momentum,
L2, epoch limit and convergence tolerance before fitting. Every completed epoch
records loss and gradient norm. Hitting the epoch limit without the tolerance
criterion is reported as nonconvergence, never silently called converged. A bounded
step invocation may stop early for checkpointing without changing the config.

A checkpoint contains weights, biases, momentum, epoch, loss, initialization RNG
state and exact training/config/source/environment identities. Resume requires
an external checkpoint hash and identical inputs, implementation and environment.
JSON research records contain numbers, not executable pickle state. Their identities
use the existing research commitment helper; floating values never enter the
float-free v1 wire codec. Errors retain the
last externally written checkpoint; fitting does not overwrite files.

Export uses explicit power-of-two int8 weight scales, int32 biases/accumulators,
ties-to-even rounding, recorded hidden/score unit scales and no saturation. Output tensors retain the
native integral-score contract: scaling is folded into the affine fractions,
and the export records how to compare its integer score with the float logit. The
existing native MLP remains the normative integer executor. Exported graph/file
identities do not enroll a backend or key, prove training, or establish task quality.

Pass this increment only after numerical gradient/max-objective checks,
fresh-versus-resumed equality, changed-input/config/environment rejection,
integer export/native execution, one-thread fixture fitting and both package
gates. Store raw source/config/environment hashes and numeric fixture results
before prose. Synthetic records are software tests, not injection-quality data.

The complete W15 comparison roster, five grouped train-internal folds, three-seed
selection, approved guard comparison and calibration/evaluation integration remain
required before W15 can close. Real measurements still need the reviewed source,
split, candidate and evaluator dossier. No dataset/model download, external
inference, HF job or new dependency is needed for this increment.
