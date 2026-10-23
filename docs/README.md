# Hallmark documentation

Start with the [project overview](../README.md). For a runnable path, go directly
to the [classifier demo](DEMO.md). Read [what is proved](PROOFS.md) for the claim
and trust boundary; for evidence, read [results](RESULTS.md).

## Use and reproduce

| Document | Purpose |
|---|---|
| [What is proved](PROOFS.md) | Classifier claim, public inputs, caller checks and exclusions |
| [TinyLlama response proof](LLM-PROOF.md) | `make e2e-llm`, exact prompt/answer, complete inference relation and limits |
| [End-to-end demo](DEMO.md) | Train, export, prove and separately verify three classifiers on one Mac |
| [Results and limitations](RESULTS.md) | Model/data notes, measured results, failed experiments and evidence links |
| [Operations](OPERATIONS.md) | Focused experiment recipes, enrollment, retained artifacts and recovery |
| [Packaging](PACKAGING.md) | Pinned build environment, reproducible archives and installed-package checks |
| [Contributing](../CONTRIBUTING.md) | Development setup, test selection and change review |
| [Security](../SECURITY.md) | Trust assumptions, qualification gaps and private reporting |

## Understand the design

The [canonical specification](../SPEC.md) is the entry point to the proposed v1
system. A specified interface is not necessarily an implemented one. Check the
[supported API table](spec/02-public-api.md) and [current state](../research/STATE.md)
before using a command or relying on a capability.

| Document | Purpose |
|---|---|
| [Baseline contract](SPEC.md) | Original software arithmetic and commitment contract; dated scope |
| [ML plan](ML-PLAN.md) | Classifier candidates, training and export strategy |
| [Evaluation](EVALUATION.md) | Data lineage, split isolation, calibration, metrics and claim boundaries |
| [Implementation tracker](roadmap/IMPLEMENTATION.md) | Work-item dependencies and links to live issues |
| [Specification checks](SPEC-CHECK.md) | Local links, requirement coverage and explicit live tracker audit |
| [Dependency notices](DEPENDENCIES.md) | Reviewed software versions, licences and redistribution limits |

For the current demo, the shortest design trail is:

1. [0058: specialized trained classifier path](decisions/0058-specialized-trained-classifier-path.md)
2. [0059: contextual byte CNN](decisions/0059-contextual-byte-cnn-screen.md)
3. [0060: revised synthetic screen](decisions/0060-contextual-screen-followup.md)
4. [0061: complete CNN proof](decisions/0061-complete-contextual-cnn-proof.md)
5. [0062: three trained classifiers on one request](decisions/0062-trained-common-request-proofs.md)

The [Go probe guide](../research/probes/gnark/README.md) covers individual circuit
experiments. The [separate verifier guide](../research/probes/py_ecc/README.md)
describes its supported proof encoding and pairing checks.

## Inspect the research record

- [Real LLM proof plan](../research/real-llm-proof-plan.md): pretrained response
  target, SASH source review, measured preparation and remaining proof gates.
- [STATE](../research/STATE.md): current capability and next qualification gates.
  Older entries below the opening summary are historical.
- [Ledger](../research/LEDGER.md): chronological commands, failures and results.
- [Program](../research/PROGRAM.md): hypotheses, controls and stopping rules.
- [Sources](../research/SOURCES.md): primary sources and inherited research limits.
- [Source packet](../research/source/README.md): dated design material, preserved
  separately from later normative decisions.

Raw checkpoints, setup keys, proofs and run directories stay local. Public evidence
files contain numeric summaries and hashes. A recorded hash is an identity check;
it does not make an untrusted source an authenticated enrollment authority.
