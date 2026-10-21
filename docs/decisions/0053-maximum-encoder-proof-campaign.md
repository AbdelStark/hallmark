# 0053 — Maximum encoder capacity and bounded proof campaign

Date: 2026-10-21. W18 / issue #19. Standing owner approval; new experiment.

PR #81's complete synthetic encoder passes its eight-byte proof campaign. All
30 candidate checks and all 15 merged-main jobs pass at
`ace56348a609d2d8f00b0520abd05e0f1e72f987`. The unchanged graph now also exports
and reloads on the Mac at its declared 32,768-byte maximum. The new capacity
protocol was frozen before execution in
`runs/w18-encoder-capacity-1792603242840959000`; no setup/proof ran at maximum.

Exports at 8, 32 and 256 bytes pass first. The eight-byte circuit reproduces the
earlier proof circuit exactly. The maximum artifact has 110,432,265 constraints,
111,821,440 internal variables, 2,211,885 private variables, 101 public variables
including the constant, and 26,434,895 private committed variables. Its 5,153,016,221
bytes hash to `7ac28b310c9727aef8c98c3d2a4944a6730d7696ddad40ef4aba1b31a6f5451a`.
Export takes 276.780 seconds and peaks at 20,233,928,704 bytes RSS. Fresh reload
matches every count and byte hash in 6.085 seconds, peaking at 17,143,889,920 bytes.
The 1 GiB Go soft-memory target, four threads, 32 GiB RSS ceiling, 28 GiB sampled
stop, 600-second maximum export and 300-second reload limits stay frozen. These
are diagnostic observations; lightweight checkout preparation overlapped the
last part of export, with no other research worker.

The existing source-bound formulas reproduce the earlier commitment analysis
before applying the new counts. They give 64,198,195,232 bytes of simultaneous
backing allocations and a 35,308,458,964-byte compressed proving-key upper bound
including a 1 MiB metadata allowance. These are source-derived allocation/file
bounds, not observed RSS or exact key size; scalar capacity includes unused pages
and other live allocations are excluded. They justify using the already approved
larger-memory fallback rather than attempting setup under the Mac's 32 GiB RSS
envelope. The existing 24 GiB artifact-reader cap is insufficient for the key bound.

Hypothesis: the same frozen encoder can produce real proofs for empty, 32,767-
and 32,768-byte inputs within a bounded larger-memory campaign. Keep graph,
constants, profiles, tokenizer, threshold, public layout, dependency revisions
and compiler/G1/Pedersen patches fixed. Independently enroll the maximum circuit
hash above. Freeze native/Decimal-oracle assignments and rejection cases before
any cloud proof. All text is owner-authored synthetic fixture data; no private
transcript, checkpoint or new model is uploaded.

Extend only the research maximum controller, its explicit Linux resource bounds,
encoder artifact cap and the HF bootstrap's exact source inventory. The original
commitment mode retains its previous limits and roster. The maximum encoder alone
allows 48 GiB artifacts. All file-type, link, pin, exact-consumption, CPU, wall-time,
memory-monitor and failure-retention checks remain. No core acceptance API or
backend qualification flag changes. Prepare offline failure tests and a small
real proof before the paid run; publish and check the exact source commit first.

The owner has repeatedly authorized continuing and finishing without repeated
micro-budget approvals. The following are agent-selected bounds under that
standing authority, not numeric quotations from the owner. Preserve all earlier
budgets/results. One sequential `cpu-performance` job uses the advertised 32-vCPU,
256-GB RAM, 1,024-GB scratch host. Its current API price is USD 0.031667/minute;
refresh it before submission. The pinned implementation keeps its earlier
48-thread upper bound, explicitly exceeding the physical vCPU count without a
scaling claim. The [provider pricing](https://huggingface.co/docs/hub/main/en/jobs-pricing)
and retained hardware API response support the resource choice.

Use 230 GB RSS with a 210 GB sampled stop, 48 GiB per file and 128 GiB stopped-worker
output. Export gets 900 seconds; setup and the shared-key batch each get 6,600;
the whole controller gets 15,000. Reserve 1,800 seconds for retention, a
17,400-second provider timeout and an 18,000-second creation deadline. Limit new
compute to USD 10. Preserve the earlier USD 7.19 conservative bound and reserve
another USD 2 for temporary storage, within a new USD 20 combined ceiling. These
are limits and estimates, not invoices. Increase the retained local ceiling only
for this campaign to 256 GiB after checking actual free disk; retain the previous
128 GiB ceiling as historical. No account top-up or automatic retry is authorized.

Acceptance requires three real maximum-capacity proofs, fresh expected-input
verification, rejection of all 100 public mutations and the frozen coverage,
padding, range, first/middle/final trace, alias, proof and wrong-key cases. The
wrong-key check uses an actual smaller encoder key with the same public layout.
Keep every failure and stopped-worker artifact; download and rehash everything
before removing temporary storage. Replay the proofs with the original dependency
build on the Mac under separately retained native-input and key pins.

A maximum export, setup or prepared job is not a proof. A successful synthetic
campaign still supplies no trained model quality, operational enrollment, accepted
ceremony, independent verifier/security review, hiding qualification or genuine
hardware evidence. `qualified_backend` remains false. No procurement, reviewer
contact, collaborator, private upload or ongoing scheduler follows from this plan.
