# 0021 — Pinned source import and lineage-first splitting

Date: 2026-10-20. Scope: W14 / issue #15; local engineering under the
[approved study authority](0019-approved-study-scope.md).
No historical experiment, fixture label or result is reinterpreted.

## Decision

Implement `hallmark.data_admission` without downloads or optional dependencies.
The caller authenticates source approval, licence rights and review evidence,
then enrolls the exact `DataImportPlan.identity()` outside the supplied bundle.
An attacker supplying both a plan and its purported trusted pin controls this
starting point. Names, hashes and `review_kind="human"` cannot authenticate a
person, establish rights, or validate annotations.

Each approved source revision is the SHA-256 of its encoded `SourceManifest`,
not an upstream Git revision. That document retains the upstream revision,
licence identifier, policy, purpose, privacy classification, exact adapter-output
files, label mapping and review, annotation/adjudication evidence, transformation
recipe and data card. `SourceApproval` separately pins licence text, restrictions
and approval evidence. All referenced evidence bytes must be present; additional,
missing or altered documents/files reject.

The adapter output is strict `SourceRow` JSONL, preserving prompt/response strings,
globally unique record IDs, source labels, family, parents, shared history and a
difficult-negative flag. An approved adapter must explain any upstream conversion
in the pinned recipe and retain its original-file provenance. This importer
does not implement Hub/Parquet adapters or establish that those declarations
match an upstream dataset. Unknown labels, missing parents, parent cycles and
positive difficult-negative labels reject.

Each normalized `Record/1` has a lineage sidecar naming its source manifest/file,
one-based row number, exact original line hash including its terminator, parents,
history and transformation/label/annotation review pointers. Policy and rubric
are bound through the source manifest and plan. No text is trimmed, normalized
or discarded.

## Group and split recipe

Before splitting, take connected components of parent edges, shared history IDs,
identical prompts (even with different responses), and reviewed near candidates.
The candidate finder has one fixed, bounded rule: ASCII case folding and ASCII
whitespace folding on prompt bytes. Non-ASCII bytes remain unchanged. Candidate
clusters contain more than one distinct original prompt; exact copies are already
grouped. The reviewed digest binds the complete sorted candidate inventory,
encoded as compact sorted-key UTF-8 JSON with a final newline.
Every candidate is retained and grouped, including conflicting labels.

This is a conservative lexical check, not semantic duplicate detection. Reviewed
paraphrase/translation/semantic links must appear as parents or shared history
before import. Missing or untruthful lineage cannot be discovered by a hash check.
Broader contamination and label audits remain required before real evaluation.

The frozen [study design](../../research/proposals/inj-direct-v1/design.md) supplies
the split and representative recipe. A group ID is `g-` plus SHA-256 of its sorted
member-ID JSON array with a final newline. Within source/family strata, groups
sort by SHA-256 of `inj-direct-design/1|split|` plus group ID, then group ID.
Groups spanning sources or families use one mixed stratum. Integer boundaries
are `floor(3*n/5)` and `floor(4*n/5)` for train/calibration/test.
All three primary partitions must exist; small inventories reject rather than
rebalance. Representatives minimize SHA-256 of
`inj-direct-design/1|representative|` plus record ID, with ID as tie break.
Labels and model scores do not enter either assignment.

A declared held-out source/family moves its entire connected component to the
separate held-out test cohort. Cross-source members travel together; this does
not imply every member of that component is from an unseen source. The split
manifest exposes all sources, families and members so evaluation can report
that limitation. Held-out cohorts must not enter primary estimates.

## Artifact and storage boundary

`build_dataset` returns a typed corpus `DatasetManifest` and exact bytes for
`records.jsonl`, `lineage.jsonl` and `splits.json`. Enroll the resulting dataset
identity separately. `verify_dataset` checks that pin and every file, then
rebuilds from the pinned source plan: rehashing a cross-split descendant or changed
sidecar still fails. This is same-code reproduction, not independent verification.

`write_dataset` validates the output inventory and creates a fresh 0700 directory
with exclusive 0600 files. It never overwrites an existing directory. Each file
is synced; the manifest is linked into its final name only after all writes
succeed. Partial failures remain for diagnosis and require a new directory.
The caller must provide a trusted parent directory and use `verify_dataset`
before consumption. This writer is not an OS immutability mechanism, a defense
against concurrent parent-path replacement, or qualified power-loss recovery.

Limits: 64 sources, 64 files per source, 100,000 total rows, 128 MiB total raw
adapter bytes, 256 MiB total output, 256 evidence files of at most 1 MiB each
and 8 MiB combined. Prompt/response fields each allow at most 32,768 UTF-8 bytes;
the study may reduce the prompt bound. Limit failures never truncate records.
The existing baseline loader keeps its separate 8 MiB bound; larger imports
require downstream training integration before use.

## Fixture and remaining data-card gaps

The committed fixture contains 26 hand-authored marker rows, invented approval/
review documents and the repository's `LicenseRef-Proprietary` notice marker.
Its purpose is local software testing, its privacy class is synthetic, and
`fixture_only=true` prevents its review declarations entering a real import.
It has no real human label audit, consent claim, task-quality measurement,
representative sampling, semantic contamination study or external source rights.
Public/human mode tests also use invented documents and establish binding only.

No real dataset, checkpoint or private review is committed. Actual sources still
need reviewed rights, restrictions, privacy/consent, original labels and policy
mapping, adjudication and difficult-negative provenance, transformation and
generator records, source/temporal/family coverage, contamination limits and
independent group counts. A completed import does not satisfy final measurement
admission or authorize a quality claim.

## Validation

`tests/test_data_admission.py` checks exact pins/inventories, malformed input,
lineage and review mutations, independent graph reachability and split arithmetic,
label/order independence, held-out closure, output tampering and write failures.
Seven schema snapshots and the harmless fixture reproduce locally.
Both package gates run `scripts/check_data_import.py` against the installed wheel.
