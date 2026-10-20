# Overview

## Authority and precedence

This corpus specifies the proposed private v1 POC. It does not describe a shipped system. The [source PRD](../../research/source/product-requirements.txt) supplies goals G1–G5; the [hybrid design](../../research/source/hybrid-specification.txt) supplies the original interfaces and threats. The [ML packet](../../research/source/ml-engineering.txt) supplies candidate research directions, not current measurements. [Decision 0002](../decisions/0002-v1-specification-scope.md) records the derived scope.

Precedence: an accepted versioned RFC defines its v1 subsystem; these spec sections define cross-cutting requirements; [baseline SPEC](../SPEC.md) defines only the existing executable. Draft RFCs are concrete proposals awaiting owner review. The source packet is immutable historical evidence and does not override this corpus. A conflict blocks enrollment until a decision and conformance vectors resolve it.

## Thesis and users

A relying party should be able to distinguish “a measured serving path produced these bytes” from “these enrolled classifier programs returned these verdicts.” Both statements concern one interaction. A classifier pass is neither a safety certificate nor evidence of complete traffic coverage.

The first proposed user is an internal enterprise auditor checking English, single-turn prompt-injection screening on a private stand-in model. This is a design assumption, not validated demand. The requester's exact prompt and delivered response are committed; classifiers inspect only the prompt. Hidden system instructions are referenced by digest and excluded from classifier scope. Policy `inj.direct/1` identifies an owner-reviewed rubric for attempts to override prior instructions; approval is an admission gate, not implied by this name.

## v1 boundary

The POC includes one confidential serving instance with an attested accelerator, an enrolled open-weight stand-in treated as closed by the serving API, an authenticated local registry, and three public-weight classifier programs: deterministic byte rule, small byte-feature MLP, and one compact encoder. The byte-logistic baseline remains a comparison, not a substitute for these three kinds. The rule is a bounded policy subset; its limits must accompany the ML quality results.

The instance performs integer release gating before returning a response. Every released response schedules all three genuine proofs; a pending proof is never accepted as verified. C0 bundles carry separate evidence objects. B1 opens the transcript and independently recomputes classifier input; B2 hides content and explicitly trusts hardware for input binding. A separate verifier may accept B1 claim B while declining claim A.

v1 includes a negative corpus, a second implementation written from the spec, per-stage costs, a three-role local demonstration and two independently authorized reviewer reproductions. It includes no production rollout or public distribution.

Future work, excluded from v1 issues: B3 tokenization proofs, recursive composition, sampled coverage, cascades, hidden classifier weights, teacher training/distillation, broad multilingual policies, frontier-model proofs, multi-node serving, streaming, external service APIs and continuous campaigns. The [ML plan](../ML-PLAN.md) retains these as later research; this boundary does not delete them.

## Milestones and acceptance

| Milestone | Exit evidence |
|---|---|
| v0.2 | Owner-reviewed protocol, typed schemas, golden vectors, enrollment, data/resource admission proposal and working baseline gates |
| v0.3 | Qualified real proof adapters for rule, MLP and encoder; measured confidential serving path; frozen evaluation and reproducible cost records |
| v1.0 | Complete hybrid bundles, independent verifier agreement, all negative cases rejected, private release packet and authorized reviewer reproduction |

These milestones are plans, not dates or permission to spend. Closure requires evidence in the issue, not merely code merged. If authority or hardware is absent, the relevant issue remains blocked.

**INV-CLAIMS:** every result reports claim A and claim B separately, their accepted/rejected/not-accepted status, binding mode, assumptions and residuals. “Safe” is not an output state.

**INV-COMMON-INPUT:** every accepted component binds the same model/policy/interaction/transcript identities and complete classifier input.

**INV-NO-SUBSTITUTION:** mock proofs, stored hashes, replay and compiler import cannot satisfy genuine-proof or genuine-hardware gates.

**INV-QUALITY:** executed policy and classifier quality are separate reports; policy adoption requires prespecified quality/power criteria and owner review.

**INV-COMPLETE-V1:** all v1 requirements in [the work map](11-requirements.md) must pass; no smaller fixture can inherit the v1 label.

RISK: the encoder and hardware path may be infeasible under the eventual budget. Resolve through measured qualification and an explicit scope decision, retaining failures.
