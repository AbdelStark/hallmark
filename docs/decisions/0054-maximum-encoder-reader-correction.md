# Correct the maximum encoder reader ceiling

Status: implementation correction under the owner's standing approval, 2026-10-21.
Scope: W18 / issue #19; preserve the frozen relation, fixtures, evaluator and prior
failure. This is a new experiment identity, not a successful retry of the old run.

The first maximum encoder HF job, `6ad8fd3a5275124786e29010`, executes candidate
`e7aab95921a8d9aaba7d569decddcac636d83416` after all 30 candidate checks pass.
PR #82 merges as `9e3e57ea112fbde4fd6d71bc8130270da13c3a08`; all 15 main jobs pass.
The cloud's small encoder setup, proof, fresh verification and changed verdict
checks pass. Maximum export takes 321.558022403 seconds and peaks at
76,479,299,584 bytes kernel RSS, with no budget or monitor failure. Its circuit
matches the independently retained Mac SHA-256
`7ac28b310c9727aef8c98c3d2a4944a6730d7696ddad40ef4aba1b31a6f5451a`.

The next worker exits 1 in 0.018125895 seconds, before decoding or setup. The
encoder passes a 48 GiB artifact allowance, but `readBounded` still rejects any
declared allowance above 24 GiB. The 5.15 GB circuit itself fits either file
limit. This is an inconsistent reader configuration, not an out-of-memory or
setup-time failure. The eight-byte proof preflight uses 2 GiB and did not exercise
the larger declaration. The previous mocked orchestration tests could not detect
this Go boundary mismatch. Retain the complete failed job before removing its
bucket; do not relabel its export as setup or proof success.

Reproduce the failure with real tiny compiled artifacts at the 48 GiB limit.
Raise only the shared reader's maximum permitted declaration to 48 GiB. Each
caller still supplies its own smaller limit: ordinary readers remain 256 MiB,
small encoder artifacts 2 GiB and maximum commitment artifacts 24 GiB. Preserve
regular-file, no-link, exact-consumption, changed-file and exclusive-output checks.
Exercise both the default and maximum declaration through actual tiny export,
reload, setup, proof and verification. Boundary tests accept exact declared caps
and reject 48 GiB plus one. These tests already run in hosted CI and the HF
bootstrap before expensive export. Reload the actual 5,153,016,221-byte maximum
circuit on the Mac with the corrected reader before another paid run.

Use `w18-encoder-reader-fix-1792606117695924000` for the correction. The native
fixture, maximum recipe, expected circuit, graph, dependency patches, controller,
bootstrap and case roster stay fixed. Record red/green logs, source/binary pins,
actual maximum reload and local/package/exact-head hosted checks. Only then
freeze one new sequential HF job with the resource limits from decision 0053.
This is a diagnosed source correction; the failed job is terminal and no provider
or controller automatically resubmits it.

The terminal provider duration is 525 seconds. At the retained rate, including
one extra billing minute, its conservative compute bound is USD 0.32. Carry the
prior USD 7.19 bound, this USD 0.32 failure, at most USD 10 new compute and a shared
USD 2 incremental storage reserve across the failed and corrected encoder attempts:
USD 19.51 within the unchanged USD 20 combined ceiling. These are conservative
bounds, not invoices. Refresh price and available storage before submission;
retain all failed output first and confirm its temporary bucket is absent. No
account top-up, private upload, collaborator, contact or ongoing scheduler is
introduced. Maximum proofs, setup lineage, independent verification, security/
hiding review, operational enrollment and model quality remain separate gates.
