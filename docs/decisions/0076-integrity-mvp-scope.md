# 0076: Complete the LLM integrity MVP

2026-10-25. Owner decision; issue #110. Implementation baseline:
`0d9c1f61a5ac36916efe10a8503d1719da85074f`.

The owner explicitly selected: “Finish the LLM integrity MVP without hardware or
hiding requirements.” This resolves the difference between the requested LLM
integrity demo and the original private, hardware-attested v1 roadmap.

## Accepted end state

A pinned real pretrained, disclosed quantized LLM produces a complete short
response. Actual specialized cryptographic proofs check that inference against
caller-owned expected inputs, model/parameter roots and coverage. Reproduction
has a simple Make command, retained failures and numeric evidence. The existing
synthetic classifier training/export/proof workflow remains available, including
composition over the same opened request. Public MIT source and direct proof
explanations remain required.

For this MVP, witness hiding and hardware attestation are not requirements.
Operational signer/setup custody, revocation infrastructure, production service
APIs, independent qualification and the original full private-v1 release are
future work. Their absence remains a limitation; it is not reclassified as a
passing security or provenance result. No `qualified_backend`, hardware, hiding
or safety-quality flag is changed.

## Acceptance audit

[The acceptance page](../MVP.md) maps these requirements to inspected evidence.
[The numeric audit](../../research/evidence/integrity-mvp-completion-2026-10-25.json)
checks all 207 current runtime sources, all 55 native verifier sources, all 20
sources of the freshly executed LLM proving pipeline, all eight downloaded model
files including the real checkpoint, and all 69 retained proof/statement/claim
files. It checks fresh proof-verifier results, the exact request join, signed
parameter authority, public MIT metadata and exact-source baseline CI.

The accepted proving code remains byte-identical to the fresh campaign. Current
composition/authorization was separately executed on its exact source. This is a
documentation/scope decision: no model, arithmetic, dataset, threshold, evaluator,
proof relation, wire format, runtime source or historical result changes. No new
proving campaign is needed to repeat unchanged computation.

## Original roadmap

The original SPEC, RFCs, work map, protocols and failed experiments stay intact.
Its 29 remaining open issues are future v1 work or dashboards for that work.
They remain open with their original acceptance criteria and are marked
`post-mvp`; none is closed as implemented by this decision. The hardware/private
v1 contract has not been completed or adopted.

Completion of this scoped research MVP does not claim arbitrary-prompt/model
support, floating-point equivalence, model quality, independent cryptographic
review, protected release or production readiness. The synthetic CNN still
blocks the ordinary France prompt; a valid computation proof is not policy
approval.
