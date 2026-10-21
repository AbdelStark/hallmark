# 0042 — Prepare an optional bounded G1 batch candidate

Date: 2026-10-21. W18 / issue #19. Status: component validation passed; maximum setup unvalidated.

The pinned setup allocates all G1 Jacobian outputs before converting them to
affine. The maximum commitment's domain alone implies at least nine GiB for that
Jacobian slice. Prepare an optional gnark-crypto patch that keeps at most 4,096
Jacobian results per existing worker and writes each converted chunk into the
final ordered affine array. Preserve the scalar window, table, digit partition,
group arithmetic and circuit statement. No artifact or resource cap changes.

The patch remains outside the default module and HF bootstrap. Apply it only to
a fresh writable module copy with exact pre/post source hashes and a complete
inventory. Preserve the existing compiler-cache experiment separately. The
default dependency and all historical binaries/results keep their original pins.

Freeze `patches/g1_batch_test.go` before evaluating this candidate. It compares
coordinates and encoded points with separate scalar multiplication, checks input
immutability and emits ordered-output hashes for baseline/candidate comparison.
Its deterministic scalar set includes zero, one, minus one and wider values;
bases include the generator and infinity. Fixed lengths include empty and chunk
boundaries. Also require `runtime.NumCPU()*4096+1` and assert the actual parallel
partition crosses a chunk boundary: a thread cap does not determine this library's
number of partitions. This is a new evaluator identity, not a change to historical
proof or policy results.

The unchanged upstream three-point baseline passes. The first candidate fails
to build because the original minimum-cost variable shadows Go's `min` built-in.
Rename that variable without changing the cost expression or comparisons. Retain
the failed build and its source identity. Exact patch application and Go parsing
passed for the correction at preparation time. The subsequent
[approved validation](0043-approved-local-validation-extension.md) builds it,
passes all 16 point cases and reproduces all seven circuit fingerprints. The
existing cubic proof/reader unit fixture passes in both builds. A separate frozen
allocation fixture retains one sample per variant with identical output digests;
this is not maximum setup or statistical performance evidence. See
[numeric results](../../research/evidence/w18-approved-validation-2026-10-21.json).

Preparation uses the existing local reservation; it does not expand authority.
The owner subsequently approved 120 Mac-only validation seconds under decision
0043. That increment covers repository/package gates and bounded corrected-candidate
component checks. It does not authorize a maximum setup/proving campaign or another
cloud job. Preserve the earlier preparation failures and exhausted reservation.

Before a maximum attempt, require full baseline/candidate point equality, the
seven serialized circuit fingerprints, small actual setup/proof/rejection checks,
and bounded allocation/latency measurements. Then freeze a plan accounting for
the key's multi-GiB serialized size, aggregate storage, memory, host, deadlines
and remaining authority. Neither point equality nor lower temporary storage
establishes maximum feasibility, a complete encoder, independent security,
accepted setup lineage or a qualified backend.
