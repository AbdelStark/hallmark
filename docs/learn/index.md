# Learn verifiable inference

These four chapters explain the proofs for Hallmark's short TinyLlama response
and classifier decisions: what they establish, how to run them, and which
questions they leave unanswered. No cryptography background is assumed.

| Step | Question | What you will be able to do |
|---|---|---|
| **1. [From inference to a claim](computation-and-claims.md)** | What does a proof establish? | Separate computation, model identity, input provenance and policy quality |
| **2. [Read a proof statement](read-a-proof.md)** | What exactly must be true? | Identify public expectations, witnesses and checks in each Hallmark flow |
| **3. [Circle STARK proof paths](proof-systems.md)** | Why SASH for LLMs and direct STWO for classifiers? | Compare their roles without confusing unlike workloads |
| **4. [Verify one request](one-request.md)** | How do the pieces meet? | Follow the three classifier cases and the composed LLM request |

## Vocabulary {#the-smallest-useful-vocabulary}

**Statement**
: The precise claim being checked, including the expected model, input and output.

**Witness**
: Values used to establish that claim, such as intermediate activations or an execution trace.

**Proof**
: A cryptographic object checked by a verifier against public expectations. A proof file is not its own trust anchor.

**Enrollment**
: The caller's decision about which model, program, parameters and keys it expects.

**Integrity**
: Evidence that the stated computation holds under its assumptions.

**Zero knowledge**
: A separate privacy property: the proof reveals no additional witness information beyond the statement. Hallmark's current LLM path makes no hiding claim.

**Attestation**
: Evidence about a measured hardware/software execution environment. Hallmark's current integrity MVP does not claim hardware attestation.

!!! tip "Prefer running something first?"

    [Choose a workflow](../START.md). The software smoke test needs no GPU or account.
    The local classifier workflow produces real proofs; the smoke test does not.

## Reading a benchmark {#a-reading-habit-worth-keeping}

For each timing, check which computation and inputs were used, which verifier
ran, and which stages the measurement includes. Hallmark's 53.94 s GPU figure
covers summed proving stages; preparation and verification take additional time.

Continue with [from inference to a claim](computation-and-claims.md).
