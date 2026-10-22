# 0057: Compose fresh synthetic proofs with program enrollment

Status: research implementation under the owner's standing approval. Operational
adoption and reuse as backend qualification remain subject to owner review.

The legacy rule and MLP probes embed classifier IDs containing placeholder key
identities. Replacing those with an actual setup key changes the classifier ID
and hence the circuit and key again. The encoder probe already avoids this cycle
by leaving the classifier bytes as a public binder checked against an externally
enrolled program/key mapping.

Add explicit `rule-program-*` and `mlp-program-*` setup/prove/verify commands.
They constrain the same fixed program, input commitment, coverage, arithmetic,
threshold and public byte ranges. Only the complete classifier ID is enrolled
outside the circuit. Preserve the legacy commands and their circuit bytes.
A proof from these new relations is insufficient without that enrollment check.

The separate eight-byte research path checks exact circuit hashes, performs
fresh setup for all three programs, and pins their ordered program/key mapping
before proving. It then completes the classifier manifests using actual typed
key/setup/backend identities and derives the policy. Its verifier reconstructs
all public inputs from a caller-owned opening and request, resolves the externally
pinned enrollment, compares full classifier manifests and proof containers, and
checks all three proofs with the separate py-ecc arithmetic implementation.
The three input hashes differ because each classifier has its own salt/profile;
the transcript context is identical. The combined decision is exactly all-pass.

This is a new experiment identity. No old proof or result is relabeled as a new
enrollment result. New negative controls reject substituted requests/openings,
missing/extra/duplicate/reordered classifiers, altered public fields, manifests,
keys, proof bytes, and incorrect combined decisions. Fresh real proofs from
other requests must also fail composition. Original arithmetic-verifier
mutation checks remain required for each new key.

The fixed roster uses `okayxxxx`, `xxBADxxx`, and `xxxxAAzz`. The final case
scores exactly 2 in the MLP and rejects at its unchanged threshold of 2. Two
preflight controls (`AAxxxxxx`, `xxxxxxAA`) instead scored zero and passed;
retain those failed assertions and frozen protocol revisions. This is test
construction against known synthetic marker arithmetic, not data/threshold
selection or detector-quality evaluation.

The controller is a bounded foreground Mac experiment: 7,200 seconds, four
threads, one worker at a time, 8 GiB worker RSS and 4 GiB new artifacts. It adds
no dependency or cloud job. Private run outputs stay outside git. The encoder
still passes every input in its frozen reachable numeric classes. The response
is a synthetic string, with no inference provenance. Setup is local and trusted,
the separate verifier is unaudited, and this path supplies neither hardware
attestation, operational enrollment, backend qualification nor safety acceptance.
