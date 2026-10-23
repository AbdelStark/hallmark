# 0066: Reconstruct legal fold placeholders during verification

2026-10-23. A new candidate under the standing implementation authority and
[decision 0064](0064-real-llm-build.md). The complete response proof remains the
acceptance gate. No backend adoption or existing classifier change.

The unchanged SASH binary generated first-layer proof bytes on the larger CPU
worker, then rejected them during verifier-side shape reconstruction. The
parameter-only constructor used a token scale exponent of 127, giving a fold
divisor exponent of 7, while the statement requires a split at 9. Its channel
scale placeholder also needs to satisfy the fold's finite remainder window.
No proof acceptance follows from successful serialization or a partial STARK check.

Freeze the original binary, proof, statement, claims and caller-enrolled roots.
Replay the rejection without the checkpoint or witness. Add a small regression
for legal placeholder divisor splits, including the observed alpha 9, before
applying a separately hashed source patch. Change only the parameter-only
constructor's dummy scales; retain every proof, root and calibration check.

The candidate passes this gate only if the existing proof verifies in a fresh
process, its derived shape root equals the previously enrolled root, and changed
prompt, model/calibration, statement and proof bytes reject. Run the upstream
synthetic digest and root/model rejection suites. Record this as new verifier
execution evidence, never as retroactive success of the original attempt.

Use a separately pinned, finite Linux CPU job because the Mac linking attempts
failed. No new proof campaign is needed to diagnose this constructor. Keep the
source, lockfile, image, patch, regression, input hashes and resource ceiling in
the run manifest; retain failed runs and remove temporary cloud storage after
verified local retention. All 22 layers and the output head still need complete
response verification before the user-facing LLM gate can pass.

The subsequent [scale-binding review](0067-bind-the-value-activation-scale.md)
disqualifies this delayed-value profile for the complete-inference demo. This
constructor regression remains a bounded diagnostic; even a passing saved proof
does not close that separate missing equality.
