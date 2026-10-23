# 0065: Preserve exact integers in the LLM witness

2026-10-23. A new candidate under the standing implementation authority and
[decision 0064](0064-real-llm-build.md). No change to Hallmark's classifier
statements, Rust proof relation or verifier acceptance rules.

The first real TinyLlama layer failed before proof generation. The upstream
Rust loader recomputed a different attention denominator on one of 1,024 rows.
A local reproduction identifies head 1, position 16: the integer Q/K dot product
is 17,866,521, but the Python witness records its maximum as 17,866,520. The
negative shift is outside the exponent table. This is a witness error; the
loader's rejection must remain.

The cause is `int_gemm_exact`'s unconditional final `.float()`. Its float64 dot
product is exact, but float32 cannot retain that odd integer. The bounded
candidate removes only this cast, preserving the dtype selected from the
partial-sum bound. All four callers were inspected: widened output projection,
integer-softmax scores, integer attention/value multiplication and quantized
Q/K attention. The [regression](../../research/probes/sash/check_exact_gemm.py)
uses int64 dot products and must fail on the original helper before passing on
the candidate. No dependency is added to Hallmark's core environment.

Freeze the source commit, patch hash, model revision, calibration, prompt and
expected answer in a new run directory. Regenerate inference and every witness
segment. Keep numerator arrays for the upstream comparison, check all row maxima
and denominators against exact integer products, and retain the failed original.
A passing model-root build is only the next gate; the full response still needs
actual proofs and caller-pinned mutation rejection.

The candidate may change intermediate values or output text. New measurements
must name the patch and must not inherit the original witness's evidence claims.
The reviewed eight-token answer is an engineering fixture, not a held-out quality
test. Existing classifier experiments and qualification flags remain unchanged.
