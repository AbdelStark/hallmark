# 0017: Structural specification coverage and explicit live audits

Date: 2026-10-20. Status: implemented engineering gate for W38 / #39.
This does not accept the draft protocol or change its arithmetic/evaluation semantics.

## Problem

The old documentation checker ignored fragments and `make check-spec` did not
exist. The tracker still called several merged items open and retained a superseded
private-visibility instruction. A passing file-link check could therefore conceal
missing requirements, broken navigation and stale implementation metadata.

## Decision

Extend the existing dependency-free Markdown checker for the repository's heading,
anchor and link forms. Add a single spec checker around the existing work map,
requirement table, RFCs and tracker. A reviewed coverage register assigns each spec
section and named invariant to concrete work IDs; no section is silently exempt.
The gate validates the fixed v1 work/RFC set, exact table metadata, acyclic
dependencies, RFC template and owned/dated open questions. Merged rows link their PR.
Historical source-text hashes are retained; frozen corpus and legacy result identities
are not regenerated.

Normal `make check-spec` is offline and part of `make check`. Package checks run
it from the extracted sdist. A separate `--live --output NEW_FILE` invocation reads
paginated GitHub issues with a 45-second timeout and compares the actual mapped
issues/trackers, including closed issues. It records selected metadata, body hashes,
response/source hashes and observation time. API failure is a failed audit;
existing output is never overwritten. It makes no issue writes and adds no CI secrets.

The [contributor guide](../../CONTRIBUTING.md) and [gate documentation](../SPEC-CHECK.md)
state the supported Markdown forms, actual API boundaries and required workflows.
The tracker now reflects the merged W09/W11/W31/W33/W37 delivery and the standing
public-visibility instruction. No package licence or research authorization changes.

## Validation and limits

[Recorded checks](../../research/evidence/w38-spec-traceability-2026-10-20.json)
include the baseline's accepted broken anchor and missing make target, isolated
missing-requirement/orphan/anchor mutations, graph/template/coverage drift,
live-metadata failures and audit timeout/overwrite behavior. The
[live observation](../../research/evidence/w38-live-issues-2026-10-20.json)
checks all 40 work issues and 10 RFC trackers. The [final parser regression and validation](../../research/evidence/w38-final-validation-2026-10-20.json)
eliminate nested-quantifier backtracking on a long unfinished link. The baseline
packet remains intact.

The gate proves structural agreement of the checked inputs. It cannot decide
whether a work item satisfies the prose, an issue closure is scientifically
justified, an owner approved an open question, or hardware/proofs are genuine.
The live audit is a dated observation; offline CI does not imply a fresh GitHub
read. Markdown forms outside the documented subset require an explicit checker
and fixture update. Final-commit hosted checks remain a separate delivery gate.
