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
