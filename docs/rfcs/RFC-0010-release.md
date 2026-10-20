# RFC-0010: Private reproducible delivery and review

- Status: Draft
- Authors: @AbdelStark (owner; engineering draft for review)
- Created: 2026-10-20
- Target milestone: v1.0

## Summary

Ship a private, versioned review packet with reproducible distribution, complete spec/issue traceability, actual validation receipts and an authorized three-role demonstration.

## Motivation

[PRD M0–M5](../../research/source/product-requirements.txt) require a statement frozen before implementation, measured adversarial evaluation and reproducible review. A green local test or polished demo cannot imply a deployed or secure product.

## Goals

- Trace every normative implementable requirement to a bounded issue and evidence.
- Validate core, optional training, packaging and documentation separately.
- Deliver a private packet that two authorized reviewers can reproduce.

## Non-Goals

- Public licensing/publishing, automatic releases, outreach, adding collaborators or automatic privileged integration jobs.

## Proposed Design

Use the [release/versioning policy](../spec/09-release-and-versioning.md). `ReleaseManifest={schema_id:"hallmark/release/1", version:Id, source_commit:Text, source_tree:Digest, lock:Digest, build_environment:Digest, distributions:List[FileRef], inventory:Digest, corpus:Digest, conformance:Digest, independent_result:Digest, hosted_checks:FileRef, limitations:FileRef, approval_ref:Digest}`. A release is an explicit owner action after all required evidence is available.

Core CI covers supported Python versions, strict typing, bounded offline tests, lock and docs checks. The train-extra job must execute training; a skip fails that job. The package gate uses an isolated install and checks required source docs plus code/type metadata. Pin the build backend exactly for reproducible distribution; record resolved platform dependency inventories, licences and hashes. Verify declared Python 3.14 compatibility or narrow metadata through an explicit compatibility decision.

`make check-spec` checks local file/anchor targets, exact RFC section template, unresolved questions with owner/date, and work-map/tracker coverage. It must reject a missing requirement or orphan issue entry. The tracker records live issue URLs, milestones, metadata and dependencies; closed requirements retain evidence links. CI jobs from PRs have no secrets, hardware privileges or artifact upload. Authorized integration runs are a distinct manual gate.

Prepare a three-role demonstration: provider creates a request/receipt; auditor checks A and B under its trust; user opens exact bytes. Demonstrate altered response, weaker classifier, changed threshold, replay and forged native pass rejection, then B1 verification with hardware roots declined. Terminal sessions are sufficient; no web dashboard is required. Use approved harmless inputs and a predeclared host budget. Every screen labels evidence strength and pending state.

Two reviewers, authorized individually before sharing, run the documented commands from a clean environment and record source/corpus/evidence identities and discrepancies. The packet includes raw stage costs, classifier limits, key/setup/platform assumptions and failures. If review or hosted CI is unavailable, keep the release blocked and report the exact dependency.

## Alternatives Considered

Publishing a public demo would simplify access but exceeds authority and licensing. A local-only checklist omits actual hosted delivery. Documentation without issue coverage leaves implementation gaps.

## Drawbacks

Hosted account limits and reviewer access can block release independently of code quality. Exact builds need a pinned environment; reproducibility across different platforms is not assumed.

## Migration / Rollout

Keep 0.1.0 research behavior intact. Land the spec on its own review branch, then file the complete work set and tracker on that branch. Implementation issues close only with their validation evidence. Tag/release v1 only after the owner approves the complete packet.

## Testing Strategy

Build/install from fresh directories, compare distribution inventories and hashes under a fixed build epoch/environment, and verify no runs/keys/private inputs enter archives. Delete a spec link/requirement in a temporary fixture to prove docs validation fails. Check train CI cannot pass on skip. Execute all demo cheats and record both reviewer results.

## Open Questions

- OPEN QUESTION RELEASE-REVIEW — @AbdelStark, resolution checkpoint 2026-11-09: confirm ownership/licence inventory, restore ability to run hosted CI if still blocked, and authorize two reviewers through W36–W40. No public licence or sharing permission is inferred.

## References

- [Contributor guide](../../CONTRIBUTING.md), [security policy](../../SECURITY.md), [release policy](../spec/09-release-and-versioning.md), [conformance](RFC-0009-conformance.md).
