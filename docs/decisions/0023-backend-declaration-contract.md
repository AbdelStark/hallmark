# 0023 — Backend declarations and external file pins

Date: 2026-10-20. Scope: W18 / issue #19; additive contracts after
the local probes. Historical results are unchanged.

Implement the exact RFC-0005 `BackendQualification` record in
`hallmark.backend`, with identity `H("backend", record)`. The name identifies
the specified record, not a verified outcome. Decoding it, including a declared
`zero_knowledge=true`, cannot establish qualification or proof validity.
No candidate is selected by this change.

The record binds source, build, proof system, setup, verifier, licence/security
reviews, conformance and costs; sorted dependency file references; sorted
supported program identities; and exact security-parameter and public-input-layout
files. Those two files must be nonempty and at most 1 MiB each, with distinct
paths outside the dependency list. There are at most 1,024 dependencies and
4,096 supported programs; both lists must be nonempty and unique.
No identity, Boolean or list default is supplied.

`validate_backend_files` accepts a caller-enrolled backend identity, an explicit
required program set, a hiding-claim requirement, a complete in-memory file map
and an aggregate byte limit. The caller authenticates that identity outside the
record. A changed record with rehashed files still fails against the old pin.
Required programs must be covered; a false hiding declaration cannot satisfy a
true requirement. All declared file sizes and actual byte totals must fit the
caller budget before file contents are hashed. Missing, extra, changed or
non-byte files fail. This function returns `None`, not an acceptance result.

Source/build/setup/review/conformance/cost references are opaque typed
identities. This function binds them but does not resolve or authenticate their
contents. Security parameters and layout are also opaque file bytes here;
the future qualification runner must validate their semantics and graph/key
relationship. No executable is loaded, process launched, key enrolled, proof
verified, review approved or hiding/security property established.
Filesystem isolation is not inferred from an in-memory dictionary.

The synthetic fixture contains marker identities, an explicitly unreviewed
security document and the existing 100-field layout. It declares no hiding
qualification. The checker intentionally demonstrates that a separately pinned
true declaration can pass structural binding without proving that the declaration
is true. The remaining W18 runner and whole-graph gates must supply the actual
evidence before any operational selection.

Tests cover exact wire/JSON/schema reproduction, independent domain hashing,
every identity/file field, strict types, list ordering and bounds, bypassed
construction, stale external pins, program coverage, claimed hiding requirements,
rehashed substitutions, exact inventories and budget checks before file hashing.
The distribution gate exercises the same fixture through the installed wheel.
