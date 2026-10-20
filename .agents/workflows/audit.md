# Audit a research claim

Read SPEC and EVALUATION. Resolve the exact claim and its evidence class: software replay, statistical evaluation, hardware attestation or cryptographic execution proof. Do not silently substitute one for another.

Check the externally enrolled identities, source/environment/data lineage, split/group isolation, calibration and test independence, exclusions, counts and uncertainty. Rerun the smallest test that could falsify the claim. Inspect changes to the evaluator and test data separately from candidate changes. Audit code/diffs and source records for confidential inputs before any proposed sharing.

For a baseline bundle, require the saved manifest hash, validate all artifacts, replay integer decisions and independently check a boundary calculation. Replay shares implementation with the generator; label this limitation. For a future proof, use a real verifier/key and mutate every public input, threshold, coverage and binding field. For hardware, require actual collateral/measurement/freshness validation. Missing evidence means unvalidated, not passed.

Write findings by consequence with exact paths/commands, smallest counterexample and concrete acceptance condition. Never repair an old run in place or report a successful mock as integration. Update STATE and LEDGER; park any outward review until separately approved.
