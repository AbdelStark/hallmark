# 0069: Reproduce the complete LLM response with one command

2026-10-23. Package the passing TinyLlama experiment without changing its model,
quantized arithmetic, calibration, proof relation or caller-enrolled roots.

The baseline is the complete 23-segment response and fresh proof-only mutation
suite in decision 0068. Its retained scripts require run-specific paths and an
operator to sequence the jobs. A reproduction must generate new witnesses and
new proofs; copying the saved proofs does not satisfy this gate.

`make e2e-llm` will prepare the pinned SASH Python environment, check every public
checkpoint file, regenerate the frozen calibration, generate the answer and
extract all witnesses on an Apple Silicon Mac. Native generation now stops at
EOS; the expected eight tokens are unchanged. Re-run the exact-GEMM regression
and the unchanged float compatibility gate before extraction. Select embedding
only for layer 0 and final normalization only for the output head.

Three foreground HF CPU jobs build the original Rust prover, prove the response,
and verify its proofs without a model or witness mount. Pin the source archive,
Rust toolchain, CUDA image, Python lock and exact case. Compare newly derived roots
with caller-owned roots frozen before this run. Credentials stay in the local
controller; the jobs receive only reviewed public inputs.

The controller reads current provider rates and rejects a run whose fixed provider
timeouts exceed the requested $2.10 ceiling, including a storage reserve. The
build and verifier use CPU Upgrade for at most 30 minutes each; proving uses CPU
Performance for at most 60 minutes. Jobs run sequentially with one attempt, finite
creation deadlines and retained outputs before temporary bucket deletion. Failed
runs remain separate. An uncertain creation response is not evidence that no job
exists; retain its bucket and identify that uncertainty.

Pass only when a fresh run reproduces the prompt, calibration and answer, produces
all 23 proofs against the enrolled roots, verifies all 22 links in two fresh
processes, and rejects all 14 mutations. Record real costs, commands, hashes and
missing/failed checks. The small native preparation check passed in 29.64 seconds
with 13.27 GB peak child RSS; it is not the full workflow result.

The first full invocation failed the exact-GEMM check before creating any cloud
job. Git discovered the enclosing Hallmark checkout and silently skipped the
patch in the extracted upstream directory. Set `GIT_CEILING_DIRECTORIES` for
patch application; a regression reproduces that nested-checkout layout. A fresh
source extraction then passes all four int64 oracle cases. Preserve the failed
run instead of repairing it in place.

The optional `llm` extra names the already locked Hub SDK. Its first repository
check rejected the old whole-lock review hash. A new review confirms that all
52 third-party package entries are unchanged, carries forward their existing
licence evidence and pins the new lock. Historical reviews remain unchanged.

The [fresh full run](../../research/evidence/llm-e2e-reproduction-2026-10-23.json)
passes in 31 minutes 15 seconds. All 23 proofs are generated anew; all 69 proof,
statement and claim files match the baseline byte for byte. Two fresh proof-only
processes verify the complete response in 80.11 and 78.45 seconds; all 14 mutations
reject. The three jobs' combined compute bound is $0.31, not an invoice. All
outputs are retained and all temporary buckets are deleted.

The fixed authored prompt remains an engineering case. This command does not
qualify language-model quality, hiding, authenticated enrollment, independent
security or hardware provenance. The classifier `make e2e` path remains available.
