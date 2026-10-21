# Optional backend experiments

## Boolean-wire cache

`boolean-wire-cache.patch` is a local research modification of Consensys gnark
v0.16.4, commit `e974abb44722dd201a7f1949baeabca0fef5866e`. Upstream gnark is
Copyright 2020-2025 Consensys Software Inc., licensed under
Apache-2.0; the retained [licence](GNARK-LICENSE) applies to the upstream material.
The patch marks its modified code. It adds no dependency and is not enabled by
this probe's `go.mod` or the Python package.

The reviewed original `frontend/cs/r1cs/builder.go` SHA-256 is
`d515546fb3442a38edf5487e6d5c0e52173687348408cb4a5ab5852dc9650e03`.
After patching it must be
`3cdd1a266ffba596d01b87a6bdcf51e141f92ae17d991bb9fe7f6e2149de01d4`.
The patch SHA-256 is
`5f70f965f4e4443ef32a01b5a2dc0163ae213d5dc86064fecc1f04fdcd52cb8c`.

Under an approved run plan, first run `go mod verify` with the admitted isolated
toolchain/cache. Copy the verified module to a fresh private directory, keep its
licence and inventory, and apply the patch there with `patch -p1`. Never modify
the original module cache. Copy this probe's `go.mod`/`go.sum` to a fresh matching
modfile pair; add a `replace github.com/consensys/gnark => ABSOLUTE_COPY` line.
Build using `-modfile=FRESH.mod -mod=readonly` and the documented offline environment.
Keep the original and patched module/source/binary identities separate.

Before any large run, build the same `cache_test.go` with upstream and patched
modules. Run `TestBooleanCache` and `TestCircuitFingerprints`, and compare all
seven `CIRCUIT` JSON records exactly, including serialized R1CS hashes and lengths.
Then execute fresh actual proof/negative-witness checks under a bounded protocol.
These checks do not establish general compiler correctness, independent security,
full-input proving or encoder qualification. See
[decision 0038](../../../../docs/decisions/0038-boolean-wire-cache-candidate.md).

## Bounded G1 batch conversion — component checks passed

`bounded-g1-batch.patch` modifies only `ecc/bls12-381/g1.go` in gnark-crypto
`v0.21.1-0.20260913224755-1409fe592052`. The upstream copyright is
2020–2026 Consensys Software Inc.; its Apache-2.0 licence has the same retained
bytes as [GNARK-LICENSE](GNARK-LICENSE). The patch marks its modified loop.

It replaces the full Jacobian output array with at most 4,096 Jacobian points
per existing parallel worker, converts each chunk and copies it into the final
ordered affine array. The scalar window, digit partition and curve operations
remain the same. Renaming the existing `min` cost variable avoids shadowing the
Go built-in. G2 is unchanged. Repeated batch inversion and temporary affine arrays
still cost work; maximum setup feasibility remains unmeasured.

| Pin | SHA-256 |
|---|---|
| Original `g1.go` | `22544597ca454517d5a4ae788a5349ae2e2ec72380e101bf1d37b4d0ffe50165` |
| Corrected candidate `g1.go` | `2c2368587355ffe6747a8fcf0d147180f74fd4b559efeccb428fbe0d2bb026ac` |
| Patch | `652609cafa8cc3bae8e88c00bbd5374ca3a6fdff4deb669fafab76b2786234dc` |
| `g1_batch_test.go` | `825a2f84b3383eeedf335e366944ba2c900936e25dcb40b7e91a81dd0a59aae1` |

Under a bounded run plan, copy the verified module to a fresh writable directory,
retain its full inventory/licence, apply with `patch -p1`, and verify the resulting
source hash. Keep the default module cache unchanged. Add an explicit
`replace github.com/consensys/gnark-crypto => ABSOLUTE_COPY` to a fresh modfile pair;
retain the separate gnark Boolean-cache replacement if that is the admitted build.
Neither the default modfile nor the HF bootstrap enables this candidate.

From the probe directory, use the frozen evaluator explicitly with both variants:

```text
go test -mod=readonly -modfile=BASELINE.mod -count=1 -v patches/g1_batch_test.go
go test -mod=readonly -modfile=CANDIDATE.mod -count=1 -v patches/g1_batch_test.go
```

Use the same host/thread configuration and compare every `G1CASE` record exactly.
The test also compares each point with separate scalar multiplication, rejects
mutated inputs, and includes generator/infinity bases, zero/one/minus-one scalars,
deterministic wider scalars and repeated values. Its final length is
`runtime.NumCPU()*4096+1`: `GOMAXPROCS` limits execution threads but does not change
this library's default partition count. An assertion checks that a worker actually
crosses a 4,096-point boundary. The shorter fixed lengths alone cannot ensure that.

The corrected patch now builds and passes all 16 baseline/candidate point cases,
including the actual per-worker boundary at 65,537 points on this host. All seven
serialized circuit fingerprints agree. Both builds pass the existing tiny cubic
setup/prove/verify unit fixture, changed-public-input rejection and trailing-byte
rejection for each artifact type. Its temporary keys/proofs are not retained.
The original `min` build failure remains in the
[preparation evidence](../../../evidence/w18-g1-candidate-preparation-2026-10-21.json).

The separate frozen `g1_alloc_test.go` measures one 262,145-point operation per
variant. Build it explicitly with the same two modfiles and run each binary with
`-test.run '^$' -test.bench '^BenchmarkG1Batch262145$' -test.benchtime 1x -test.benchmem`.
Compare its `G1ALLOCATION` output digests as well as resource receipts.

| One diagnostic sample | Baseline | Candidate |
|---|---:|---:|
| Allocated bytes per operation | 80,061,592 | 76,999,144 |
| Allocations per operation | 250 | 2,622 |
| Operation nanoseconds | 3,697,711,000 | 3,687,230,916 |
| Worker peak RSS bytes | 96,813,056 | 79,331,328 |

Ordered output digests agree. Allocation count increases despite fewer allocated
bytes and lower observed RSS. One sample per variant establishes neither a latency
distribution nor maximum setup feasibility. See the
[validation evidence](../../../evidence/w18-approved-validation-2026-10-21.json),
[decision 0042](../../../../docs/decisions/0042-bounded-g1-preparation.md) and
[approved validation increment](../../../../docs/decisions/0043-approved-local-validation-extension.md).
A fresh complete-input commitment proof/negative campaign and an explicit maximum
setup resource plan remain required. These component checks do not qualify W18.
