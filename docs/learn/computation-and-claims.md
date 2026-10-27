# From inference to a claim

Suppose someone returns:

> The capital of France is Paris.

That sentence alone tells you nothing about which model produced it. A model
name next to it is a declaration. A hash can identify bytes. A native rerun can
check a computation. A cryptographic execution proof checks an enrolled relation.

These provide different evidence; the useful choice depends on the question.

## Four questions, four boundaries

| Question | Evidence you need | Hallmark today |
|---|---|---|
| Did the expected computation yield this result? | Exact relation, expected inputs and a checked cryptographic proof | Fixed TinyLlama response and dedicated classifier relations |
| Is this the model I intended? | Independently enrolled model/program/parameter identities | Caller-pinned expectations; optional signed enrollment |
| Where did the input or execution come from? | An authenticated capture/provenance mechanism | Not established by these proofs |
| Is the policy useful? | Task-specific evaluation, suitable data and an adoption decision | Synthetic engineering tasks only |

A proof can be valid while the policy is unhelpful. In the composed demo,
the contextual CNN blocks the ordinary TinyLlama prompt. Its proof establishes
the CNN computation, not a sensible real-world safety rule.

## A useful abstraction

Let \(x\) be the expected input, \(\theta\) the enrolled model, and \(y\)
the claimed result. A witness \(w\) carries the intermediate values needed by
the selected proof relation.

$$
R(\theta, x, y, w) = 1.
$$

The verifier checks a proof against public expectations. It does not infer the
correct model or input from a prover's file names. In Hallmark, root/key enrollment
and request binding are explicit parts of the surrounding protocol.

This notation is an explanation, not a new formal specification.
The actual [LLM](../LLM-PROOF.md#the-statement) and
[classifier](../PROOFS.md) statements define the implemented checks.

## Inference becomes an exact arithmetic problem

Floating-point library calls leave many choices implicit: rounding, clipping,
accumulation, quantization and padding. The proof relation needs a fixed answer
to those questions.

Hallmark's LLM case names a disclosed mixed-quantization profile,
`y-attnout-w12`. The classifier exports specify integer graphs and thresholds.
The proofs bind those exact arithmetic choices. They do not prove that every
input would receive the same answer from the original floating-point network.

## Integrity and hiding are separate

A proof of a correct computation does not automatically hide the weights,
prompt or witness. Hallmark's current research path focuses on integrity.
Its published classifier weights and synthetic examples are public, and the
LLM backend has no witness-hiding claim.

Likewise, an execution proof does not establish hardware provenance or show
that nothing else ran. Read [MVP scope](../MVP.md) before extending a working
fixed case into a broader claim.

## Check your understanding

??? question "A valid classifier proof returns block. Did verification fail?"

    No. The proof can establish that the classifier correctly computed a block
    verdict. Proof validity and classifier approval are separate outcomes.

??? question "The prover supplies a model hash. Is that sufficient enrollment?"

    No. The caller needs an expected identity from an independently trusted
    source. Accepting whatever identity the prover supplies lets it choose the claim.

Continue with [read a proof statement](read-a-proof.md).
