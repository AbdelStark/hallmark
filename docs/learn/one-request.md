# Verify one request

The local classifier workflow trains an MLP and a contextual byte CNN, exports
exact integer graphs, and proves the rule, MLP and CNN decisions for each of
three synthetic requests.

```sh
make e2e
```

This command requires the [Mac demo prerequisites](../DEMO.md#prerequisites).
For a small software-only check on Linux/macOS, follow
[the workflow chooser](../START.md); that check generates no proof.

## Follow the evidence

```mermaid
flowchart TD
    D[Frozen synthetic fixtures] --> T[Train MLP / CNN and export integer models]
    T --> C[Compile gates and enroll public preprocessing]
    E[Caller-owned request and expected identities] --> P[Three requests × three Circle STARK proofs]
    C --> P
    P --> V[Fresh proof-only STWO verification]
    E --> V
    V --> G[Host all-pass gate over verified verdicts]
```

The caller reconstructs public inputs from its expected request. Before
interpreting the verdicts, it checks the classifier, program, preprocessing and proof parameters
against identities chosen outside the proof bundle. Running a downloaded
Hugging Face model computes a score without these proof or enrollment checks.

## Three controls, different reasons to block

| Case | Rule | MLP | CNN | All-pass gate |
|---|---|---|---|---|
| Benign active action, restricted action quoted | Pass | Pass | Pass | Pass |
| Restricted active action, benign action quoted | Pass | Pass | Block | Block |
| Benign case prefixed with `BAD; ` | Block | Pass | Pass | Block |

The contextual pair has the same byte counts. The MLP cannot distinguish it;
the CNN can use local order. The literal rule detects its fixed marker,
including across chunk boundaries.

These controls test classification under the artificial grammar and the
proof workflow. Real-world safety performance has not been evaluated.

## What to inspect after the command

The driver prints a fresh local `runs/e2e-…` path. Read its
[documented output layout](../DEMO.md#evidence-bounds-and-failures):

- training records and original/resumed checkpoints;
- quantizations and integer model identities;
- caller enrollment, its pin and proof files;
- fresh proof-only verifier results;
- cross-request substitution and arithmetic checks.

The retained model exports are also available as
[public model releases](../MODELS.md). Their pinned revisions and manifests
let you inspect the weights without rerunning training.

## Join the LLM and classifier proofs {#now-join-the-llm}

```sh
make e2e-composed
```

A fresh run also launches the paid LLM workflow; read its
[prerequisites and cost ceiling](../COMPOSED-DEMO.md#run-the-workflow) first.
Caller-owned retained inputs can avoid new cloud jobs.

The composition binds three new classifier proofs to the proved TinyLlama
request. The classifiers inspect its prompt only. The frozen CNN blocks
“Name the capital of France in one short sentence.” Verification accepts that
block verdict because it matches the CNN computation.

## Next steps

[Run the full classifier guide](../DEMO.md) ·
[Prove the pretrained response](../LLM-PROOF.md) ·
[Audit the research evidence](../research/index.md) ·
[Contribute a matched backend comparison](https://github.com/AbdelStark/hallmark/issues/112)
