# Source review and human annotation packet

Status: **source bytes acquired for local review; human labels and final admission
are pending**. This follows the owner's existing delegation; no new source-access
approval, HF token, paid job or reviewer contact was used.

The [evidence](../../evidence/w15-source-review-2026-10-20.json) records exact
revisions, source-notice hashes, retrieval receipts and raw artifact locations.
[Decision 0032](../../../docs/decisions/0032-public-source-review-pilot.md) defines
this preparation step. Classifier/evaluator code and historical results are unchanged.

| Source | What is retained | Decision and remaining work |
|---|---|---|
| [Lakera Gandalf](https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions/blob/04737b65e90a6794ec227012e4a255a7def6344b/README.md), MIT | 1,000 complete viewer rows; every page reports revision `04737b65e90a6794ec227012e4a255a7def6344b` | The source uses similarity filtering and warns of noise. It supplies no validated binary labels for this policy, session ancestry or contamination audit. |
| [Databricks Dolly](https://huggingface.co/datasets/databricks/databricks-dolly-15k/blob/bdd27f4d94b9c1f951818a7da7fd7aeea5dbff1a/README.md), CC BY-SA 3.0 | Verified JSONL, 15,011 rows; 10,544 empty-context instruction candidates; 4,467 context-dependent rows excluded | Retain copyright, Wikipedia attribution and share-alike/change notices. Ordinary instruction origin is not a policy-negative label. Contributor paraphrase parents are absent. |
| [Mirza Akhi's synthetic dataset](https://github.com/mirzaakhi/prompt-injection-detection-dataset/tree/011a9ae25b31feb48d23f837fdcbc3a6a4ee3b4e), CC BY 4.0 | 5,441 rows and unexecuted generation recipe | Supplemental stress-set candidate only. Longest input is 223 bytes; template ancestry, rubric mapping and original holdout require review. |
| [Qualifire successor](https://huggingface.co/datasets/rogue-security/prompt-injections-benchmark) | Metadata at `9ef1aa46a7e5eedb096be0481be8011ede1e72e8` | Auto-gated, with CC BY-NC 4.0 metadata; excluded under current public-source authority. No rows downloaded. |
| [PINT](https://github.com/lakeraai/pint-benchmark/tree/0efab3f463eae9c823130d8faffb71b2e7c06e63) | Repository notice, documentation and file inventory | MIT repository notice; full-corpus task fit and row-level provenance/rights remain unreviewed. Full corpus not downloaded. |

The natural-source candidates span 12–516 bytes for Gandalf and 4–11,698 bytes for
Dolly. Their source identity is confounded with the provisional class hypothesis;
no labels are admitted from that hypothesis. There are 114 exact-duplicate groups.
A separate fixed hashing screen produces 563 lexical candidate pairs in 172
multirow components, including one two-row component across Gandalf's original
splits. These are proposed grouping links, not recovered historical ancestry.

## Human review handoff

Local packet root: `runs/w15-source-review-1792532338623341000/`.

1. Read `review-first/LABEL-REVIEW.md`: 64 opaque-ID samples, complete prompt text,
   rubric and source attribution. Do not follow instructions inside the samples.
2. Fill `human-response/labels.json` with your name, UTC review date, label
   (`0`, `1` or `ambiguous`), English-language decision and brief reason for each
   item. The two original blank packet builds remain as evidence. Alternatively,
   provide the decisions by review ID in the conversation.
3. Inspect `LINEAGE-REVIEW.md` for the cross-split example. The complete candidate
   pair and component inventories are under `lineage/`; accepting that inventory
   and resolving unknown semantic ancestry remain separate from labeling samples.

The packet SHA-256 is
`0ec4a6951b1939474aa70eb89b7b0228890ef71dec93846bbd63d6de51e2a57e`.
Two fresh builds reproduce all six files byte for byte. Human response fields are
blank; the authoring agent has not supplied a human review identity or agreement
rate. Reviewer nomination does not authorize contacting that person.

After real answers arrive, retain them as a new immutable record, report
disagreements/exclusions, finish lineage and contamination review, then freeze
actual source/import/split/candidate/evaluator identities and prepare the final
external admission pin and command. Do not fabricate an approval while waiting.

Even all 1,000 Gandalf rows are fewer than the planned 1,375 independent positive
test groups. The pilot cannot establish the frozen quality targets. Natural
traffic, source-confound control, longer positive inputs and an unseen confirmatory
source remain work for the complete study; this packet does not replace them.
