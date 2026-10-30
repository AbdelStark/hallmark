# Hallmark agent contract

Hallmark is research in a public repository. Read [research/STATE.md](research/STATE.md) first, then the document for the task below. Keep claims proportional to the evidence: a replay is software checking, an attestation needs genuine hardware evidence, and a ZK claim needs a real proof checked against independently enrolled inputs.

## Work loop

1. Inspect `git status --short` and preserve others' changes. Choose one open acceptance gate from STATE; state the hypothesis, baseline, mutable paths and pass/fail criterion.
2. For contracts, binding, arithmetic or proof adapters, read [SPEC](docs/SPEC.md). For data, models or training, read [ML-PLAN](docs/ML-PLAN.md) and [EVALUATION](docs/EVALUATION.md). For a research run, read [experiment workflow](.agents/workflows/experiment.md).
3. Run the smallest fixture first. Freeze dataset/splits, evaluation code, thresholds and baseline before measuring a candidate. Keep test data out of model and threshold selection.
4. Make the bounded change and test its failure modes. `make check` is the local gate; `make package-check` checks distribution. A core-only environment legitimately skips optional training; the train-extra CI job must run it.
5. Update STATE, the research ledger and the exact command/evidence pointers. Report failed and missing results. Finish only when the selected criterion passes or the missing dependency is explicit.

## Authority and resources

On 2026-10-20, the owner explicitly requested public repository visibility. Keep the repository public; change it to private only if the owner explicitly asks. This supersedes the earlier private-repository instruction.

Publication of additional private material, new collaborators, uploads of transcripts/checkpoints and ongoing schedulers require specific authority. The backlog mandate authorizes issue/PR bookkeeping. Keep fixtures local and harmless. Use the locked environment; no system-package installs or unreviewed model code.

Use the current [run authority](research/AUTHORITY.json), updated by the owner's 2026-10-20 approval. It permits licence-reviewed public assets and bounded local research, with HF Jobs as a conditional GPU fallback. Prefer the Mac; record exact inputs and consumed resources before each run. It is a declaration, not an OS sandbox. Unresolved source rights block that source, not unrelated implementation; preparation of hardware/reviewer options does not authorize procurement or contact.

Protocol/evaluation changes require a decision in `docs/decisions/`, updated conformance tests and owner review before prior results are reused. An optimizer changes its candidate only; dataset and evaluator changes start a new experiment identity. CODEOWNERS signals review ownership; it is not branch-protection enforcement.

Issue tracking, triage labels and domain docs follow [docs/agents](docs/agents/issue-tracker.md) ([labels](docs/agents/triage-labels.md), [domain](docs/agents/domain.md)).

## Completion and privacy

Store source/config/environment hashes and raw numeric results before prose. New runs use new directories; preserve failures. Data source, licence, purpose and approval travel with every record. Secrets, raw private transcripts, real checkpoints, local runs and credentials stay out of git. Public research sources may be fetched by topic; private design text and partner details never enter search queries or external-model prompts.

Use [research audit](.agents/workflows/audit.md) before scientific claims and [resume guide](docs/OPERATIONS.md) after interruption. Only the owner decides policy adoption, release and acceptable residual risk. Do not infer safety, completeness, hardware provenance or ZK from hashes or fixture checks.

For a code security review or full audit (trust boundaries, input handling, supply chain, CI), load the [`security-audit` skill](.agents/skills/security-audit/SKILL.md), vendored from Cloudflare under MIT ([provenance](.agents/skills/security-audit/PROVENANCE.md)). Full audits write outside the repository by default and run target code only in a network-off sandbox.
