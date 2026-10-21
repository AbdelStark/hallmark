# Check the synthetic encoder with separate pairing arithmetic

Status: bounded implementation research under the owner's standing approval,
2026-10-21. Scope: W18 / issue #19. This creates new verification evidence; prior
gnark replays remain shared-library checks and are not relabeled independent.

Both existing verifier builds use gnark. Implement the fixed synthetic encoder's
100-scalar, single-Pedersen-commitment verification equations in Python using
hash-locked py-ecc 8.0.0 arithmetic. Keep this optional research probe outside the
core package and its acceptance APIs. Review and retain the exact dependency
wheel licenses before installation. Admit only CPython 3.12 Mac arm64 and Linux
x86_64 wheels; preserve the lock and notices. No dependency is vendored.

The verifier accepts a caller-owned key pin and public scalars. It checks exact
key/proof sizes and layout, canonical compressed points, subgroup membership and
canonical scalars. Check the Pedersen equation separately from the Groth16
equation; multiplying them together would allow cancellation. Hash the exact
uncompressed commitment encoding with the protocol's field-hash domain. Reject
other commitment layouts. A key included by the prover is not an enrollment.

Freeze the existing 15 small encoder proofs, key and independently recomputed
native public assignments before testing. Exercise all 100 public mutations,
field aliases/types/counts, malformed encodings, points outside the subgroup,
commitment and knowledge-proof changes, and both pinned-key and algebraic-key
changes. Include a valid joint negation of proof A and B: their pairing is
unchanged, so valid proofs are not byte-unique. Do not claim every byte change
must invalidate a proof. Preserve failures and all earlier source versions.

Use a bounded, isolated Mac worker with no network, forks or outside-file reads.
The initial 147-case run has 15 original valid proofs, one valid algebraic
transformation, 109 algebraic rejections and 22 malformed-input rejections.
Record raw costs and pins before any performance prose. No latency distribution
or comparison with the concurrent cloud run is claimed.

The hosted proof-artifact job will generate a fresh eight-byte capacity proof
using the pinned Go toolchain and original dependencies, enroll its key and
expected public vector before proving, then run the separate checker. Bound
fixture generation to 600 seconds, two compute threads, 2 GiB worker RSS and
512 MiB retained output; bound the Python checker to 300 seconds and 2 GiB RSS.
The job ceiling becomes 15 minutes. Network-restricted workers receive fixed
environments without inherited credentials. No cloud job or private upload is
introduced. Local fixture validation uses the same envelope in fresh directories.

This supplies a second implementation and arithmetic library, not independent
human cryptographic review. The library is experimental and unaudited. Accepted
setup lineage, authenticated program/key enrollment, hiding/security review,
trained-model quality and hardware attestation remain absent. The active maximum
encoder job, graph, native inputs, controller and resource limits are unchanged.
All qualification flags remain false; W18 and W12 remain open.
