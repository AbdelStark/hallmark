# 0022 — Local proof probes before backend selection

Date: 2026-10-20. Scope: W18 / issue #19, under the
[approved local study authority](0019-approved-study-scope.md).
This adds research probes, not an enrolled backend or a production proof API.
Historical software results retain their original meaning.

## Candidate and setup

Use the reviewed gnark v0.16.4 source and pinned Go 1.26.8 toolchain for a
local Groth16/BLS12-381 experiment. The
[source review](../../research/proposals/backend-v1/candidate-review.md) and
[dependency inventory](../../research/evidence/w18-backend-dependencies-2026-10-20.json)
record source, licence, module and toolchain identities. EZKL remains on hold
because the inspected candidate does not establish an applicable licence grant.
This does not establish that no suitable grant could exist elsewhere.

An isolated source build leaves the system toolchain unchanged. The selected
14-module compilation closure is pinned; an attempted full upstream module
inventory failed on the unavailable Solidity checker and remains failed.
Neither the optional Solidity tool nor GPU/recursion paths were executed.

Every experiment creates a real circuit-specific random setup, never a dummy
setup. The controller snapshots and pins the resulting verifier key before
running the prover. That is an experimental key boundary, not independent
operational enrollment, a trusted ceremony or proof of secret erasure.
The same pinned gnark library performs proving and fresh-process verification.
There is no independently implemented verifier.

## Relations

The installation probe constrains private uint8 `x` and public uint32 `y` to
`y = x³ + x + 5`. It checks actual proof verification, field aliases, changed
inputs/proof/key, invalid witnesses and repeated randomized proofs. Its small
public output can reveal `x`; it is not a privacy demonstration.

The separate rule probe implements the frozen native marker fixture: `BAD`,
0..8 UTF-8 bytes, four-byte chunks, threshold one, and strict pass-on-less-than.
It constrains every possible marker start, zero padding and the exact number of
chunks, including one empty chunk. This complete-input Boolean OR is equivalent
to the native maximum of chunk scores for this fixed rule. It does not expose or
prove an arbitrary integer DAG or a general rule program.

The circuit constructs the exact canonical encoding of
`H("input", [derived_salt, profile, count, byte_list])`. Byte values below 24
and values from 24 through 255 use their distinct canonical CBOR forms. It
checks the SHA-256 digest against the public input. The private salt is already
derived; an independent B1 caller must reconstruct the expected digest from its
opening and selected classifier. The circuit does not prove salt derivation,
UTF-8 validity or a transcript opening from context alone.

All 100 `ProofInputs` fields use the existing layout: three byte-constrained
digests, bounded counts, offset-encoded int32 threshold, Boolean verdict.
The classifier identity and input profile are fixed to the synthetic fixture.
Its backend/key/setup tags remain synthetic and do not match operational
enrollment. Context is a public binder; the fixture uses a harmless fixed context.
Even a passing proof cannot enter the production receipt-verification path.

The rule path adds the backend's SHA-256, byte lookup, range-check and commitment
gadgets. Their exact composition is not independently reviewed. Upstream's
integer-gadget warning, estimated 126-bit curve security and side-channel
limitations remain explicit. Randomized proof output does not establish the
whole application's hiding claim.

## Execution boundary

Both runners require macOS arm64 and caller-pinned binary bytes. Each case gets
a fresh private directory, fixed credential-free environment, expected file
inventory and a sandbox denying network and process forks. Reads outside the
case are restricted to the binary and OS runtime paths, including Apple's
`dyld-support.sb`. Inputs are copied before worker execution. The controller
rejects missing, extra, linked, oversized or changed artifacts.

Wall timeout kills the worker's process group and waits for termination. OS
fixtures test assigned-file access, external-file denial, loopback network
denial with a positive control, omitted inherited variables, denied forks and
timeout. These are tests of this platform profile, not a general hostile-code
containment certification. The caller must own the parent directory.

CPU limits are requested with `setrlimit`, but the first rule experiment
measured more CPU time than requested. Subsequent runners reject measured CPU
overages explicitly. Go's memory limit is soft; RSS and aggregate artifact
limits are checked after a case. Per-file and wall controls do not constitute a
hard aggregate memory/storage quota. The amended rule experiment records
120 seconds per case, 120 measured CPU seconds, four threads, 16 GiB observed
RSS maximum, 256 MiB per file, 4 GiB output and 30 minutes total. These fit the
owner's local envelope; no HF token, GPU job, private data or paid service is used.

The first rule source incorrectly encoded the domain length as 16 instead of
17. Its real prover rejected the empty-input vector. The failed source hashes,
setup, costs and failure survive under their original identity. The corrected
candidate computes the tag length and starts a new experiment. A failed
candidate never inherits a subsequent candidate's result.

## Remaining gate

These optional maintainer scripts do not implement `hallmark qualify` or the
`BackendQualification` artifact, and never set `qualified_backend` true.
W18 remains open for the bounded MLP, encoder operator block, complete admitted
encoder at required lengths, full resource measurements, setup/security review
and externally enrolled graph/key identities. W19–W21 cannot infer their
qualification from an installation or marker proof. Public-source selection
and local implementation remain authorized; these missing results are not a
request for renewed permission.
