# Run and resume guide

Read `AGENTS.md`, `research/STATE.md`, this guide, then the task's spec. Inspect branch, remote and `git status --short` before edits. Preserve other work. Do not use an old agent summary as evidence that a run passed.

## Local gates

```
uv sync --locked --extra train
make check
make check-train
make package-check
```

Core tests do not require scikit-learn; the training marker may skip if the extra is absent.
`make check-train` installs only the locked train extra and invokes
`pytest -m train --require-train` with one BLAS/OpenMP thread. The guard requires
at least one selected training test and successful setup, call and teardown for
every selected training test; skips, xfails/xpasses and collection/setup-only
runs cannot pass. Plain `make check` retains the optional-training boundary.

The supported interpreter matrix is CPython 3.12, 3.13 and 3.14, with 3.12 as
the default local pin. CI runs core checks/package installation and a separate
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
