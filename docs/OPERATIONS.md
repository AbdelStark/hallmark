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
