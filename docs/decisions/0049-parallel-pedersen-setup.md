# 0049 — Optional parallel Pedersen setup candidate

Date: 2026-10-21. W18 / issue #19.

The maximum commitment circuit has 22,366,059 private committed bases. The pinned
Pedersen setup computes each base's scalar multiple serially. This is a plausible
setup bottleneck, not a measured attribution: the active baseline's phase logs
are buffered until the controller exits. Keep that experiment unchanged.

The candidate patch
uses the dependency's existing `parallel.Execute` over disjoint output ranges,
with `runtime.GOMAXPROCS(0)` as its worker upper bound. Randomness, scalar, base
order, point arithmetic, key serialization and circuit relation stay fixed. Apply
it only to a separate copy of the pinned module. The published zero-context patch
applies with `patch -p1` from that copy; its reconstructed candidate hash was checked. The original source and candidate
SHA-256 are allowlisted; the bootstrap also verifies the complete module inventory.
An absent candidate keeps the previous execution path. Compile-only plans cannot
opt into this maximum-setup candidate.

The local evidence
records a protocol frozen before each phase. Sixteen sizes at one, two and four
workers produce identical complete setup bytes to the original serial function;
the bases remain unchanged. Empty outer slices also match. Both ordinary and
race-detector builds pass. This deterministic fixture uses disclosed randomness
and related bases and is explicitly insecure; it is only an implementation check.
The race detector does not establish general concurrency correctness.

The actual tiny cubic fixture and seven small circuit fingerprints pass before
a fresh 50-case small commitment campaign. Eight real proofs verify; 18 malformed
witnesses, all 33 public-field mutations, a field alias, changed proof and wrong
key reject. Setup circuit byte hashes match the frozen baseline. All eight proofs
replay under separately retained key/proof/native-input pins. A verifier built with
the original, unmodified dependency modules passes 43 further cases: eight valid
proofs, 33 public changes, the alias and altered proof. This shares the proof library's verifier
implementation and is not an independent verifier or security review.

The small roster takes 185.746 seconds and peaks at 1,246,986,240 bytes worker RSS.
This single diagnostic run is not an isolated or statistical speed comparison.
No maximum setup or proof has used this candidate at preparation time. The local
protocols reserve 300 seconds for equivalence/race checks, 420 for the proof
campaign and 60 for unmodified replay, at zero spend. Actual preparation and
campaign commands consume 236.841 seconds; retain their individual receipts.

Under standing approval in decision 0045, a maximum follow-up may proceed only
after reviewing the active baseline's terminal result and retaining its files.
Freeze a new experiment, source commit, complete module inventory and input
manifest. Keep the existing maximum circuit hash, native fixtures, proof/rejection
roster and worker limits. The candidate changes only setup execution. No failed
or incomplete prior result becomes a pass.

Use at most one further `cpu-performance` job, sequentially, after exact-source
CI and a fresh price/resource check. Retain decisions 0047/0048's 170 GB RSS,
150 GB sampled stop, 48-thread upper bound on 32 vCPU, 24 GiB/file, 96 GiB output,
6,600-second controller and separate 900-second retention window. Keep the
8,400-second provider and 9,000-second creation deadlines. Reserve at most USD
4.80 for new compute only if the actual prior charges plus temporary storage and
that reservation fit the unchanged USD 10 campaign ceiling. Check that retaining
all outputs fits 128 GiB locally. No simultaneous job, automatic retry or top-up.

Maximum acceptance still requires three real proofs, the complete frozen rejection
roster, and fresh Mac verification against separately retained inputs and keys.
An additional unmodified-dependency replay checks compatibility. Full encoder,
operational enrollment, accepted setup lineage, hiding, genuine hardware and
independent security evidence remain separate gates. No backend is selected.
