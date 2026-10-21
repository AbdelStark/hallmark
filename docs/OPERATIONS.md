# Run and resume guide

Read `AGENTS.md`, `research/STATE.md`, this guide, then the task's spec. Inspect branch, remote and `git status --short` before edits. Preserve other work. Do not use an old agent summary as evidence that a run passed.

## Local gates

```
uv sync --locked --extra train
make check
make check-train
make package-check
make package-check-train
```

Core tests do not require scikit-learn; the training marker may skip if the extra is absent.
`make check-train` installs only the locked train extra and invokes
`pytest -m train --require-train` with one BLAS/OpenMP thread. The guard requires
at least one selected training test and successful setup, call and teardown for
every selected training test; skips, xfails/xpasses and collection/setup-only
runs cannot pass. Plain `make check` retains the optional-training boundary.

The supported interpreter matrix is CPython 3.12, 3.13 and 3.14, with 3.12 as
the default local pin. Linux and macOS run core/package and required-train/installed
train gates on each version; see [reproducible packaging](PACKAGING.md). CI runs core checks/package installation and a separate
required-training job on each interpreter. These are software fixture checks,
not research results or hardware/proof integration.

CI has read-only repository permissions, disables persisted checkout credentials,
and has no secrets, self-hosted runners or transcript/artifact uploads. Push, PR
and manual workflow dispatch run the same offline fixture jobs. Dependency
installation and the fresh-environment packaging check may fetch locked software
packages; they do not fetch research datasets or models.

There is no privileged integration workflow. A real proof/hardware run needs an
approved protocol, host and budget under the admission gates, and separate
owner-authorized execution on that host. Manual CI dispatch does not supply
that authority. If hosted jobs cannot start because of account billing or limits,
retain the unavailable run/annotation; the owner must resolve account settings.
Agents must not change billing or replace unavailable hosted evidence with a local pass.

## Conformance corpus

Before full-system work, run the frozen software corpus:

```sh
make check-conformance
uv run --locked python scripts/check_conformance.py --corpus tests/vectors/v1/corpus.json --expected-corpus "$(cat tests/vectors/v1/corpus.id)" --self-test
```

The first command explicitly checks software components and exits 0 after
156 matches. The second requests all required evidence and currently exits 3,
reporting 32 unavailable cases. Neither counts missing evidence as passed;
both leave `independent:null`. The pin above is the reviewed repository fixture
pin, not operational enrollment. Use an independently approved pin when checking
another corpus. Preserve failures and use a new directory/identity for corrections;
see [conformance reproduction](decisions/0013-frozen-conformance-corpus.md).

## Research run

Freeze config and evaluate a fresh directory. Set BLAS/OpenMP thread variables to 1 for the bootstrap. Save the printed manifest hash outside the bundle. Run `audit-run` with that hash and the exact dataset. Inspect the report's evidence class, counts, uncertainty and missing mechanisms before writing a conclusion. A hash supplied by the bundle's author does not authenticate that author.

Compare repeated runs on model/config/predictions/results, not `source.json` byte equality: git state, Python version and platform metadata can differ and must be explained. Full scientific reproducibility and an independent verifier remain separate gates.

## MLP training fixture

The MLP fitting API accepts only training records. `fit_mlp(rows, config)`
returns a checkpoint and epoch samples; it does not read a dataset or save files.
To resume, pass `checkpoint=...` and its separately retained
`expected_checkpoint=checkpoint.identity()`. Resume rejects changed training,
configuration, implementation or recorded numerical environment. `steps` bounds
an invocation without changing the frozen epoch limit. An epoch-limit result is
explicitly nonconverged unless its tolerance criterion passed.

`quantize_mlp(checkpoint, config)` returns integer weights and explicit scales.
Pass them to `compile_mlp(..., hidden_fraction=0)` with the recorded first/last
fractions and a matching byte input profile. Compare a native integer score
divided by `score_scale` with the float logit. Calibrate on native integer scores;
do not reuse a float threshold. Export does not enroll classifier/backend trust.

Reproduce the authored marker fixture into a **new** local directory:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  uv run --locked --extra train python scripts/check_mlp_training.py \
  fixtures/mlp-training.json --expected-fixture "$(cat fixtures/mlp-training.sha256)" \
  --output runs/mlp-training-fixture
```

The fixture fixes seeds 17/29/43 and saves the environment, configuration,
partial/final/resumed optimizer checkpoints, epoch losses, export and numerical
scores. All checkpoint outputs remain local. It checks fresh/resumed equality,
complete byte coverage and a fixed numerical-error tolerance, including maximum
length and Unicode. It does not select a policy, measure injection quality,
authenticate training or produce a proof. Omitting `--output` checks the fixture
contracts without importing NumPy or training; both installed-package gates use
that core path, and the train package gate also executes all three seeds.

The full baseline roster and admitted real-data commands remain work for issue
#16. Do not treat this fixture as a measurement admission.

## Grouped comparison fixture

`grouped_selection(train_rows, plan)` accepts only training records and a frozen
`SelectionPlan`. It preserves five rotations for every declared candidate and
seed, with group-disjoint fitting, internal threshold selection and validation.
It retains ineligible/nonconverged candidates and reports missing guard/encoder
comparisons. Pass-all and block-all remain fixed controls.

Refit a selected candidate with `fit_candidate(train_rows, candidate, plan, seed)`.
Save the returned `record` and its identity before calibration. The returned
`Fitted` object is in-process state; do not pickle it or treat its JSON record as
authenticated training. `calibrate_fitted(..., expected_fit=pin, target_fpr="0.01")`
accepts calibration rows only. Retain its identity separately before calling
`evaluate_fitted(..., expected_fit=pin, expected_calibration=calibration_pin)` on
test rows. The joint MLP allocation is `"0.0035"`; standalone learned comparisons
use `"0.01"`. Wrong pins, nonconverged fits and group/prompt overlap reject.

The character baseline saves exact vocabulary, coefficients, solver settings,
iterations, seed and environment identities. Its liblinear solver supports only
a fresh fit, not optimizer resume. The MLP retains its explicit optimizer checkpoint.
Native score evaluation does not enroll a proof backend or authenticate training.

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
  uv run --locked --extra train python scripts/check_selection.py \
  fixtures/grouped-selection.json --expected-fixture "$(cat fixtures/grouped-selection.sha256)" \
  --output runs/grouped-selection-fixture
```

Use a fresh output directory. This fixed software fixture performs 75 fold fits,
retains 15 deliberately nonconverged MLP attempts, and refits/calibrates/evaluates
nine selected models. Its loose successful-MLP tolerance exercises the pipeline;
neither MLP configuration is a real study candidate. All artifacts stay local.
Omitting `--output` validates contracts without importing optional libraries.
Both installed-package gates check that path; the train package gate executes
the entire fixture. Reviewed real data and a final admitted
measurement command are still pending; none is replaced by a synthetic pass.

## Local guard runtime

`make check-guard` exercises an authored tiny graph with the optional locked
`guard` extra. `make package-check-guard` repeats it through an isolated installed
wheel. These commands download software dependencies only, never research models.
CI runs this fixture on Linux/macOS CPython 3.12; actual model qualification is
currently Mac CPU only.

`LocalGuard(root, spec, expected_spec=spec_pin)` reads `model.onnx` and
`tokenizer.json` under a caller-owned root into checked bytes. `GuardSpec` pins
their byte counts/hashes, vocabulary, input/sequence limits and 1–4 CPU threads.
The caller owns the process, filesystem and time/memory budget; this is not an
OS sandbox. The adapter never downloads assets or uses credentials. Core imports
do not import its optional runtimes.

For the fixed pretrained comparison, retain `guard.record` and independently
pin its identity before `bind_guard(guard, bounds, expected_runtime=runtime_pin)`.
Use the returned in-process `Fitted` object with `calibrate_fitted` and
`evaluate_fitted` exactly as above. The declared empty local training inventory
does not establish clean upstream pretraining; contamination review remains an
admission obligation.

For bounded engineering probes, create a `GuardSpec` JSON and an input object
with schema `hallmark/guard-probes/1`, `fixture_only: true` and at most 16 harmless
prompt strings. Enroll their spec identity and input-file SHA-256 separately.
Then, inside an admitted foreground controller with a fresh output directory:

```sh
HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false \
  uv run --locked --extra guard python scripts/run_guard.py \
  --assets "$GUARD_ASSETS" --spec "$GUARD_SPEC" --expected-spec "$GUARD_SPEC_PIN" \
  --inputs "$GUARD_PROBES" --expected-inputs "$GUARD_PROBES_SHA256" \
  --output "$GUARD_OUTPUT"
```

The [retained engineering evidence](../research/evidence/w15-guard-cpu-2026-10-20.json)
contains the actual pins and numeric results. The full prompt enters the pinned,
lossy tokenizer; no prefix/suffix is truncated. Contiguous 510-token blocks get
CLS/SEP individually, with no padding. The maximum float64 difference between
the two float32 logits is the record score. Positive margins on the two harmless
maximum-length repetitive probes remain visible. This command neither calibrates
a task decision nor grants real-data measurement admission.

## Failure and interruption

Keep failed output directories. Never overwrite a complete run or repair its hashes in place. Diagnose from a copy, issue a new experiment identity if the protocol changes, and record failed hypotheses in `research/LEDGER.md`. On resume, recheck source/data identity and actual environment; do not continue training from an undocumented checkpoint.

If no authority for a needed resource exists, produce the smallest bounded proposal with host/data/cost/policy/kill criteria. Stop before the download, paid job, hosted API call or upload. Do not start a daemon, scheduler, remote runner or multi-agent campaign merely because this project is agent-native.

## External registry checkpoint provisioning

The owner must first approve signing-key custody and the exact signature-library
revision through the private REGISTRY-ROOT record. No operational roots are
provisioned by this repository. Fixture keys are public test data.

1. Obtain the trust policy, accepted artifact identities, exact registry-body
   digest and sequence through the relying party's authenticated channel.
   Compare `trust.identity()` to the independently retained trust digest.
   A bundle cannot provide this authority.
2. Retain the digest/sequence outside the bundle and the verifier's working
   storage. Create a fresh `RegistryState(schema_id="hallmark/registry-state/1",
   sequence=approved_sequence, digest=approved_digest)`.
3. In an owner-controlled local directory outside git, call
   `provision_state(path, external_state)` from `hallmark.registry_store`.
   The new SQLite file is mode 0600; existing files are refused. Do not reuse a
   failed initialization without inspection.
4. Read the checkpoint with `read_state(path)`, then call
   `enroll_and_store(path, snapshot, trust, expected_state, now, history=history)`.
   Supply each signed successor after the checkpoint and before the final
   snapshot. A direct successor uses empty history. Use the relying party's clock.
5. Require every used identity from the returned enrollment and resolve the
   exact externally pinned policy/classifier manifests. Re-enroll at each new
   verification clock; a saved enrollment result is not a credential.

Failures leave the prior checkpoint in place; a concurrent writer or stale caller
fails without retry. Read the current state and inspect the failure before retrying.
Keep the database and SQLite journal together. Restore a whole-store backup only
under owner re-enrollment with the independently retained checkpoint, never by
trusting a bundle's latest claimed sequence. More than 1,024 intermediate snapshots
requires a new authenticated checkpoint. Network filesystems, untrusted parent
directories and malicious modification by the OS account are outside this store's
guarantees. The [decision](decisions/0010-external-enrollment.md) specifies exact
signature, time, persistence and resource boundaries.

## Registry authoring and key rotation

Exercise only the public fixture keys, without provisioning operational roots:

```sh
uv run --locked python scripts/check_registry_vectors.py fixtures/wire/registry-rotation-v1.json
```

This creates temporary stores, verifies both transition authorizations, retains
the old/new signed snapshots, runs the actual CLI and rejects a replay. The same
command runs against the isolated installed wheel in `make package-check`.

For operational work, first record owner approval of custody, the exact signature
library and the reviewed artifact inventory in the private REGISTRY-ROOT record.
Keep private keys, that record and the databases outside git. The authoring API
accepts caller-owned Ed25519 key objects; it has no key-generation/loading command.
An operational approval record has not been supplied by these fixtures.

1. Prepare a complete reviewed `RegistryBody`, with immutable validity/review
   metadata for each identity. Use `next_snapshot` for successors. Retain every
   old entry; retire an identity by setting `retired_at`, never by removing it.
   An existing retirement can be made earlier, never postponed or cleared.
2. Call `sign_snapshot(body, external_trust, key_objects)`. Signers must be distinct
   authorized keys satisfying the threshold. Inspect the exact body before signing.
3. Start an owner-controlled authoring archive with `create_history` and an
   independently pinned state. Append each new signed snapshot with `append_history`
   and the last state. Keep returned state identities independently; never replace
   an old archive to hide a failure. Use `read_snapshot`/`read_transition` to export
   retained records, checking them against the independently retained state.
4. For rotation, independently provision the complete new policy through the
   approved channel. Its minimum sequence must be the next registry sequence.
   Prepare `RegistryTransition` with both policy digests, both sorted key-ID lists,
   the activation sequence, predecessor digest, reason and review reference.
   Use `sign_transition` with both approved thresholds; then sign the activation
   snapshot under the new policy. Append it with the transition and old policy.
5. Distribute the public signed records through the approved channel. A relying
   party with an already provisioned checkpoint checks ordinary updates with:

   ```sh
   hallmark registry-check snapshot.cbor --trust trust.cbor --state checkpoint.sqlite --now 1792497600
   ```

   Supply each missing intermediate snapshot in order with `--history FILE ...`.
   For exactly one activation, supply all of `--old-trust old-trust.cbor`,
   `--transition transition.cbor` and `--previous previous.cbor` instead of history.
   Replace the example clock with the relying party's actual verification time.
6. Retain the returned registry/trust IDs only after a successful command.
   The checkpoint now records the external trust digest as well as registry state.
   Ordinary updates cannot switch policies; rotation changes both atomically.
   Reusing the old policy afterward fails. Other policy changes require explicit
   owner re-enrollment in a new store. Preserve the prior store and checkpoint.

The first successful trust binding upgrades the checkpoint database from `HMR1`
to `HMR2`. Older packages reject the new application ID. Keep a backup and do not
revert software or restore old trusted state to work around a failed check.

Missing old-threshold authorization requires owner recovery/re-enrollment; an
unsigned replacement is never a valid transition. An archive is not a globally
witnessed log: compare conflicting roots out of band. Signatures authenticate
registry decisions, not scientific quality or hardware/proof evidence. The full
[decision and bounds](decisions/0012-registry-authoring-rotation.md) describe
single-account, local-filesystem and crash-test limits.

## Offline bundles and private openings

Use `decode_bundle(raw, limits=external_trust.limits)` for untrusted binary input.
It checks the complete wire size/depth, exact embedded file hashes/references and
per-proof limits. It returns a container, not an authenticated enrollment or a
verified claim. Neither file paths nor registry entries trigger network/file reads.

Keep the B1 opening in a separately authorized confidential exchange. Bundles in
both modes reject opening fields and canonical embedded opening/response records.
The assembler must also restrict its file inventory; opaque payloads are not a
general-purpose secret-sanitization boundary. Response-envelope serialization can
disclose its private response/opening and belongs only on the response channel.

A collection `pending`, `failed` or `expired` status is not a partial valid bundle.
`ready` names a complete file but does not authenticate it. A reported
`VerificationResult` is also not a verifier: decoding an `accepted` flag does not
make the referenced evidence true. See [the contract decision](decisions/0011-offline-bundle-contracts.md)
for exact claim, status and privacy boundaries. Full assembly and verification
remain W26–W28.

## Private local events

Choose a fresh path beneath an owner-controlled local directory outside git.
Set `max_bytes` from the approved run budget (4 KiB–1 MiB). For an admitted
operation, use:

```python
from pathlib import Path
from hallmark.events import EventLog, inspect_events
from hallmark.wire import encode

path = Path("/private/approved/run-events")  # Parent must already exist.
with EventLog(path, max_bytes=16384) as log:
    with log.attempt():
        with log.stage("parse"):
            payload = encode({"fixture": 1})
summary = inspect_events(path, max_bytes=16384)
assert summary.status == "complete"
```

Only the finite stage and monotonic timing are logged; `payload` is not.
The self-contained harmless fixture uses a temporary directory:

```sh
uv run --locked python scripts/check_event_storage.py
```

It retains a failed attempt and explicitly retries once. In actual runs a retry
requires a transient `HallmarkError(..., retryable=True)`, unchanged inputs/key/
setup and remaining original admission budget. No retry happens automatically.
A storage failure may leave only a partial stream/pending marker; preserve the
entire directory. Do not edit or resume it, delete failures to improve a summary,
or infer completion from the last stage. Inspection while a writer is live fails.

Treat events and receipts as private metadata, with the same access, backup and
retention policy as the run. Keep them out of git and sharing tools; there is no
telemetry, upload or cleanup scheduler. Local permissions are not encryption.
After ambiguous filesystem failures, quarantine the archive. See the
[storage decision](decisions/0015-private-event-storage.md) for filesystem and
power-loss limits. Legacy `run` artifacts do not gain this boundary retroactively.

## Caller-enrolled baseline comparisons

`scripts/run_comparisons.py` joins reviewed admission, reproduced source import,
train-only selection, final fitting, calibration and test scoring. Obtain the
expected review identity from the authenticated reviewer outside the dossier.
The command verifies its bindings; it cannot authenticate a human approval or
replace label/contamination review. See [decision 0031](decisions/0031-admitted-comparison-command.md).

Prepare an owner-controlled, read-only dossier containing `policy.cbor`,
`protocol.cbor`, `review.cbor`, `comparison.json`, `import.cbor`, `dataset.cbor`,
and the exact referenced files under `documents/`, `sources/` and `dataset/`.
The [run-plan schema](../fixtures/comparison-run.schema.json) pins the import,
dataset, selection, guard assets and guard runtime. Bind the exact bytes returned
by `hallmark.comparison_run.execution_inventory()` into the admission evaluator
and first six candidate code references; bind the comparison-plan bytes into
their configuration references. Review these actual inventories and the source
evidence before enrolling the review identity. The seventh candidate remains
explicitly unavailable in this W15 path.

After real admission, invoke with independently supplied paths and review pin:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  uv run --locked --extra train --extra guard python scripts/run_comparisons.py \
  --dossier "$DOSSIER" --guard-assets "$GUARD_ASSETS" \
  --expected-review "$REVIEW_ID" --output "$FRESH_OUTPUT"
```

This is a command template, not an admitted real-data run. The caller enforces
the reviewed process time/memory and total working-storage limits, records a
resource receipt, and prevents reuse of test data across separate output roots.
The runner checks time between stages and its output-byte allowance; it cannot
interrupt a blocked native operation. Roots and parent directories must remain
under the caller's control. Keep dossiers, source rows and fitted artifacts out
of git.

All retained fit/calibration pins are written to `frozen.json` before test
scoring. Failures preserve partial artifacts and sanitized `failure.json`;
existing output directories are refused. Exit 0 means the W15 baseline roster
executed; exit 3 retains an incomplete comparison result. Neither exit establishes
task quality, full-study completion or independent verification. Default runs
reject fixture data. `make check-comparison` explicitly uses invented approvals,
authored rows and a tiny ONNX marker graph; `make package-check-comparison` also
executes that fixture against an installed wheel.
Read the result status from stdout JSON. Optional native libraries can emit host
device warnings on stderr even when execution succeeds; retain that diagnostic
stream privately. Exceptions handled by the CLI use sanitized error JSON.

## Approved synthetic pipeline development

[Decision 0033](decisions/0033-approved-synthetic-pipeline.md) allows agent-reviewed
synthetic data without human review for the current pipeline stage. The existing
`--fixture-only` mode preserves that evidence class through import, fitting,
calibration and evaluation. Its internal marker approval documents are software
fixtures, not a human signature or operational enrollment. An outer run protocol
must record the real authority, exact guard assets, resources and agent review.
The same command can use the pinned real guard weights with an explicitly
synthetic dossier; this does not validate injection-detection quality.
Human labels and the old blank review packet are not prerequisites for this stage.

## Frozen group report command

The core-only API is `hallmark.group_evaluation.group_report`. Construct and retain
`GroupReportPlan` before reporting, including the source/provenance SHA-256 values,
`dataset_identity(test_rows)`, `evaluator_identity()`, member fit/calibration pins,
annotations, whole-group exclusions and prespecified pairs. Save `plan.identity()`
outside the input directory. Every family/variant needs all seeds 17/29/43 or one
fixed, untrained member (`seed: null`). Represent failed/missing members explicitly
with `ReportUnavailable`; do not drop them or average only surviving seeds.

For existing W15 output, copy each calibration into `ReportObservation.calibration`
and the corresponding evaluation's `predictions` into its predictions field.
Use the already retained `frozen.json` fit/calibration identities in the plan;
keep that file's externally enrolled inventory pin. Preserve the originating
source, run, review and data identities in the provenance document. This adapter
does not authenticate those artifacts or their historical freeze order. Native
score scales must match the retained fit/export record; float scales are one.

```sh
uv run --locked python scripts/report_groups.py \
  --plan /path/to/plan.json --expected-plan "$REPORT_PLAN_ID" \
  --records /path/to/test-records.jsonl \
  --observations /path/to/name-to-observation.json \
  --source /path/to/source-inventory.json --provenance /path/to/provenance.json \
  --output runs/new-group-report
```

The command rejects existing output directories. New reports contain no prompt
text, but identifiers and source/provenance metadata can still be private. Keep
inputs, raw scores and reports local unless publication is separately authorized.
A failed attempt retains `failure.json` and has no completed `report.json`.

Reproduce the authored, correlated fixture without NumPy, model files or downloads:

```sh
uv run --locked python scripts/check_group_evaluation.py --output runs/new-group-fixture
```

This fixture uses 36 records in 12 declared groups, three training-seed labels,
three 10,000-resample float/integer comparisons and explicit unavailable encoder
members. Its scores are authored software controls, not trained classifiers.
Repeat into a second fresh directory and compare report bytes. Python and its
random implementation are part of the evaluator identity.


## Synthetic encoder conformance

`IntegerGraph` implements the nine existing integer DAG operations with bounded
exact row-major tensors. `execute_encoder` binds a program, classifier, profiles,
constant bytes, operator bytes and the supported byte-tokenizer recipe before
preparing every input chunk. No optional runtime, download or file lookup occurs
inside either API. Use a caller-owned run budget. Returned tensors and token IDs
are private diagnostics; their serialization is not authenticated evidence.

The committed authored two-feature graph has both normalization stages and a
separately written rational/Decimal oracle. Check its frozen vectors against the
installed runtime with an independently retained fixture pin:

```sh
uv run --locked python scripts/check_encoder_vectors.py \
  fixtures/wire/integer-encoder-v1.json \
  --expected-fixture "$(cat fixtures/wire/integer-encoder-v1.sha256)"
```

The checked-in pin identifies this public software fixture, not operational
trust. The command compares every intermediate and strict-threshold result in
eight cases. Repository tests additionally check all embedding classes/masks,
normalization table entries, malformed contracts, padding isolation, complete
32,767/32,768-byte inputs and overflow before rescaling. `make package-check`
executes the small vectors from a fresh installed wheel.

See [decision 0051](decisions/0051-complete-synthetic-encoder.md) for the exact
nonlinear tables, limits and approximations. The native result cannot satisfy
W18 qualification, W12 qualified-encoder admission, a real proof, safety quality
or independent verification. Keep prior experiments and missing results intact.
