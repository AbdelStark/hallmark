# 0018: Proposed admission terms and review binding

Date: 2026-10-20. Status: engineering proposal awaiting owner/relying-party review.
Scope: [W13](https://github.com/AbdelStark/hallmark/issues/14).
No scientific protocol is adopted and no prior experiment is reused.

The [concrete proposal](../../research/proposals/inj-direct-v1/README.md) names one
assay, seven comparisons and explicit holds. Its proposal schema is distinct from
`AdmissionProtocol`; incomplete or null terms cannot pass as an admitted protocol.

## Separate assay and deployed policy identities

An admission protocol must exist before training. The runtime `Policy` requires
final classifier identities, so it cannot also name an untrained assay without
a dependency cycle. `StudyPolicy` uses `hallmark/study-policy/1` in the existing
policy hash domain and binds `inj.direct/1`, English prompt scope, rubric byte hash
and a positive byte cap no greater than 32,768. The schema separates its identity
from the runtime `Policy`. Runtime enrollment remains a later, distinct review.

## Acyclic review

1. Freeze all protocol terms, including nested source and budget approval hashes.
2. Compute `H("protocol", ["hallmark/admission-terms/1", terms])`, excluding only
   the top-level `approval_ref`.
3. Prepare `AdmissionReview` naming those terms, owner, relying-party role,
   both approval documents and an exact bounded document inventory.
4. Set the final protocol's `approval_ref` to that review's identity.
5. The caller authenticates the reviewers and independently enrolls that identity.

Changing a term requires a new review; changing the top review reference changes
the final protocol identity but not the terms hash. Copying a pin from a supplied
dossier provides no authority. The verifier checks names, identities and bytes,
not signatures, review content, legal rights or statistical adequacy.

## Document semantics and bounds

`SourceApproval.revision` is the SHA-256 of a revision-manifest document, not
a Git commit ID. The document records the exact source revision and declared
inventory. `license_text`, source/budget approval references, rubric, split
manifest, evaluator and candidate code/config fields are SHA-256 hashes of exact
document bytes. Code/config documents must identify the complete implementation
and dependencies; a filename alone is insufficient review evidence. The final
protocol and study/review links use typed artifact identities.

Candidate base files are declared, sorted unique `FileRef`s. This check does not
fetch or inspect asset bytes. Import/runtime adapters must verify approved bytes
separately. Review evidence is sorted, unique and exact: at most 256 documents,
1 MiB each and 8 MiB total. All required references/hashes must be represented.
Private operational dossiers must be supplied through an authorized private
channel; fixture documents are harmless public markers.

Decimal strings are canonical rationals in [0,1], with at most 18 fractional
digits, no redundant zeros or exponent. FPR/alpha are strictly between 0 and 1,
TPR is positive, loss is below 1. Three distinct uint64 seeds and the seven-item
ordered roster are mandatory. Resource caps are positive except an explicitly
zero cost, stages fit within total wall time and verification is capped at 60 s.
Declarations do not allocate or enforce resources.

## Validation and migration

Fixed CBOR/JSON/schema vectors and admission-negative tests cover missing pins,
changed terms, role mismatches, incomplete evidence, invalid budgets, ambiguous
numbers and unsafe constructed records. `make check-admission` and both package
gates exercise the no-download marker fixture. The actual proposal is rejected as
an admitted protocol. The old conformance corpus and prior results are unchanged;
new admission vectors are separate component evidence.

This API does not authorize the legacy synthetic runner or implement data import,
training, hardware access or proof execution. A future runner must bind its actual
inputs to independently admitted terms and enforce the full resource envelope.
Owner review is required before this proposed contract is used for real research.
