# 0010: External registry enrollment and transactional checkpoints

Date: 2026-10-20. Status: implemented software contract, pending owner protocol
adoption and operational REGISTRY-ROOT approval. Implements W08 / #9. No existing
experiment, transcript, policy or model result is reused as v1 evidence.

## Decision

`hallmark.enrollment` implements the RFC-0002 records and actual Ed25519 signature
verification. W08 needs this verification to reject an unsigned history; W09
retains snapshot authoring, immutable retained history and dual-authorized key
transitions. There is no signing-key generation or operational authoring API here.

`RegistryBody` uses `hallmark/registry/1` and `H("registry", complete_body)`.
Signatures cover `u32be(len(tag)) || tag || canonical_body`, where
`tag = "hallmark/v1/sign/registry"`. `RegistrySignature` and `RegistryEntry` are
nested unversioned records. `SignedRegistry`, `TrustPolicy` and `RegistryState`
use `hallmark/signed-registry/1`, `hallmark/trust/1` and
`hallmark/registry-state/1`, including when nested. Trust identity hashes the
complete trust record. No new hash domain is introduced.

Signers must be distinct, externally authorized and individually valid, including
any extra signature beyond the threshold. Duplicate trust identities and a
threshold outside 1..key-count fail. A+B requires explicit hardware roots and
measurements; B2 additionally requires A+B. Empty B1/B hardware lists are allowed.
This checks the trust configuration, not hardware evidence.

`enroll(snapshot, trust, state, now, *, history=())` has no default trust, clock
or checkpoint. Its history contains every successor **after** the checkpoint
and **before** the final snapshot, in sequence order. A direct successor needs
no history; an equal-sequence snapshot must have the exact retained digest and
empty history. Each link and signature is verified. Histories cannot exceed
1,024 intermediate records. New owner provisioning is needed beyond that cap.

Intermediate snapshots may have expired at the current clock; their signatures
and links remain checked. All supplied issuance times must be nondecreasing and
not in the future. The final snapshot must reach the trust minimum, satisfy
`issued_at <= now < expires_at`, and have age no greater than `max_age_seconds`.
The retained checkpoint alone contains no prior issuance time or entries, so it
cannot establish first-link entry retention or time monotonicity against the
checkpoint body. W09's retained authoring history covers that separate obligation.

`Enrollment` is a frozen process-local result with no public constructor or
decoder. It is not a transferable credential; Python object access is not an
isolation boundary. Re-enroll for each verification clock. `admitted` contains
signed, nonretired identities: model/policy/backend identities intersect external
allowlists; measurements intersect the external measurement list; classifier
identities remain subject to resolution against the externally pinned Policy.
Enrollment is possible when only some allowlisted alternatives are present.
The full verifier must require **each** artifact actually used.

`require_entry(kind, digest, issued_at=...)` checks membership and
`valid_from <= receipt_issued_at < valid_until` at the enrollment clock.
Expired artifact validity does not erase historical validity. Retirement at or
before the enrollment clock excludes an identity even for an older receipt.
`RegistryEntry.validate_time` can report `ARTIFACT_RETIRED` separately; absence
from the result reports `TRUST_MISSING`. No enrollment result establishes a valid
receipt, classifier execution, hardware provenance, ZK proof or policy quality.

## Persistence

`hallmark.registry_store` uses standard-library SQLite transactions instead of a
handwritten temporary-file/rename protocol. `provision_state` exclusively creates
a 0600 database from an external `RegistryState`. It refuses existing files.
`read_state` and `enroll_and_store` never create missing databases. The database
has an application ID and exactly one bounded canonical state record.

The update acquires an immediate write transaction, compares the caller's
expected checkpoint, validates enrollment, writes and reads back the new record,
and commits before returning the result. A stale caller or concurrent writer
fails; busy retries are not implicit. Statement and commit failures roll back.
Rollback-journal mode and `synchronous=EXTRA` request
[SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) under its documented
filesystem and hardware assumptions.
Tests include update rejection, deferred-constraint commit failure, suppressed
updates and process exit before commit. These are not physical power-loss tests.

Use owner-controlled local POSIX storage with trustworthy locking and fsync.
Final-path links, hard links, nonregular files, wrong ownership and modes other
than 0600 are rejected. The parent directory and all ancestors are caller-trusted;
this is not an untrusted-path resolver. Do not put the database in a bundle,
network filesystem, shared writable directory or repository.
OS account compromise, malicious replacement by the owner, disk corruption and
rollback of the entire trusted storage are outside this local monotonicity claim.
Keep an independent checkpoint backup. Failed initialization may leave an
unusable file for inspection; it never overwrites a prior checkpoint.

## Dependencies and bounds

The [pre-install dependency review](../../research/evidence/w08-dependency-review-2026-10-20.json)
pins cryptography 50.0.2, cffi 2.1.1 and pycparser 3.11 with distribution hashes,
published licence metadata and primary security-review sources. Ed25519 uses
raw public keys and detached signatures. The fixtures use explicitly public,
deterministic test seeds, never operational roots. Upstream-library selection and
fixture verification are not owner approval for operational key custody.

Limits only lower 64 MiB total encoded registry/history bytes, 16 MiB per proof,
16 nesting levels, 60 seconds and a 2 GiB worker-memory ceiling. Enrollment checks
encoded bytes, nesting and elapsed time between bounded cryptographic operations.
It does not allocate a worker or enforce RSS/process termination; that remains
the full verifier's worker obligation. Signature checks never fetch a network
resource. The generic parser's item/byte limits still apply before enrollment.

Schemas and golden signed fixtures are in `docs/schemas/*registry*-v1.json`,
`docs/schemas/trust-v1.json` and `fixtures/wire/enrollment-v1.json`. Existing v0
hashes and APIs are unchanged. A local hash chain detects divergent roots only
when compared against retained checkpoints; it provides no global transparency
or protection against a registry giving different relying parties different views.
