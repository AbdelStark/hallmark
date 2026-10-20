# 0005: immutable v1 model manifests

Date: 2026-10-20. Implements W03 / issue #4 under the autonomous backlog request.
This interprets the draft schema for implementation; RFC-0001 WIRE-REVIEW still
blocks enrollment. No existing experiment is migrated or reused as v1 evidence.

`ModelManifest` has the required `schema_id="hallmark/model/1"`. `FileRef` and
`GenerationConfig` are nested records, with exactly the listed fields and no
separate schema ID or hash domain. The complete manifest is hashed with
`H("model", value)`. File SHA-256 and artifact identities have distinct Python
types, both represented by exactly 32 bytes on the wire. Runtime, architecture,
tokenizer and template references bind identities; this schema does not validate
the referenced artifacts' semantics or enrollment.

All records are frozen; the file array becomes an immutable tuple. Integers are
strict, including the seed constrained to integer zero rather than `Literal[0]`,
which could equate booleans with integers. Encoding, hashing and explicit file
inspection revalidate nested instances because Pydantic's unchecked construction
and copy methods bypass normal validation. See
[Pydantic instance revalidation](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.revalidate_instances).

Paths are exact UTF-8 relative POSIX identifiers, bounded to 4096 bytes. Reject
empty components, `.` and `..`, absolute paths, backslashes, colons, ASCII control
characters and DEL. Do not normalize Unicode, case, separators or dot segments.
Files are in strictly increasing path order (UTF-8 byte order, equivalent to
Unicode scalar order). Reject duplicate paths and more than 4096 files. Identical
content under different paths is allowed; aliases of the same filesystem inode
are rejected during file inspection.

Schema parsing performs no filesystem access. `verify_model_files` is a separate,
explicit caller action with a trusted root and total byte budget. It uses
[descriptor-relative opens](https://docs.python.org/3/library/os.html#os.open),
opening each directory and final file with `O_NOFOLLOW`. It rejects symbolic and
hard links, nonregular files, size/hash mismatches, repeated inodes and detected
size/time/link-count changes during reading. Nonblocking opens prevent a FIFO
from hanging before the regular-file check. Unsupported safe-open platforms fail
closed; macOS and Linux are the supported file-inspection platforms. The root's
ancestors and host filesystem are trusted; this is not an OS sandbox.

Reads do not exceed the declared total byte budget. This helper has no wall-clock
deadline for a slow filesystem; the caller supplies process/time isolation where
required. It closes all descriptors after checking. A pass describes the opened
files at that check, not an immutable snapshot, a subsequent load, model execution,
hardware provenance or ZK. A loader must protect and validate the actual inputs
it uses (W23), rather than treating this result as a loading capability.

The [JSON schema snapshot](../schemas/model-manifest-v1.json) documents a JSON
projection with 64 hex characters per digest. CBOR uses byte strings. JSON Schema
cannot enforce path normalization, UTF-8 byte length, ordering, filesystem state
or all cross-field rules: executable validation remains required. JSON projection
helpers are for local tooling; the untrusted wire boundary is
`ModelManifest.decode`, with canonical/duplicate/version checking and typed,
sanitized errors. Direct Pydantic validation errors are not log-safe records.

The [fixed vector](../../fixtures/wire/model-manifest-v1.json) uses the harmless
three-byte file `abc`. Its CBOR was assembled with explicit headers and key order,
then compared with the model encoder and cbor2. Its hash was calculated from the
domain prefix and exact bytes. This is conformance evidence, not independent
implementation review or a cryptographic proof.
