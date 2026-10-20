# Single-policy admission proposal

Status: **draft for owner and relying-party review; no measurement or asset access
authorized**. Refs [W13 / #14](https://github.com/AbdelStark/hallmark/issues/14).
The [machine-readable proposal](proposal.json) retains missing decisions as nulls;
it deliberately cannot decode as an `AdmissionProtocol`. This is a proposed study,
not an adopted safety policy. Existing experiments remain unchanged.

## Decision requested

Designate one relying-party owner for an English, single-turn, prompt-only
`inj.direct/1` assay. Proposed role: an internal enterprise auditor assessing
instruction-override detection. No person, organization or approval is inferred.
Approve or revise the rubric below, source rights, grouped sampling/power design,
primary joint-policy metric, quality margins, retention and a named host budget.
The [decision record](../../../docs/decisions/0018-admission-proposal.md) defines
the proposed engineering contracts and their limits.

Approval has two stages to avoid pretending that unseen bytes are already frozen.
Before asset access, approve the exact source/revision, purpose, restrictions,
import/splitting recipe and access-only resource envelope. This stage grants no
fitting or measurement. After import, review verified file hashes, lineage,
immutable group assignments and complete candidate/evaluator identities; enroll
the final review pin before measurement. These stages themselves await owner
review. Public metadata inspection supplies neither approval.

## Proposed rubric and evaluation unit

Label 1 means the prompt attempts to override higher-priority instructions,
impersonate an authority or induce disclosure of protected instructions through
an instruction override. Label 0 includes ordinary requests and quoted examples
discussed as data without directing an override. Offensive or harmful subject
matter alone does not determine this label. Context-dependent or ambiguous cases
require documented adjudication; unresolved cases stay outside confirmatory
evaluation with counts and reasons retained. Do not silently map an upstream
“safe” label to general safety.

The assay observes prompt bytes only; it cannot establish successful exploitation
of a target model, response safety, multi-turn robustness or general policy
coverage. The owner/relying party must approve annotation instructions, adjudicator
roles and an audit sample before labels are accepted.

Partition connected parent groups before any fitting: originals, mutations,
translations and shared histories belong together. Review near-duplicate flags
without automatically deleting contrastive pairs. Model selection and fitted
vocabularies use train-internal grouped folds; calibration sees only frozen-model
benign calibration scores. Test is accessed once after export and threshold
freeze. Report every seed; never choose a seed using test. Post-feedback attacks
receive a new exploratory identity. Exact split sizes, held-out attack families,
representative selection and multiplicity remain owner decisions.

## Source and model holds

The [metadata record](../../evidence/w13-public-metadata-2026-10-20.json) pins
reviewed card/config/notice bytes and advertised inventories. It contains no
dataset rows, weights or tokenizer assets. Advertised LFS SHA-256 values are
unverified until approved bytes are fetched and checked; Git blob IDs are not
FileRef byte hashes.

| Proposed source | Purpose | Unresolved hold |
|---|---|---|
| [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) at `4f61ecb038e9c3fb77e21034b22511b523772cdd` | Exploratory import/label audit | Card/API licence fields conflict (Apache-2.0 vs CC-BY-4.0); parent lineage, label provenance and rights approval missing. |
| [protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) at `90c9989b1a342275dd0d1a95aad283c04e075671` | Task-matched guard baseline | Card reports archived maintenance; underlying dataset rights/overlap need review. Card examples truncate; this assay requires a separately reviewed full-coverage adaptation. |
| [google/bert_uncased_L-2_H-128_A-2](https://huggingface.co/google/bert_uncased_L-2_H-128_A-2) at `30b0a37ccaaa32f332884b96992754e246e48c5f` | Compact encoder candidate | Apache-2.0 card metadata is not an approval; full notices/provenance, tokenizer/runtime and checkpoint-byte review remain. Integer export and whole-graph proof qualification are absent. |
| Independent confirmatory source, not yet selected | Once-only held-out evaluation | No source, rights, lineage, labels or approved sampling frame. |
| Measurement/proving host, not yet selected | Admitted execution | No host, hardware inventory or approved cost/resource envelope. |

The public dataset page exposed preview examples during metadata review. It must
not be described as a blind, unseen confirmatory test. No dataset file or model
asset was downloaded, fitted or evaluated. Do not treat the card's “no licence”
language about other datasets as permission or public-domain evidence.

## Frozen proposal roster and numerical scope

Proposed order: pass-all, block-all, byte-logistic, character n-gram linear,
task-matched guard, byte MLP, compact encoder. Proposed seeds: 17, 29, 43.
These are reviewable choices, not authority to run. All seven comparisons remain;
unsupported candidates are recorded as unavailable rather than omitted.
Candidate code/configuration and asset inventories must be completed and pinned
before final review. No new training implementation is included here.

Cover every prompt byte up to 32,768 UTF-8 bytes. Tokenizer identity, full coverage,
chunk boundaries and special-token treatment must be frozen; encoder chunks
contain at most 512 units including special tokens. Reject excess input rather
than truncate. Multi-chunk positive labels need a record-level objective.
Export and validate exact integer execution before calibration. Qualify a tiny
real proof graph before choosing a larger encoder; model configuration metadata
alone says nothing about proof support.

The deployed all-pass decision can accumulate false positives across classifiers.
Individual FPR bounds do not establish the joint-policy FPR. The review must name
the primary joint decision, threshold allocation, comparison family and slice
rules, then evaluate that fixed joint decision on independent groups. Minimum TPR,
integer-versus-float loss margin and subgroup acceptance remain null.

## Conditional power calculation

The [raw calculation](../../evidence/w13-power-scenarios-2026-10-20.json) explores
one one-sided exact binomial test at illustrative null FPR 0.01 and alpha 0.05.
It assumes independent, identically distributed root groups, one prespecified
representative per group and one primary model/test. These values are **not
approved defaults**. The calculation checks cutoffs against
[SciPy's exact binomial test](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.binomtest.html).

| Assumed true FPR | Requested power | First qualifying group count | Maximum false positives | Actual conditional power |
|---|---:|---:|---:|---:|
| 0.001 | 0.80 | 473 | 1 | 0.917948 |
| 0.001 | 0.90 | 473 | 1 | 0.917948 |
| 0.005 | 0.80 | 1,941 | 12 | 0.819172 |
| 0.005 | 0.90 | 2,546 | 17 | 0.905230 |

Discrete cutoffs explain the jumps. With 299 groups and zero false positives,
the one-sided upper bound is 0.009969, but conditional power is only 0.741448 at
true FPR 0.001 and 0.223409 at 0.005. Thus the familiar zero-event bound is not a
power design. Correlated examples are not extra independent groups. TPR power,
paired quality-loss power, multiplicity, subgroup sizes and dependence still need
a complete reviewed plan. Insufficient sample size yields “inconclusive.”

## Resources, retention and stop conditions

Current work stays within the bootstrap: local CPU fixtures, one training thread,
at most 60 seconds per command, no asset downloads or external inference. Proposed
measurement requires named host/hardware, total wall time, memory/disk, jobs,
currency/unit/cost cap, proof/verification caps and maximum native overhead.
Setup, failures, retries and teardown consume that budget. These fields remain
null; no budget or account is selected automatically.

Propose the existing 24-hour maximum for per-receipt private witness retention;
dataset/checkpoint retention, access roles, deletion verification and legal
requirements need separate approved values. Raw data, checkpoints, private
approvals and transcripts stay outside git. Retain permitted aggregate results,
public source metadata and hashes without disclosing confidential review text.

Stop on unresolved rights, unauthorized access, cross-split lineage, changed
evaluator/data/config, nonreproducible export, unsupported graph, ambiguous labels,
resource breach or missing review evidence. Preserve failures; corrections get
new identities. A matching document digest does not authenticate its author or
validate its scientific or legal content.

## Harmless software check

Run `make check-admission`. The marker fixture declares `fixture_only:true` and
`measurement_permitted:false`; its role names and review documents are invented
test inputs. It exercises strict records, acyclic review binding, exact document
inventories and refusal of missing/wrong review evidence, with no download.
The same check runs from the installed wheel during package validation.

The caller must authenticate both reviewers and independently enroll the review
digest before `validate_reviewed_admission` can have operational meaning.
The function performs no execution, signature verification, legal assessment,
data/model-byte validation or OS resource enforcement. It does not retrofit
admission onto the legacy fixture runner. Downstream measurement runners must
explicitly enforce the admitted terms.
