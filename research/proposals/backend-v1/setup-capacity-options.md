# Maximum commitment setup: source bounds and next candidate

Status: maximum circuit exported and reloaded on the Mac, 2026-10-21.
Maximum setup and proof remain unexecuted; the prepared larger-memory fallback is
[decision 0046](../../../docs/decisions/0046-bounded-maximum-hf-proof.md), under the
standing approval in decision 0045.
The [numeric source review](../../evidence/w18-setup-capacity-2026-10-21.json)
pins every file and line range used below. Existing results keep their original
source identities. The approved 120-second local validation increment closes the
streamed-artifact gates and validates bounded G1 fixtures. It does not authorize
a maximum campaign. Those historical increments retain their original scope;
decisions 0045/0046 now authorize bounded continued execution without repeated
micro-budget approval.

## Established bounds

The two completed Linux compiles report 40,015,721 constraints. The pinned
Groth16 setup chooses the next power-of-two FFT domain: `N = 67,108,864`, with
26 stages. Its proving key retains `N - 1` points in `G1.Z`.

| Source-derived quantity | Bytes | Meaning |
|---|---:|---|
| Encoded Z vector, including its four-byte length | 3,221,225,428 | One part of the key alone exceeds the current 268,435,456-byte artifact cap |
| Two FFT twiddle tables and two coset tables | 8,589,936,192 | Default precomputation retained through assignment to the proving key |
| At least N G1 Jacobian results | 9,663,676,416 | Materialized before batch affine conversion |
| At least N G1 affine results | 6,442,450,944 | Live alongside those Jacobian results during conversion |
| Domain plus these two point arrays | 24,696,063,552 | At least 23 GiB of live slice backing storage in that stage |

The last row is not peak RSS or measured physical memory. It excludes the circuit,
scalar/digit arrays, boolean masks, extra points beyond N, G2 data, slice headers,
allocator overhead and garbage-collector overhead. Do not add the earlier compile
peak to this bound: their peaks and live object sets are not measured together.
The previous HF worker stopped at 26 billion sampled RSS bytes and its container
reported 29,999,996,928 bytes. There is no evidence that unchanged maximum setup
fits those limits. The unchanged 256 MiB file cap certainly cannot hold the key.

The arithmetic can be checked without allocating a domain or points:

```python
N, stages = 1 << 26, 26
twiddles = sum(1 + (1 << (stages - i - 1)) for i in range(stages))
assert twiddles == N - 1 + stages
domain_bytes = (2 * twiddles + 2 * N) * 32
live_backing_bytes = domain_bytes + N * (144 + 96)
assert live_backing_bytes == 23 * 1024**3 + 1600
assert 4 + 48 * (N - 1) == 3_221_225_428
```

## Candidate to prepare first

Bound the Jacobian temporaries inside the existing G1 scalar-multiplication
parallel loop to 4,096 points per chunk, converting them to affine and copying into the final
ordered affine array. Keep the existing scalar window choice, base table,
digit partition, input/output ordering and curve arithmetic. This targets the
at-least-nine-GiB temporary without changing the circuit or proof statement.
It adds more batch inversions; latency and total peak memory must be measured.
The final affine array, FFT precomputation and scalar/digit arrays still remain.

The pinned G2 implementation already converts each result directly to affine;
it does not allocate a full Jacobian result array. Do not apply a G1-shaped patch
there without evidence of a separate bottleneck. This differs from the initial
unverified idea of batching both groups at the setup call site.

Use an optional patch against a separately inventoried `gnark-crypto` copy.
Preserve the default module cache and existing gnark compiler-cache patch. The
candidate needs its own source/build/experiment identity. The
[patch and evaluators](../../probes/gnark/patches/README.md#bounded-g1-batch-conversion--component-checks-passed)
have exact source pins. The corrected candidate passes all 16 point cases, seven
serialized circuit fingerprints and the existing cubic proof/reader unit fixture.
The earlier shadowed-built-in build failure remains retained. The
[allocation diagnostic](../../evidence/w18-approved-validation-2026-10-21.json)
records one 262,145-point sample per variant: allocated bytes fall from 80,061,592
to 76,999,144, while allocation count rises from 250 to 2,622. Observed process
RSS is 96,813,056 / 79,331,328 bytes. These observations do not establish a latency
distribution or whole-setup memory; the final affine array and domain still exist.

## Acceptance before a new maximum attempt

1. Compare candidate and baseline affine coordinates and serialized points for
   deterministic public scalars, including zero, one, minus one and repeated values,
   with both the generator and infinity as bases. Use lengths 0, 1, 4,095, 4,096,
   4,097 and 8,193 to cross chunk boundaries and a short final chunk. Keep the
   worker count fixed. Also use `runtime.NumCPU()*4096+1` and assert that the actual
   partition includes a span longer than 4,096: the library partitions by CPU
   count, independently of `GOMAXPROCS`, so fixed lengths alone miss that boundary.
2. Reproduce the seven small circuit fingerprints (passed). Run fresh small
   commitment setups, proofs and invalid-input/key/proof cases. This gate passes in
   [two fresh small campaigns](../../evidence/w18-g1-small-proofs-2026-10-21.json),
   each with eight valid proofs, 18 invalid witnesses, all 33 public mutations,
   alias, altered proof and wrong key. Separately pinned fresh replay verifies all
   16 generated proofs. Keep old results and failures; maximum input is unproved.
3. Measure the allocation/latency tradeoff on the same bounded fixture (one
   diagnostic sample per variant retained). A passing point comparison or one
   helper measurement does not qualify the complete setup implementation.
4. Record maximum wire counts, artifact sizes and explicit per-file/aggregate
   storage limits. A larger file cap must follow a new bounded plan; streaming
   alone supplies no cap or memory authority.
5. Freeze the exact public-input manifest, host, deadlines, memory stop, logging,
   retention and cost cap before requesting or executing a further cloud run.
   The historical one-job allowance is consumed; decision 0046 records a new
   single-job envelope under standing approval. No retry follows automatically.

If that candidate cannot fit the approved host class, prepare a source-backed
larger-host option with explicit cost/authority terms. A host change cannot fix
the current artifact cap, supply independent setup/security review or qualify the
full encoder. Do not purchase capacity from this proposal.

## Measured maximum circuit and current fallback

The [artifact evidence](../../evidence/w18-maximum-artifacts-2026-10-21.json)
retains the exact circuit hash, 48,477,333 wires and one commitment over 22,366,059
private wires. The compressed-key upper bound with a one-MiB metadata allowance
is 16,027,358,074 bytes. The larger reader cap is 24 GiB for this profile only.
Scalar-capacity, minimum affine/digit arrays and precomputed FFT tables account
for at least 30,186,277,504 simultaneous backing bytes before the circuit and
other allocations. This is not a measured RSS lower bound: allocation liveness,
page residency and garbage collection affect RSS. A 186 GB HF L4 host gives a
bounded fallback without another arithmetic patch; the GPUs are unused. The
built-in `fft.WithoutPrecompute()` is a possible future candidate, not enabled
in these results or the prepared job.
