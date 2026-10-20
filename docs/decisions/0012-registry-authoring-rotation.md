# 0012: Registry authoring, retained history and dual-authorized key transitions

Date: 2026-10-20. Status: implemented software contract, pending owner protocol
adoption and operational REGISTRY-ROOT approval. Implements W09 / #10. No prior
research result is reused as v1 evidence.

## Authoring and retirement

`hallmark.registry.sign_snapshot` signs an exact reviewed `RegistryBody` with
caller-supplied Ed25519 key objects. It generates, loads and exports no private
keys. Every signer must be authorized by the external `TrustPolicy`, distinct,
valid and sufficient for its threshold. Signatures are sorted by key ID.
The exact reviewed dependency remains cryptography 50.0.2, recorded in
[W08's dependency review](../../research/evidence/w08-dependency-review-2026-10-20.json).
The lock and dependency versions are unchanged.

`next_snapshot` and `validate_successor` require the next sequence, exact
predecessor digest and nondecreasing issuance time. Every previous `(kind,digest)`
entry must remain, including expired and retired entries. Its validity interval
and original review reference are immutable. `retired_at` can change from null
to a timestamp, or to an earlier timestamp, never to null or a later timestamp.
This makes revocation irreversible within a retained history. New identities
carry explicit review digests. These references do not prove that a review took
place or admit an artifact's quality; the owner must retain its source evidence.
Opaque artifact digests still require independent content resolution.

Signing by itself does not establish a valid successor or freshness. Committing
to the authoring history performs both checks. An expired snapshot is rejected;
expired entry intervals remain for historical receipt checks. Retirement at or
before verification time rejects use even for a historically valid receipt,
unchanged from decision 0010.

## Rotation

`RegistryTransition` is a strict frozen record with schema
`hallmark/registry-transition/1`. It binds complete old/new trust identities,
their sorted unique key IDs, `activation_sequence`, the prior registry digest,
a bounded reason identifier and a review digest. `SignedTransition` has schema
`hallmark/signed-transition/1` and separate old/new signature lists, each 1..16.

Both externally supplied policies must authorize their own threshold. Each side
signs `u32be(len(tag)) || tag || canonical_transition_body`, using respectively
`hallmark/v1/sign/registry-transition/old` and
`hallmark/v1/sign/registry-transition/new`. These are signature tags, not new
artifact hash domains. A shared key must authorize each role separately.
The transition exposes no independent hash identity or accepted flag.

Activation must be exactly the retained checkpoint's next sequence and
predecessor. The old trust minimum cannot exceed that checkpoint; the new
minimum must equal the activation sequence. The key set or its threshold must
change. The complete new policy digest binds other owner-reviewed changes, too;
changing an allowlist, limits, required claims or binding mode invalidates the
authorizations. A transition supplied with no external new policy cannot enroll
its own keys.

`enroll_transition` verifies both authorizations, the retained previous signed
snapshot and its identity, successor retention, the new snapshot's signatures
and current freshness. The previous snapshot can have expired; its independently
retained digest and signatures still authenticate the history. It accepts
exactly one activation. Further successors use normal enrollment under the new
policy; another rotation needs another independently supplied policy and transition.
One-sided, skipped, replayed and substituted transitions fail.

Emergency recovery after loss or compromise of an old threshold needs owner
re-enrollment from an independently retained checkpoint. There is no unsigned
replacement or emergency-bypass flag.

## Checkpoints and authoring history

`rotate_and_store` performs transition verification, checkpoint comparison and
update inside one existing SQLite write transaction. On its first successful
enrollment, an existing W08 checkpoint database also records the supplied external
trust digest in `trust_binding`. This lazy format extension and checkpoint update
commit together. Later enrollment requires that exact policy digest; rotation
requires the old digest and replaces it with the fully authorized new digest.
This prevents reusing a retired policy against the same checkpoint store.
Unrelated policy changes need owner re-enrollment in a new checkpoint store.
No trust is discovered from the database or bundle.

The first successful binding also changes the checkpoint's SQLite application ID
from `HMR1` to `HMR2` in that transaction. This implementation reads both formats;
older W08 readers reject `HMR2` instead of silently ignoring the trust binding.
An `HMR2` store with a missing binding fails closed. Preserve the original backup
before upgrading; reverting the package is not a valid rollback of trusted state.

`hallmark.registry_history` is a separate authoring database with a distinct
application ID. `create_history` exclusively creates it from an independently
pinned signed checkpoint. `append_history` compares the expected latest state,
checks complete successor content and trust continuity, and inserts one record.
It stores exact signed snapshots, their body/trust identities and any signed
transition. Earlier records are never overwritten or pruned. Duplicate sequence
or digest insertions fail. UPDATE/DELETE triggers reject accidental mutation;
readback verifies exact inserted bytes and transition retention before commit.
`read_snapshot` checks the body against a caller-retained state; `read_transition`
returns a record which still needs external-policy verification.

Both databases reuse the W08 owner-controlled local POSIX path checks and SQLite
transaction settings. No file is implicitly created by read/update. Stale writers,
concurrent locks, suppressed writes, statement/commit failures and process exit
before commit are tested. The prior checkpoint, its trust binding and prior
history survive the tested failures. History and relying-party checkpoints are
separate roles/stores, not a distributed transaction.

These are local integrity and crash-recovery checks, not physical power-loss
tests, global transparency or protection from a malicious OS account. Database
owners can remove triggers or restore whole-store backups. Keep independent
checkpoints and approved policy copies. Different relying parties can still be
shown different validly signed roots; compare same-sequence digests out of band.

## CLI, bounds and operational authority

`hallmark registry-check SNAPSHOT --trust TRUST --state STATE --now SECONDS`
reads canonical CBOR and an already provisioned checkpoint database. Optional
`--history` contains every successor after the checkpoint and before SNAPSHOT,
up to 1,024. Rotation instead requires `--old-trust`, `--transition` and
`--previous` together, with no intermediate history. It does not generate keys,
provision state, fetch files or install a new trust-policy file.

Inputs must be explicitly supplied regular, non-symlink local files. File opens
use no-follow/nonblocking flags and bounded reads; FIFOs, directories and
oversized inputs fail. Trust-policy input is capped at 64 KiB. Total encoded
snapshot/history bytes obey the caller's lower ceiling and hard 64 MiB limit.
Rotation counts the prior snapshot, transition and activation together and
honors the lower byte/depth caps of both policies. Existing per-record bounds
and enrollment's elapsed-time checks apply. No new worker/RSS enforcement is
claimed. Retained authoring history grows on disk; it has bounded record reads,
no automatic pruning and no background writer.

Success emits only schema `hallmark/registry-check/1`, registry/trust IDs,
sequence and check time, after commit. Errors use the existing sanitized finite
error contract and exits. This command checks registry enrollment, not receipts,
hardware, classifiers, proof execution or policy quality.

The committed fixture keys are explicit deterministic public test seeds. No
operational roots were created, enrolled or rotated. The owner must record key
custody and signature-library approval through the private REGISTRY-ROOT process
before operational enrollment; software completion does not supply that approval.
