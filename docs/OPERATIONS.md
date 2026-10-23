# Run and resume guide

For the complete current training/proof path, start with the [demo walkthrough](DEMO.md).
This guide retains focused commands and historical experiments; their capacities
and evidence boundaries differ. See [results](RESULTS.md) for the current comparison.
For pretrained LLM inference, use [the `make e2e-llm` guide](LLM-PROOF.md#run-it):
local witness preparation, bounded HF CPU jobs and retained proof-only verification.

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
required-training job on each interpreter. The Python jobs are software fixture checks. A separate proof-artifact job builds
a pinned synthetic encoder proof and checks it with separate arithmetic; it does
not run the full Mac campaign or establish hardware/operational qualification.

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

## Common-input synthetic proofs

`scripts/run_common_input.py` connects the three fixed native classifiers to
fresh actual keys and a shared caller-bound transcript. It is a Mac arm64
research controller, with an eight-byte input capacity and the limits in
[decision 0057](decisions/0057-common-input-program-enrollment.md). It does not
run inference, produce hardware evidence, admit a backend, or accept a policy.

Use the already reviewed Go toolchain/dependency pins to build
`research/probes/gnark` into a local binary. Use a separate Python environment
installed from `research/probes/py_ecc/requirements.txt` with `--require-hashes`;
the main locked environment remains unchanged. Record the binary's SHA-256
outside the output directory, then run with a fresh directory:

```sh
uv run --locked python scripts/run_common_input.py \
  --binary /absolute/path/to/probe --expected-binary "$PROBE_SHA256" \
  --verifier-python /absolute/path/to/verifier-env/bin/python \
  --output runs/common-input-fresh
```

The runner checks exact compiled relations, sets up three keys, and writes
`enrollment.json` and its separately retained pin before any proving worker.
It derives complete classifier manifests and a policy from those real keys,
reconstructs native public inputs, and verifies each three-proof case with
separate arithmetic. The first `allow` case must pass before either rejection
case runs. Each case retains its caller expectation/opening, native assignments,
proof bundle, separate-verifier jobs, worker plans and raw costs. Eighteen
cross-request proof substitutions and the fixed arithmetic-negative roster for
each key must reject before `result.json` is written. Failures retain
`failure.json` and all preceding artifacts; use a new directory for a retry.

For a separate caller-side binding check, `common_input.check_bundle` takes the
externally retained enrollment hash, caller-owned `TranscriptOpening` and
`RequestExpectation`, and candidate bundle bytes. It returns exactly three
pairing jobs, **not acceptance**. Pin those job bytes and pass them to
`research/probes/py_ecc/verify_set.py --jobs jobs.json --expected-jobs HASH`
using the reviewed separate environment. Do not substitute openings, expectations
or enrollment hashes supplied only by a prover for caller-owned values.

A `release` value in these research bundles is only the native all-pass decision.
The encoder is the frozen synthetic pass-all control; the two rejecting cases
exercise rule/MLP composition, not useful safety classification. The separate
verifier is experimental and unaudited. Neither a successful run nor its local
setup keys establish production enrollment, setup security, zero knowledge,
hardware provenance or full MVP completion.

## Trained MLP proof fixture

`scripts/run_trained_mlp.py` connects the existing three-seed trainer and integer
exporter to a dedicated byte-weight lookup circuit. It requires Mac arm64 and
the reviewed Go binary and separate verifier environment described above. The
fixed authored data, threshold, capacities and limits are in
[decision 0058](decisions/0058-specialized-trained-classifier-path.md).

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
uv run --locked --extra train python scripts/run_trained_mlp.py \
  --binary /absolute/path/to/probe --expected-binary "$PROBE_SHA256" \
  --verifier-python /absolute/path/to/verifier-env/bin/python \
  --output runs/trained-mlp-fresh
```

Keep the verifier's virtual-environment invocation path; resolving its Python
symlink to the base interpreter loses that environment's packages. Record source,
environment and binary hashes outside the fresh output before running. The
controller trains and exports seeds 17/29/43, enrolls the exact model/circuit/key
before each batch, and runs all eight-byte proofs before the 1,024-byte roster.
The larger roster must show both decisions under threshold zero. Each batch
requires three proofs, three unsatisfied witness mutations and separate pairing
verification with the existing malformed/public-input/key/proof corpus.

Inspect each worker's `plan.json`, `cost.json`, result files and stderr. Any
failure retains the preceding artifacts; restart only into a new directory.
Repeat with fresh training and setup keys, comparing export identities, scores
and negative rosters. Checkpoints and raw runs remain local. This proves a
bounded synthetic execution relation; it does not measure task quality, prove
the profile's 32,768-byte maximum, or qualify setup, hiding or hardware provenance.

## Trained contextual CNN screen

The authored scope task and two immutable protocols are described in
[0059](decisions/0059-contextual-byte-cnn-screen.md) and
[0060](decisions/0060-contextual-screen-followup.md). The first all-seed screen
failed. Its old test is exploratory training data in the explicitly new second
experiment; the second calibration/test contain fresh action-pair groups.

Run the fixed follow-up with the locked train extra and an unused directory:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
uv run --locked --extra train python scripts/run_contextual_cnn.py \
  --study v2 \
  --expected-protocol 3c47c07a5a3413f00814b957ae8752bcb3f786b0c6484becd6cab5290beb5394 \
  --output runs/contextual-cnn-fresh
```

Enroll that protocol hash outside the output. Supervise the declared 7,200-second,
8 GiB RSS, 1 GiB output and single-worker limits; the command is not an OS sandbox.
It records source/runtime/data pins before fitting, all three full/resumed
checkpoints, exact integer exports and operator maps, calibration before test,
every prediction/count and a final artifact manifest. Keep all checkpoints, input
traces and raw run directories local. The printed manifest hash must be retained
outside its bundle. A failed quality screen remains a complete negative experiment;
check `all_seeds_pass`, not merely process exit. Execution exceptions retain a
`failure.json` and no complete manifest.

Use a fresh directory for reproduction. Compare training, quantization, profiles,
weights, thresholds and predictions byte for byte; time/RSS are measurements,
not expected deterministic artifacts. `make check-train` exercises numerical
gradients, resume mismatches, byte boundaries, integer oracle agreement, ties,
near-threshold quantization flips and source/label lineage. `make package-check-train`
also trains/exports the smallest 32-channel fixture against the installed wheel.

This training command produces a 96-byte local-context software candidate and
rejects longer inputs. The following sections separately reproduce its real
proof and research enrollment; training alone does not provide them. The artificial run/quote grammar and small,
shared-vocabulary groups do not establish a real-world safety operating point.

## Proving the selected contextual CNN

[Decision 0061](decisions/0061-complete-contextual-cnn-proof.md) freezes the
follow-up's preselected seed-17 quantization, program and threshold. The controller
rejects a different export; retraining to a different artifact requires a new
model identity and experiment. Keep the trained quantization/checkpoint local.

Build the reviewed probe with the pinned Go toolchain and enroll its binary hash.
Use the separately installed, hash-pinned py-ecc environment described above.
The interpreter argument must preserve its virtual-environment invocation path.
Then run on the admitted Mac into an unused directory:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
uv run --locked --extra train python scripts/run_contextual_proof.py \
  --binary "$PROBE_BINARY" --expected-binary "$PROBE_SHA256" \
  --verifier-python "$VERIFIER_PYTHON" \
  --quantization "$CNN_TRAIN/17/quantization.json" \
  --output runs/contextual-proof-fresh
```

The controller checks the learned graph against the original native program,
requires the frozen full-length pair's decision contrast, and enrolls each actual
circuit/key before proving. It runs three small proofs first, nine witness
rejections and the separate arithmetic corpus; only then does it run three
capacity-96 proofs. The re-encoded-input mutation updates the commitment while
retaining the wrong neural trace. Success requires an unsatisfied constraint for
every negative assignment, not merely a child-process error.

Inspect each worker's `plan.json`, `cost.json`, raw proof and verifier output.
Record source/environment/binary pins before execution and compare afterward.
Repeat in a fresh directory with new setup keys; compare model/circuit, scores,
verdicts and rejection rosters. Preserve all failures. The controller enforces
7,200 seconds overall, four worker threads, 8 GiB worker RSS and 8 GiB output;
check the 256 GiB total retained-checkout ceiling before launching. No new cloud
compute is required for the documented Mac path.

These are complete proofs of the admitted synthetic CNN computation. They do not
qualify its task quality, setup custody, hiding, compiler/enrollment authenticity,
hardware provenance, response generation or the full hybrid verifier.

## Trained classifiers on one opened request

[Decision 0062](decisions/0062-trained-common-request-proofs.md) composes the
literal rule, frozen seed-17 trained MLP and screened seed-17 contextual CNN.
It preserves the old eight-byte fixture and admits up to 96 complete prompt bytes.
Reproduce the model exports using the MLP training fixture and contextual-v2
command above; the controller requires their exact frozen quantization hashes.
Use the reviewed probe binary and separately pinned verifier environment:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
uv run --locked --extra train python scripts/run_trained_common.py \
  --binary "$PROBE_BINARY" --expected-binary "$PROBE_SHA256" \
  --verifier-python "$VERIFIER_PYTHON" \
  --mlp-quantization "$MLP_TRAIN/seed-17/quantization.json" \
  --cnn-quantization "$CNN_TRAIN/17/quantization.json" \
  --output runs/trained-common-fresh
```

The binary must include `scaled-rule-* 96`, `trained-mlp-* 96` and `contextual-* 96`.
The controller sets up all three relations, retains the exact circuit/key/model
roster and pins enrollment before producing nine proofs across three fixed cases.
For each case it reconstructs every public input from one caller-owned opening,
checks the all-pass decision and verifies all three proofs in a separate py-ecc
process. It then rejects all 18 cross-request substitutions and runs the
separate arithmetic mutation corpus for each classifier. The result is research
proof composition: `release` is the classifier gate, with hardware explicitly
unaccepted and backend qualification false. The response is authored fixture text.

Keep the external enrollment digest, exact exports, circuit roster, requests,
proofs, worker costs and separate-verifier output. A bundle-provided enrollment
hash is not a trust anchor. The Python binding helper returns pairing jobs, never
cryptographic acceptance. Repeat into a new directory with fresh setup keys and
compare model/circuit identities and decisions. Check the total retained checkout
limit before each launch; per-run limits are 7,200 seconds, four worker threads,
8 GiB RSS and 8 GiB output. No private inputs or cloud jobs are needed.
