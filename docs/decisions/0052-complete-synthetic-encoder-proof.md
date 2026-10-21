# 0052 — Complete synthetic encoder proof experiment

Date: 2026-10-21. W18 / issue #19. New bounded proof experiment, not qualification.

The native baseline in decision 0051 is merged as
`1f7294c31deed06beb5eb4a245a532143b9ec40e`. Its frozen fixture is
`8d0551ac2e9c9e2527004bc4a33392844963ffcb17b9589139448db3f068ee7d`.
Lower the same 39 nodes and 121 per-chunk tensor elements, including both
normalizations, into the existing pinned Groth16/BLS12-381 probe. Keep the native
runtime, constants, tokenizer and earlier proof fixtures unchanged.

The first circuit capacity is eight original content units, four two-token
chunks. It uses the native profile identity, whose declared maximum remains
32,768. This is a strict capacity subset: an eight-unit success cannot clear the
maximum-profile gate. A later maximum experiment needs a new circuit, setup and
measured resource plan; it cannot inherit these proof results.

Use shared instances of the already pinned gnark log-derivative lookup gadget
for embedding, exponential, reciprocal and normalization tables. The direct
fixed-graph lowering must match every frozen native tensor, including the pair
indices used by normalization. Right padding, masks, original unit order and
canonical CBOR must be constrained. All actual chunks contribute to the maximum;
unused circuit slots evaluate the empty chunk but must not change a negative
maximum. Empty input still contributes its one empty chunk.

Reuse the existing complete-input commitment relation with an explicit profile
pin, preserving its default synthetic profile and all seven prior circuit
fingerprints. The new relation exposes exactly the existing 100 public fields:
context, classifier, input digest, unit count, chunk count, offset int32 threshold
and Boolean verdict. The threshold comparison is strict for every int32 value.

Preserve RFC-0001's acyclic identity order. Compile a program-specific circuit
and generate its key before completing a classifier manifest. Do not bake the
completed classifier digest or its verification-key digest into that same
circuit. Classifier and context are public interaction binders; enrollment must
check the completed manifest's program, profiles, constants, threshold, key and
setup against trusted artifacts. A proof verifier must receive the expected full
public tuple independently of the proof. An arbitrary new proof naming another
classifier is not enrollment authorization. This experiment retains synthetic
backend/key/setup tags and supplies no operational enrollment or acceptance path.

The frozen small roster contains the eight native vectors, seven/eight-unit
capacity boundaries and five threshold cases (equality, adjacent integers and
both int32 extremes). Threshold variants have new complete classifier identities,
classifier-specific input salts and input commitments. They are conformance
counterexamples, not calibrated models or reuse of a statistical test set.
`build_gnark_encoder_fixture.py` checks the independently retained native fixture
hash and reproduces native/Decimal-oracle tensors before generating assignments.
Freeze this roster before the first proof.

Run the smallest Go solver check first, then real setup/proof/fresh verification.
Reject all 100 changed public fields, every private tensor element, altered
units/coverage/masks/encoding/padding, aliases and changed proof/key bytes.
Distinguish expected unsatisfied constraints from crashes, timeouts and resource
failures. Keep each failed attempt and its source/cost records. The exact limits
and protocol are in `runs/w18-complete-encoder-proof-1792601385038675000`.

Use the previously reviewed boolean-cache/parallel-Pedersen module candidate for
the measured circuit, with the default dependency build retained as a separate
regression comparison. Record module/source/binary hashes; do not substitute a
later source or evaluator into the frozen run. This is a Mac foreground campaign:
180 seconds preparation, 1,800 seconds small proving, four threads, one proof
worker, 8 GiB RSS and 8 GiB new artifacts, within the 128 GiB retained-checkout
limit. There is no cloud launch, new dependency, model download or spend.

Software test vectors, local setup and shared gnark verification cannot establish
hiding, an accepted ceremony, independent security review, learned model quality
or genuine hardware evidence. `qualified_backend` remains false. Maximum-profile
proofs, authenticated program/key enrollment and independent verification remain
separate requirements. Neither W18 nor W12 is closed by this small experiment.
