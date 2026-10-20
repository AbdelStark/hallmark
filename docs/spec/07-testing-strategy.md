# Testing strategy

## Existing gate

`make check` validates the lock, formatting/lint, strict source typing, offline tests and local Markdown file links. `make package-check` builds and checks wheel/sdist plus an isolated installed CLI. The existing reference test compares 300 seeded ASCII examples to histogram arithmetic; it is useful software evidence, not an independent verifier.

Core-only checks may skip the optional training test. `make check-train` invokes
the train extra with one BLAS/OpenMP thread and `--require-train`. Every selected
training test must complete all three pytest phases successfully; zero selection,
skips, xfail/xpass and collection/setup-only execution fail. Negative subprocess
fixtures in `tests/test_train_gate.py` exercise the guard independently of the
training dependencies.

Core/package and required-train CI jobs cover CPython 3.12, 3.13 and 3.14 on Linux.
Local macOS results do not substitute for Linux hosted execution. Hosted checks
blocked before steps run are recorded as unavailable. CI has no privileged
integration job; see [operations](../OPERATIONS.md#local-gates) for that boundary.

## Required layers

| Layer | Required cases | Evidence |
|---|---|---|
| Contract/unit | Duplicate keys, bool/int distinction, invalid UTF-8, wrong length/version, noncanonical CBOR, integer extrema, domain separation | Fixed bytes and expected result/code |
| Generated arithmetic | Seeded boundary cases across empty/one/exact/max-plus-one lengths, negative values, halfway rounding, padding and late positive chunks | Independent formula comparison with seed and count |
| ML | Group/descendant leakage, frozen data mutation, no benign calibration, threshold ties, missing denominator, insufficient power, resumed run identity | Rejected mutation or exact expected counts |
| Proof | Real valid proof; mutate each public input/key/setup/constraint-sensitive boundary; omitted chunk and field alias | Verifier rejects every invalid case; mock results excluded |
| Hardware | Genuine accepted evidence; stale/revoked/debug/wrong measurement/key/device/nonce, swapped model file and bypass attempt | Real verifier code plus collateral and expected rejection |
| Composition | Valid B1/B2, mismatched transcript, forged native pass, missing classifier, replay, retirement, unknown mode, conflicting verdict | Complete bundle and reason code |
| Lifecycle | Concurrent duplicate, crash at each write, disk full, timeout, restart, expiry, key deletion | No partial ready bundle or unauthorized release |
| Distribution/docs | Isolated install, absent optional extras, schema snapshot changes, local anchors/requirement coverage, secret fixture exclusion | Build and documentation gates |

Each new security branch needs a negative case. Property tests complement fixed cross-language vectors; they do not replace them. Do not introduce a property-testing dependency solely to run deterministic generated loops.

## Independent verifier and corpus

The separate [native MLP vectors](../../fixtures/wire/integer-mlp-v1.json) check
every intermediate layer against explicit numeric expectations; 60 seeded cases
also compare a direct byte-sum/division formula. Boundary tests cover signed
extrema, negative halfway rounding, masked padding, UTF-8 tails, partial-sum
overflow and execution caps. These tests are native arithmetic evidence, not a
proof or the independent verifier. They preserve the frozen W33 corpus unchanged.

The first [frozen corpus](../../tests/vectors/v1/corpus.json) contains 156 executable
component vectors and 32 unavailable genuine-evidence obligations. The source
snapshots, exact pin, mutation ancestry, full outcome comparison and migration
rules are fixed in [decision 0013](../decisions/0013-frozen-conformance-corpus.md).
`make check-conformance` explicitly selects software scope and self-tests a wrong
expectation and missing evidence. It is included in `make check`; the default
script scope still exits 3 for the unavailable cases. A passing software target
does not satisfy INV-CONFORMANCE for the full system or independent comparison.

Publish only approved harmless vectors under `tests/vectors/v1/`, with `case_id`, input bytes/hashes, external trust/request/time, expected claim status/code, evidence class and mutation parent. One mutation per case isolates the failed obligation; combined adversarial cases supplement it. Genuine hardware evidence and real checkpoints stay in approved local evidence storage, referenced by digests rather than committed indiscriminately.

The second verifier lives under `independent/`, shares no parser, arithmetic, transcript/token-binding or policy implementation with `src/hallmark`, and is developed from these specs and vectors. It may use the qualified proof library, with that common dependency disclosed; it is not independent evidence of proof-system soundness. Its dependency graph and provenance are reviewed. Differential comparison checks accepted/rejected status, codes, input digests and integer results on all corpus cases.

**INV-CONFORMANCE:** the valid corpus passes and every invalid corpus case is rejected for its specified reason. Skips, unavailable hardware and mock proofs cannot count as passed cases.

## Acceptance commands

Current commands remain valid. Target commands must be added with the corresponding implementation:

```text
make check
make package-check
make check-spec
make check-conformance
make check-independent
hallmark qualify PROTOCOL --output FRESH_DIRECTORY
```

`check-conformance` runs offline vectors and clearly separates real-evidence cases requiring local inputs. `check-independent` runs the independent executable against the same frozen corpus. Gated hardware/proof execution requires a pinned protocol and approved host; it is never silently triggered by ordinary CI or a PR.
