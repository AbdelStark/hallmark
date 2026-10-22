# Changelog

## Unreleased

Add `make e2e` to prepare pinned dependencies and run the frozen Mac training,
export, proof and separate-verification workflow in a fresh retained directory.
Fail on incomplete results or changed exports; retain stage logs and failures.
Explain the exact proof statement, caller trust and distinction between a valid
proof and a passing classifier verdict. Models and proof semantics are unchanged.

Document the end-to-end synthetic rule/MLP/CNN proof demo, its pinned Mac setup,
separate verifier, expected outputs and measured limits. Add a documentation index
and model/data/results guide; distinguish current proof evidence from historical
baseline status. Adopt the MIT licence at the owner's explicit request and update package metadata
and current licence guidance. Runtime, model and evaluator semantics are unchanged.

Add an opt-in, pinned gnark Boolean-wire cache experiment with original/patched
circuit-byte comparisons, cache boundary tests and separate proof/cost evidence.
Keep the upstream dependency default and full-graph qualification gates unchanged.

Constrain commitment coverage with exact Boolean prefixes and retain malformed
mask prover attempts. Preserve native memory-sampler error codes so normal child
teardown does not become a false monitor failure. Full-input feasibility and
backend qualification remain separate gates.

Stop optional proof workers using live macOS RSS samples with conservative
headroom, preserve cutoff/failure costs and handle child-exit signal races.
Sampling and post-exit checks do not provide a hard memory quota.

Add an optional complete-input commitment scaling probe with canonical indexed
CBOR packing, small real proofs and bounded maximum-size compilation. Keep
proof results and resource failures distinct; no backend
or encoder qualification follows.

Add `hallmark qualify` with an externally pinned protocol, safe input snapshots
and a shared deadline/storage budget across the existing real-proof probes. Keep
standalone commands compatible. Passing available stages reports incomplete with
exit 3; full-encoder and independent qualification evidence remain unavailable.

Add the RFC-0005 backend declaration, caller-enrolled file/program/hiding-claim
checks, a synthetic schema/vector and installed-package checks. These bind
declarations without executing or selecting a backend. Separate local proof
probes retain genuine small-circuit results, failures and measured costs.
Extend those probes with an exhaustive fixed integer attention/feed-forward
block, including masked lookup/normalization, residuals and signed pooling.
This remains operator-block evidence, not complete encoder qualification.

Add caller-pinned group evaluation reports with fixed slices, all training seeds,
10,000 paired root-group resamples and separate float/integer drift. Preserve
unavailable members, null denominators and whole-group exclusions. A core-only
command consumes existing scores; descriptive reports never claim task quality.

Add exact-text character n-grams, fixed controls and five grouped train-internal
selection rotations. Retain every convergence/unsupported-input failure, then
calibrate and evaluate separately pinned native models with overlap rejection.
Execute the pinned complete-input guard and synthetic comparison command;
confirmatory real-data quality remains unvalidated.

Add train-only record-level byte MLP fitting, externally pinned optimizer resume
and explicit integer export. Check three authored-marker seeds, full 32,768-byte
inputs, numerical gradients and installed core/train paths. Preserve the historical
logistic baseline and its negative results; real-data validation remains separate.

Add caller-pinned source import, raw-row lineage sidecars and deterministic
grouped splits. Preserve contrastive pairs, bind review/rights documents and
reject rehashed leakage mutations. Ship synthetic fixtures, seven schemas and
installed-package checks; real data and task-quality review remain unestablished.

Execute bounded literal byte rules over complete prompts, carrying suffix state
across chunks and checking exact program/profile/provenance identities. Add
complete-input oracle tests, fixed vectors, schemas and installed-wheel checks.
Threshold equality blocks; fixtures make no policy-quality or proof claim.

Record the owner's approved prototype study, delegated evaluation/public source
selection and bounded local/HF research authority. Freeze conditional power and
quality criteria and prepare hardware/reviewer options. Actual source and
measurement dossier holds remain explicit.

Prepare the single-policy admission proposal with explicit source, quality and
resource holds. Add strict study/protocol/review records, caller-pinned document
checks, fixed marker vectors and installed-package validation. The proposal and
fixture initially authorized no asset access or measurement; the subsequent
scope approval is recorded above.

Add `make check-spec` for local anchors, RFC ownership/template checks, exact
work-map/tracker agreement and section/invariant coverage. Add an explicit
read-only live issue audit with immutable results. Run the offline gate in CI
and from the sdist; update contributor, API, security and release guidance.

Pin the full build dependency set, compare repeated wheel/sdist bytes and rebuild
the wheel from its source archive. Add exact source/archive/dependency inventories,
credential-pattern and archive safety checks, and installed core/train contracts.
Run both Python matrices on Linux and macOS. Clarify public repository visibility
while retaining unpublished packages and `LicenseRef-Proprietary`.

Add bounded private POSIX event storage, random run IDs, strict event/attempt
schemas and explicit single-retry retention. Check durable completion separately
from stage completion, reject unsafe or tampered files and suppress external
exception chains. Preserve legacy run artifacts and omit hosted telemetry.

Add bounded native byte-count MLP execution, explicit weight/program exports,
exact ties-to-even rescaling and private per-layer traces. Reject int32 partial-sum
overflow, conflicting file paths and over-budget inputs without truncation.
Ship fixed numerical vectors, schema snapshots and installed-wheel checks.

Add a pinned conformance corpus, three schemas and exact component-result
comparison. Include all original cheat obligations and retain unavailable real
evidence explicitly. Run software scope and wrong-expectation self-tests in
`make check-conformance`, the main gate and isolated installed-package checks.

Add registry snapshot signing, complete retained history, irreversible retirement,
dual-authorized key transitions and the offline `registry-check` CLI. Persist the
external trust digest with checkpoint updates; reject retired policy reuse.
Ship public-key fixtures and keep operational key custody separately gated.

Add bounded offline bundle, private response-envelope, collection-status and
reported-result contracts. Check exact embedded files, ordered proof declarations,
caller limits and claim consistency; keep openings separate from bundles. Publish
schema snapshots and structural vectors without an evidence-verification path.

Add external registry trust, Ed25519 threshold verification, complete linked
history checks and transactional SQLite checkpoints. Pin the reviewed signature
dependency, publish schemas/signed vectors and document separate owner provisioning.
Operational roots remain a separate owner gate.

Add v1 receipt, epoch and proof-container schemas with exact 100-field public-input
packing, offset-encoded signed thresholds, declared-reference/time checks and bounded
opaque payloads. Publish fixed vectors and schema snapshots without a verification stub.

Add v1 transcript openings, caller-bound context and salted complete-input hashes.
Reconstruct all prompt bytes locally; require explicit independent token units
and vocabulary bounds for encoders. Publish schema/preimage vectors and a separate
JavaScript checker. Preserve legacy transcript hashes unchanged.

Add v1 all-pass policy, request and caller-expectation contracts with schema
snapshots and fixed vectors. Check resolved rule/MLP/encoder order, model/policy
identities, explicit continuity and UTF-8 byte limits. No policy admission,
nonce consumption or evidence verification is supplied.

Add v1 classifier/input/arithmetic contracts, typed operator parameter files,
schema snapshots and fixed identity vectors. Validate graph topology and,
against supplied hashed parameters, shapes, mask/index bounds and exact
fixed-point range envelopes. Preserve the existing model-manifest bytes while
sharing its checked serializer. No classifier execution or backend qualification
is supplied.

Add immutable v1 model, file-reference and greedy generation contracts, a fixed
CBOR/hash vector and JSON schema snapshot. Bind all execution-relevant fields in
the model identity. Explicit rooted file checks reject links, nonregular files,
duplicate filesystem aliases and mismatches within a caller's byte budget.
No model loading, hardware evidence or enrollment is supplied.

Require actual training-test execution in the train CI job; skips and incomplete
execution now fail `make check-train`. Check core/package and training separately
on CPython 3.12, 3.13 and 3.14. Keep CI read-only without privileged integration
hosts, secrets or artifact uploads.

Replace raw CLI failure text with versioned, sanitized error JSON. Preserve
input/argument exit 2; execution/storage/resource failures now exit 3.
Unexpected failures receive local random diagnostic IDs. Add the finite error
taxonomy and stage ordering without modifying historical run artifacts.

Add a separate bounded v1 CBOR value codec and 22 domain-separated identities,
with canonicality, type, Unicode and resource-limit rejection. Preserve all legacy
research hashes. Artifact schemas, enrollment and cryptographic verification remain
separate implementation gates.

Proposed private v1 specification: canonical index, twelve specification sections, ten RFCs and a filed implementation backlog with dependency tracker. Preserve existing runtime/evaluation semantics and historical results. Include the corpus and tracker in source distributions; no new hardware, proof or classifier-quality capability is claimed.

## 0.1.0, 2026-10-20

Private research initialization: hybrid technical specification, evaluation/data/ML research plans, bounded agent workflows, strict data/model/run contracts, synthetic marker fixture, optional trained linear baseline, exact integer inference/calibration, uncertainty reports, caller-pinned replay, conformance and tamper tests, locked packaging and CI. TEE evidence, ZK proofs, real safety evaluation and encoder training are not implemented.
