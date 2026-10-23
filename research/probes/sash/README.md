# SASH witness precision regression

The real TinyLlama attempt found that upstream `int_gemm_exact` computes a dot
product in float64 when required, then unconditionally casts it to float32.
Odd integers above 2²⁴ are lost. One recorded attention score was 17,866,521,
while its witness maximum was 17,866,520. The unchanged Rust loader correctly
rejected the resulting negative shift and denominator mismatch.

`exact-gemm.patch` removes that final cast. Apply it only to SASH commit
`eb95bfa887299d1637550228d42086c27cbb2b3b` in a separate checkout. It changes the
witness candidate, so regenerate its inference and witness; do not repair old
arrays or reuse their proof claims. It changes no Rust proof or verifier code.

With SASH's locked Python environment installed, from the Hallmark checkout:

```sh
git -C "$SASH_SOURCE" apply --check "$PWD/research/probes/sash/exact-gemm.patch"
git -C "$SASH_SOURCE" apply "$PWD/research/probes/sash/exact-gemm.patch"
PYTHONPATH="$SASH_SOURCE" "$SASH_PYTHON" research/probes/sash/check_exact_gemm.py
```

The four cases compare the real helper against an int64 oracle: a small dot
product, positive and negative results above 2²⁴, and cancellation. The original
helper fails; the patched helper passes. This regression alone is not a full
model proof. See the [candidate decision](../../../docs/decisions/0065-exact-llm-witness-accumulators.md)
and [current evidence](../../evidence/llm-preflight-2026-10-23.json).

The patch derives from Apache-2.0 SASH source; its [licence](LICENSE.upstream) and
[notice](NOTICE.upstream) are retained here. The checker is Hallmark code under MIT.

## Shape reconstruction regression

The larger first-layer run serialized a proof but rejected it during verification:
the parameter-only constructor supplied placeholder scales outside the statement's
fold divisor bounds. `fold_shape.rs` exercises that constructor at alpha 9 and
three boundary/control values. `shape-reconstruction.patch` changes its dummy
scales; it leaves the proof constraints and acceptance checks intact. This is a
separate Rust candidate, described in [decision 0066](../../../docs/decisions/0066-llm-shape-reconstruction.md).

With the pinned upstream build environment, from the Hallmark checkout:

```sh
cp research/probes/sash/fold_shape.rs "$SASH_SOURCE/prover/tests/fold_shape.rs"
cargo test --manifest-path "$SASH_SOURCE/Cargo.toml" --release --locked --test fold_shape
# The original constructor fails the alpha-9 case.
git -C "$SASH_SOURCE" apply "$PWD/research/probes/sash/shape-reconstruction.patch"
cargo test --manifest-path "$SASH_SOURCE/Cargo.toml" --release --locked --test fold_shape
```

The regression alone does not establish proof validity. The
[execution record](../../evidence/llm-shape-reconstruction-2026-10-23.json) must
also show the saved proof verifying against its previously enrolled roots and
changed claims rejecting. The patch retains the upstream Apache-2.0 notices;
the new regression is Hallmark code under MIT.

The delayed-value profile also leaves an activation-scale equality unchecked;
see [decision 0067](../../../docs/decisions/0067-bind-the-value-activation-scale.md).
This constructor patch does not repair that relation. The full-response candidate
uses the existing non-delayed profile and the original Rust binary instead.

## Complete-response caller checks

`check_response.py` is the caller guard used by the TinyLlama proof-only experiment.
It requires the caller's expected prompt/answer IDs and 23 enrolled model,
preprocessed and shape roots. Its parameter digest reproduces the pinned upstream
shape-key encoding, including calibration float bit patterns. It rejects incomplete
file coverage, changed parameters, invalid token IDs, the open-scale Fold profile
and an output head that omits final normalization. These checks remain active
under `python -O`.

The guard is an importable research module, **not a cryptographic verifier or an
admitted Hallmark backend**. After `bundle(proof_directory, caller_expectations)`
succeeds, the real `zk-prover boundary-grid --verify` must check all 23 proofs,
22 layer links, exact prompt and enrolled model/preprocessed/calibration roots.
The fresh-worker protocol and [response evidence](../../evidence/llm-response-composition-2026-10-23.json)
record the complete sequence. Tokenization remains the caller's responsibility.
See [the LLM proof explanation](../../../docs/LLM-PROOF.md) for the statement and
measured limits. Unit tests exercise this guard; they do not generate STARK proofs.
