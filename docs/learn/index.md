# Learn verifiable inference

You do not need to start with a proof-system paper. Start with a computation
whose result another person wants to check.

Hallmark gives you two concrete examples: a short pretrained LLM response and
a classifier decision. This path builds the vocabulary needed to read their
proof statements, run them, and understand what their evidence leaves open.

| Step | Question | What you will be able to do |
|---|---|---|
| **1. [From inference to a claim](computation-and-claims.md)** | What does a proof establish? | Separate computation, model identity, input provenance and policy quality |
| **2. [Read a proof statement](read-a-proof.md)** | What exactly must be true? | Identify public expectations, witnesses and checks in each Hallmark flow |
| **3. [Two proof systems](proof-systems.md)** | Why Circle STARKs here and Groth16 there? | Compare their roles without confusing unlike workloads |
| **4. [Verify one request](one-request.md)** | How do the pieces meet? | Follow the three classifier cases and the composed LLM request |

## The smallest useful vocabulary

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

## A reading habit worth keeping

For every result, ask: **Which computation? Which expected inputs? Which
verifier? Which measurement boundary?** Keep the answer with the number.

Continue with [from inference to a claim](computation-and-claims.md).
