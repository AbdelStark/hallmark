# Editorial Decision Package

## Calibration Resolution

`calibration_status: NOT_CALIBRATED`

Current runtime boundary: this package is not upgraded from a candidate or prose-named profile. `PROFILE_MEASURED` remains unavailable until a closed profile artifact and replay validator bind the exact target fields to the completed panel's `execution_topology_sha256`.

## Manuscript Information

- **Title**: Proofs, Attestation and Logs: What a Verifier Must Trust to Know a Safety Classifier Ran
- **Manuscript ID**: hallmark-paper-round-1 (panel ID); manuscript copy `runs/paper-panel/manuscript.md`, SHA-256 `56e022570dff8eca33f6b62f641d83db96b98fe115e9d5b53917ffee51ae7ad5`
- **Submission Date**: not provided
- **Decision Date**: 2026-11-02
- **Review Round**: Round 1
- **Contract**: `reviewer/reviewer_full/v2` (mode `reviewer_full`, `panel_size` 5, Schema 13.2 sprint contract)
- **Venue binding**: `criteria_binding_unavailable`. No venue, track or article type is bound. This package makes no venue-alignment claim. D6 is read on originality and significance alone, as the Journal-Fit Reviewer's card states.

## Review Panel Provenance (#540/#740)

- **Typed artifact**: `runs/paper-panel/provenance.json` (`review-panel-provenance/1.0`, validated PASS by the dispatching layer)
- **Artifact SHA-256**: `110da2739e5fdf33d49d988aef2c1c4c131007d3e45b850bc8df664d550015c4`
- **Panel ID**: `hallmark-paper-round-1`
- **Contract SHA-256**: `e9712090d2469fea15a37b8e22d4e137afbcb2bf38d5789939c5df56738ef7af`
- **Normalized manifest SHA-256**: `b435386b5ccd13ed6d6fc5bb091f123af45a539238c668b4a954a4e15dc04201`
- **Execution topology SHA-256**: `ba4de2cf08761c7f478a4d22252e1c234f07e2b96cfc887197ff296a1c11b059`
- **Fresh-context scope**: `within_panel_attempt_only`. This scope does not compare retries or earlier rounds.

| Seat | Role ID | Actor type | Context ID | Peer outputs visible | Model family | Provider | Human reviewer ID |
|---|---|---|---|---|---|---|---|
| EIC | eic | model | subagent-eic-phase2 | false | claude | anthropic | null |
| R1 | methodology | model | subagent-methodology-phase2 | false | claude | anthropic | null |
| R2 | domain | model | subagent-domain-phase2 | false | claude | anthropic | null |
| R3 | perspective | model | subagent-perspective-phase2 | false | claude | anthropic | null |
| DA | da | model | subagent-da-phase2 | false | claude | anthropic | null |

| Provenance axis | Status |
|---|---|
| Role-separated | true |
| Within-panel invocation-context separation | true |
| Blind to peer outputs | true |
| Model-family distinct | false |
| Provider distinct | false |
| Human-reviewer distinct | false |

- **Binary independence claim**: not computed (`independence_claim: not_computed_from_personas`). Role and persona diversity establish only `role_separated`. This panel is not described as independent.
- **Correlated-error disclosure** (required, reason `same_model_family`): "All model-executed review seats used one model family; role separation does not remove correlated-error risk."

A practical consequence for the author: where the seats agree, for example on the arithmetic that four seats recomputed (pair counts, FRI bit figures, mutation totals), that agreement comes from one model family and is not independent corroboration.

## Pre-synthesis checks

- **Panel cardinality**: 5 of 5 Phase 2 reports are usable (EIC, R1, R2, R3, DA). There is no `[PANEL-SHRUNK]` and no substitute score.
- **Role binding**: each report declares `contract_role` once, matching its dispatch role (eic, methodology, domain, perspective, da). Every score outside a seat's eligible dimensions is `not_assessed`.
- **Unbound-run disclosure**: all five Phase 1 cards carry the exact line `criteria_binding_unavailable`. Four of the five Phase 2 cards repeat it. The domain Phase 2 card (`domain.phase2.md`) does not repeat the token, but it makes no venue-alignment claim and scores D6 `not_assessed`. This is recorded here as a conformance observation. It is not a score, failure condition or verdict, and the card was not altered.
- **Manuscript as data**: every seat reports that the manuscript contains no text addressed to reviewers. The Phase 0 card notes that the AI-Use Disclosure mentions earlier simulated review rounds. That was weighed as a disclosure, and this synthesis did not anchor on those rounds.
- **Cross-model decision check (#518)**: not run, because `ARS_CROSS_MODEL` is unset. Behaviour is unchanged.

---

# Part 1: Editorial Decision Letter

Dear Author,

Thank you for submitting "Proofs, Attestation and Logs: What a Verifier Must Trust to Know a Safety Classifier Ran". Five role-separated review seats assessed it, including a Journal-Fit Reviewer role. Their execution provenance is reported above and is not reduced to a binary independence claim. No venue is bound, so nothing below assesses venue fit.

## Mechanical synthesis (v3.6.2 sprint contract)

### Step 1: Role-scoped scoring matrix

| Dimension | Priority | Eligible seats | Assessed scores | Verdict (worst assessed) |
|---|---|---|---|---|
| D1 methodology_rigor | mandatory | methodology | R1 = warn | warn |
| D2 domain_accuracy | mandatory | domain | R2 = warn | warn |
| D3 argumentative_coherence | mandatory | da, methodology | DA = warn, R1 = warn | warn |
| D4 cross_disciplinary_relevance | high | perspective | R3 = warn | warn |
| D5 writing_and_structure | normal | eic | EIC = warn | warn |
| D6 venue_fit_and_contribution | mandatory | eic | EIC = warn | warn |

No seat scored `block`, so no `block_class` was declared and no fatal flag exists. No seat abstained, every dimension was assessed, and no card carries a `## Scoring Plan Dissent`.

### Step 2: Failure conditions

| ID | Severity | Quantifier | Expression | Evaluation | Fired |
|---|---|---|---|---|---|
| F1 | 95 | any | any mandatory dimension has a fatal block | No fatal block on D1, D2, D3 or D6 | false |
| F2 | 90 | any | any mandatory dimension scores 'block' | D1, D2, D3 and D6 are all warn | false |
| F3 | 70 | majority | two or more mandatory dimensions score 'warn' or worse | The per-dimension majority holds on D1 (n=1, the owner R1 is warn), D2 (n=1, the owner R2 is warn), D3 (n=2, both DA and R1 are warn) and D6 (n=1, the owner EIC is warn). That is 4 mandatory dimensions, which is at least 2 | **true** |
| F4 | 60 | any | any high-priority dimension scores 'block' | D4 is warn | false |
| F5 | 40 | any | any dimension scores 'warn' or worse | All six dimensions are warn | **true** |
| F0 | 10 | all | every dimension scores 'pass' | No dimension passes | false |

### Step 3: Precedence and audit lines

F3 (severity 70) has the highest severity among the fired conditions F3 and F5. Its action applies. The DA's `#### CRITICAL` table is empty, so the DA adjudication list is empty.

```
dimension_verdicts: [D1=warn, D2=warn, D3=warn, D4=warn, D5=warn, D6=warn]
fired_conditions: [F3, F5]
da_critical_adjudications: []
editorial_decision=major_revision
```

## Decision: Major Revision

## Reviewer Summary

The Schema 13.2 cards carry dimension scores and per-finding confidence. They state no overall recommendation, and none is invented here.

| Reviewer | Role | Dimension scores | Findings (Major / Minor) | Confidence |
|---|---|---|---|---|
| Journal-Fit Reviewer (EIC) | Field-general SoK handling editor, unbound | D5 warn, D6 warn | 1 / 9 | per-finding, 3 to 5 |
| R1 | Formal security modelling and SoK method | D1 warn, D3 warn | 2 / 6 | per-finding, 3 to 4 |
| R2 | Transparent proof systems, confidential computing, SNARK-vulnerability literature | D2 warn | 0 / 15 | per-finding, 2 to 5 |
| R3 | Audit and assurance practice, AI governance | D4 warn | 2 / 9 | per-finding, 2 to 4 |
| Devil's Advocate | Fixed adversarial seat | D3 warn | 0 Critical / 3 Major (+5 unbanded minor issues) | per-finding, 3 to 4 |

## Consensus Analysis

### Step 1b: Weakness sub-claim inventory

Positions are counted only over the four non-DA seats. The DA is listed separately in the last column and never enters a consensus count. Severity and confidence are carried over from each finding unchanged. `n-m` means not-mentioned, which is silence and not opposition.

| SC | Parent weakness | EIC | R1 | R2 | R3 | Severity (transported) | Confidence | Evidence pointer | DA | Disposition |
|---|---|---|---|---|---|---|---|---|---|---|
| SC-1 | EIC W1 contribution framing | raised | n-m | n-m | n-m | major | 4 | EIC W1 | — | single-reviewer |
| SC-2 | EIC W1: headline the integrity/auditor divergence as core | raised | n-m | n-m | disputed (R3 W1: not constructed as an order) | major (EIC) / major (R3) | 4 / 4 | EIC W1; R3 W1 | — | SPLIT (direction) |
| SC-3 | EIC W2 novelty paragraph leads with artifact priority | raised | n-m | n-m | n-m | minor | 4 | EIC W2 | — | single-reviewer |
| SC-4 | EIC W3 cost material in §5 / Table 4 | raised | n-m | n-m | n-m | minor | 4 | EIC W3 | — | single-reviewer |
| SC-5 | EIC W4 symbol T overloaded | raised | n-m | n-m | n-m | minor | 5 | EIC W4 | — | single-reviewer |
| SC-6 | EIC W5 pair-count sentence | raised | n-m | n-m | n-m | minor | 3 | EIC W5 | — | single-reviewer |
| SC-7 | EIC W6 class numbering | raised | n-m | n-m | n-m | minor | 4 | EIC W6 | — | single-reviewer |
| SC-8 | EIC W7 repository flags, "qualified" undefined | raised | n-m | n-m | n-m | minor | 4 | EIC W7 | — | single-reviewer |
| SC-9 | EIC W8 competing-interest scope | raised | n-m | n-m | n-m | minor | 3 | EIC W8 | — | single-reviewer |
| SC-10 | Per-strand search counts not reported | raised (W9) | raised (W4) | n-m | n-m | minor (EIC) / major (R1) | 3 / 3 | EIC W9; R1 W4 | — | SPLIT (severity) |
| SC-11 | EIC W10 figures not rendered in the review copy | raised | n-m | n-m | n-m | minor | 3 | EIC W10 | — | single-reviewer |
| SC-12 | R1 W1: granularity sensitivity worked out for K only, not P/D | n-m | raised | n-m | n-m | major | 4 | R1 W1 | — | single-reviewer |
| SC-13 | Result 5 / abstract "replay needs less trust than the proofs" stated beyond the universe's support | n-m | raised (W1) | raised (W1) | n-m | major (R1) / minor (R2) | 4 / 4 | R1 W1; R2 W1 | M1 corroborates | SPLIT (severity) |
| SC-14 | R1 W1: §7.2's claim about granularity-dependent edges is inaccurate | n-m | raised | n-m | n-m | major | 4 | R1 W1 | M1 corroborates | single-reviewer |
| SC-15 | R1 W2 universe not closed (auditors, third party) | n-m | raised | n-m | n-m | minor | 4 | R1 W2 | — | single-reviewer |
| SC-16 | R1 W3 adversary strategies not applied per class | n-m | raised | n-m | n-m | minor | 4 | R1 W3 | — | single-reviewer |
| SC-17 | R1 W4 query strings and sources not reported | n-m | raised | n-m | n-m | major | 3 | R1 W4 | — | single-reviewer |
| SC-18 | R1 W4: the §6 negative novelty statement rests on an unreproducible search | n-m | raised | disputed (W15: "defensible given the searches described in §3") | n-m | major (R1) / minor (R2) | 3 / 2 | R1 W4; R2 W15 | — | SPLIT (existence) |
| SC-19 | R1 W5 reading-depth denominators | n-m | raised | n-m | n-m | minor | 3 | R1 W5 | — | single-reviewer |
| SC-20 | R1 W6 LLM replay claim from one reproduction | n-m | raised | n-m | n-m | minor | 3 | R1 W6 | — | single-reviewer |
| SC-21 | R1 W7 exp-R1 provenance and timing repetition | n-m | raised | n-m | n-m | minor | 4 | R1 W7 | — | single-reviewer |
| SC-22 | R1 W8 failure-record claim backed for two classes | n-m | raised | n-m | n-m | minor | 3 | R1 W8 | — | single-reviewer |
| SC-23 | R2 W1: replay relies on hash K when weights are identified by digest | n-m | n-m | raised | n-m | minor | 4 | R2 W1 | M1 corroborates (major) | single-reviewer |
| SC-24 | R2 W2 attestation appraisal parameters | n-m | n-m | raised | n-m | minor | 4 | R2 W2 | — | single-reviewer |
| SC-25 | R2 W3 class 4 attack record thin on attestation forgery | n-m | n-m | raised | n-m | minor | 3 | R2 W3 | — | single-reviewer |
| SC-26 | R2 W4 GKR soundness term omitted | n-m | n-m | raised | n-m | minor | 3 | R2 W4 | — | single-reviewer |
| SC-27 | R2 W5 Fiat–Shamir public-input absorption unstated | n-m | n-m | raised | n-m | minor | 4 | R2 W5 | — | single-reviewer |
| SC-28 | R2 W6 patched SASH verifier; "shape roots" | n-m | n-m | raised | n-m | minor | 4 | R2 W6 | minor issue 2 corroborates | single-reviewer |
| SC-29 | R2 W7 "spares a verifier the weights" needs a qualifier | n-m | n-m | raised | n-m | minor | 4 | R2 W7 | minor issue 3 corroborates | single-reviewer |
| SC-30 | R2 W8 abstract credits logs with G | n-m | n-m | raised | n-m | minor | 4 | R2 W8 | — | single-reviewer |
| SC-31 | R2 W9 conjecture status | n-m | n-m | raised | n-m | minor | 3 | R2 W9 | — | single-reviewer |
| SC-32 | R2 W10 cite [A27] with [A40] | n-m | n-m | raised | n-m | minor | 3 | R2 W10 | — | single-reviewer |
| SC-33 | R2 W11 "strictly logarithmic" in the IOP model | n-m | n-m | raised | n-m | minor | 4 | R2 W11 | — | single-reviewer |
| SC-34 | R2 W12 hiding vs confidentiality from the host | n-m | n-m | raised | n-m | minor | 4 | R2 W12 | — | single-reviewer |
| SC-35 | R2 W13 limb decomposition stated as achieved | n-m | n-m | raised | n-m | minor | 4 | R2 W13 | — | single-reviewer |
| SC-36 | R2 W14 one attack, three names | n-m | n-m | raised | n-m | minor | 5 | R2 W14 | — | single-reviewer |
| SC-37 | R2 W15 LLM-prover coverage (zkGPT) | n-m | n-m | raised | n-m | minor | 2 | R2 W15 | — | single-reviewer |
| SC-38 | R3 W1: Table 2 assigns no trust sets to G/T; "order" not constructed | n-m | n-m | n-m | raised | major | 4 | R3 W1 | — | single-reviewer |
| SC-39 | R3 W1: "cares about most" unsupported by cited audit literature | n-m | n-m | n-m | raised | major | 4 | R3 W1 | — | single-reviewer |
| SC-40 | R3 W2: pre-release log needs a party other than O to keep time | n-m | n-m | n-m | raised | major | 4 | R3 W2 | — | single-reviewer |
| SC-41 | R3 W2: release time must be evidenced to the verifier (receipt) | n-m | n-m | n-m | raised | major | 4 | R3 W2 | — | single-reviewer |
| SC-42 | R3 W3 sampling detection depends on block base rate | n-m | n-m | n-m | raised | minor | 4 | R3 W3 | — | single-reviewer |
| SC-43 | R3 W4 class 4 capture provenance needs the user channel inside the boundary | n-m | n-m | n-m | raised | minor | 3 | R3 W4 | — | single-reviewer |
| SC-44 | R3 W5 streaming caveat on Table 2 G/T | n-m | n-m | n-m | raised | minor | 4 | R3 W5 | — | single-reviewer |
| SC-45 | R3 W6 honest-enroller deployment reading | n-m | n-m | n-m | raised | minor | 3 | R3 W6 | — | single-reviewer |
| SC-46 | R3 W7 Code of Practice read inconsistently | n-m | n-m | n-m | raised | minor | 3 | R3 W7 | — | single-reviewer |
| SC-47 | R3 W8 roles not mapped to regulatory roles | n-m | n-m | n-m | raised | minor | 3 | R3 W8 | — | single-reviewer |
| SC-48 | R3 W9 §5.3 lacks a governance-reader takeaway | n-m | n-m | n-m | raised | minor | 4 | R3 W9 | — | single-reviewer |
| SC-49 | R3 W10 prompt privacy in retained evidence | n-m | n-m | n-m | raised | minor | 2 | R3 W10 | — | single-reviewer |
| SC-50 | R3 W11 "receipt" framing invites misuse | n-m | n-m | n-m | raised | minor | 3 | R3 W11 | — | single-reviewer |
| SC-51 | DA M1: with K charged to replay, Result 4 and the §4.2 counts change | — | — | — | — | major | 4 | DA M1 | raised | DA single-verifier |
| SC-52 | DA M2: "computed" shifts meaning; Skip vs Misreport | — | — | — | — | major | 4 | DA M2 | raised | DA single-verifier |
| SC-53 | DA M3: RAILS delta follows from τ = U; attribution not recorded | — | — | — | — | major | 3 | DA M3 | raised | DA single-verifier |
| SC-54 | DA minor 1: no enrolled transform from R to the model's tokens | — | — | — | — | minor [SEVERITY-SOURCE: DA "Minor issues" heading] | not stated [CONFIDENCE-SOURCE: none on the card] | DA minor issue 1 | raised | DA single-verifier |
| SC-55 | DA minor 4: classifier proofs bind the response, so an input-rail proof cannot precede Y | — | — | — | — | minor [SEVERITY-SOURCE: DA "Minor issues" heading] | not stated | DA minor issue 4 | raised | DA single-verifier |
| SC-56 | DA minor 5: request binding vs hiding for the user-as-verifier | — | — | — | — | minor [SEVERITY-SOURCE: DA "Minor issues" heading] | not stated | DA minor issue 5 | raised | DA single-verifier |

Decomposition notes: R1 W1 is split into SC-12, SC-13 and SC-14. R2 W1 is split into SC-13 and SC-23. R1 W4 is split into SC-10, SC-17 and SC-18. R3 W1 is split into SC-38 and SC-39 (and is the dispute on SC-2). R3 W2 is split into SC-40 and SC-41. No sub-claim was introduced that a seat did not raise.

### Points of Agreement (Consensus)

**[CONSENSUS-4] and [CONSENSUS-3] on weaknesses: none.** No weakness sub-claim is raised by three or four of the non-DA seats. Two sub-claims are raised by two seats (SC-10 and SC-13), and both became SPLITs because the seats gave them different severities.

**Agreement on strengths** (reported for completeness; strengths create no roadmap obligation):

- [CONSENSUS-3] The S versus S′ = S ∧ G ∧ T split is the paper's clearest and most transferable idea: EIC S1, R2 S7, R3 S1. R1 is silent on it as a strength.
- [CONSENSUS-3] The proofs-over-attestation edge is correctly made conditional: EIC (Review Body, "the conditional proofs-over-attestation edge" as citable core), R1 S2, R2 S2. R3 is silent. The DA concurs ("What the manuscript does well").
- Corroborated (two seats): Appendix A's rejection evidence is honestly scoped (R1 S6, R2 S5). The §4.2 pair counts and §5.3 bit figures recompute (R1 S3 and Review Body, R2 S1; the DA also recomputed them). Given the same-model-family disclosure, this recomputation agreement is not independent corroboration.

**Panel-level agreement (all four non-DA seats):** no finding reaches the block level, and the problems can be fixed without overturning the central result. EIC: "The repair is to reframe and rebalance, not to add analysis, so it is not block". R1: "None of them overturns the main result". R2: "No finding needs re-analysis or new data". R3: "can be fixed in revision without touching the integrity analysis". The DA agrees that the thesis "survives both objections". This agreement bounds the revision. It does not soften the fired condition's action.

### Points of Disagreement

**Disagreement 1 (SC-2): how to present the integrity order versus the auditor's order**
- **EIC view (W1)**: the citable core includes "the gap between the integrity order and the order an auditor needs". The contribution list and abstract should be rewritten around it and the other original insights.
- **R3 view (W1)**: the "auditor's order" is "asserted, not constructed". Table 2 assigns no trust elements to G or T, so "the word 'order' promises a comparison the paper does not supply". The minimum remedy is to call it an "auditor's view" and drop "reverses". The stronger option is to construct τ_G and τ_T.
- **Disagreement type**: direction (the two remedies pull in opposite directions on prominence).
- **Editor's resolution**: the two positions are compatible once ordered. Contribution 3 may be headlined as an order only if the revision constructs it (R3's stronger option, REV-37). Otherwise it is headlined as an auditor's view, and "reverses" is dropped. The author chooses which path to take. Either way, the abstract must not promise an order the body does not build.
- **Resolution rationale**: on expertise, R3 is the audit-practice seat and EIC is the contribution-framing seat. EIC's card does not claim that the auditor's order is constructed; it judges prominence only. R3's evidence (Table 2's qualitative cells, §4.4 "Table 2 reverses much of Figure 1.") stands unrebutted, so it governs what may be claimed. EIC's point governs how prominently the claim is placed.

**Disagreement 2 (SC-10): severity of the missing per-strand search counts**
- **EIC view (W9)**: Minor. Readers cannot tell how representative the few systems per class are. EIC states "method adequacy is D1's call".
- **R1 view (W4)**: Major. Neither the search terms nor any counts are reported, and two claims depend on the procedure: the completeness of the class list and the §6 negative novelty statement.
- **Disagreement type**: severity.
- **Editor's resolution**: obligation `must_fix` (REV-10). Both severities are carried on the item unchanged.
- **Resolution rationale**: on expertise, the procedure is a D1 (methodology) matter, and the EIC card explicitly defers to that seat. The remedies are the same (report counts per strand and per stage), so only the severity differed.

**Disagreement 3 (SC-13): severity of the overstatement in "replay needs less trust than the proofs"**
- **R1 view (W1)**: Major. If P is split by where the implementation lives, replay and proofs become incomparable, "Result 5 then disappears", and so does the abstract's claim.
- **R2 view (W1)**: Minor. Only the hash part of K is at issue, and "The substance survives". The text should say which reading makes "less trust" strict.
- **Disagreement type**: severity. Both seats agree that the claim must be qualified.
- **Editor's resolution**: obligation `must_fix` (REV-13), with both severities carried on the item.
- **Resolution rationale**: evidence first. R2's Minor rating rests on the K mechanism alone and does not address R1's P-split argument. No card rebuts that argument, and R1 recomputed the inclusions under alternative partitions. The DA's M1 adds a third route by which the result changes. The requirement is a qualifier, not a choice of universe: the author decides which reading to put first (R1: "which universe to put first is the author's choice").

**Disagreement 4 (SC-18): whether the §6 negative novelty statement is adequately supported**
- **R1 view (W4)**: "a reader cannot re-run the search that supports it". The statement depends on an unreported procedure.
- **R2 view (W15)**: the bounded novelty statement is one "I find defensible given the searches described in §3".
- **Disagreement type**: existence. The two seats apply different criteria: R1 asks whether the search is reproducible, R2 whether the statement is plausible.
- **Editor's resolution**: both hold. The statement need not be retracted. It must point to the documented search that REV-16 and REV-10 produce, and if a documented re-run finds a qualifying system (R2 W15 names zkGPT as a candidate from recollection), the statement must be revised to match. Obligation: `should_fix` (REV-17), because the reporting work itself is already `must_fix` under REV-10 and REV-16.
- **Resolution rationale**: the evidence does not settle whether the search was complete. That part stays as unresolved dissent, and the panel does not claim to have resolved it. The documented search is what resolves it.

**Disagreement 5 (DA versus EIC, outside the consensus count): the RAILS delta**
- **EIC view (S2)**: the comparison with RAILS is "the right form for an SoK novelty claim", because it names the two places where the orders differ.
- **DA view (M3)**: the first of those differences "follows from the τ = U convention and from leaving attribution out of both tables". The paper's own gap 8 relies on attribution.
- **Editor's resolution**: the two views are not contradictory. EIC judges the form of the delta (explicit and checkable), and the DA judges its substance (convention-driven). The DA finding is retained as REV-50 (`must_fix`, Major, anchored to §6 and §7.1). The DA's confidence of 3 ("RAILS read only through the manuscript's account") is a scope disclosure and is not used to discount the finding.

A related non-conflict: R1 S3 confirms that the §4.2 counts reproduce from Table 1 as assigned, and DA M1 shows the counts change if K is charged to replay. These start from different premises and do not contradict each other. REV-48 asks the author to settle the premise.

## Decision Rationale

The decision follows mechanically from the contract. Every dimension scored warn and none scored block. F3 fired because four mandatory dimensions (D1, D2, D3 and D6) scored warn under each dimension's majority rule, and it outranks F5's minor-revision action. Its action, Major Revision, is applied as written and is not softened.

The cards explain why this is more than an accumulation of small edits. The Major findings sit on three mandatory dimensions. On D6, EIC W1 finds that the contribution framing foregrounds what the paper itself calls readouts. On D1 and D3, R1 W1 shows that Result 5 and the abstract's replay-versus-proof sentence depend on an unanalysed choice of granularity for P, which R2 W1 and DA M1 reach independently through K. R1 W4 finds that the literature search, on which completeness and the novelty statement rest, cannot be reproduced. The DA adds two coherence challenges: the shifting sense of "computed" (M2) and the attribution property the RAILS comparison leaves out (M3). On D4, which is high priority but outside F3, R3 W1 and W2 find that the auditor-facing material, the "auditor's order" and the pre-release-log composition, is asserted at a rigour below that of the integrity order.

A stricter decision is not supported. No seat declared a block or a fatal flaw. All four non-DA seats state that the central result survives. The DA has no Critical finding. A milder decision is not available, because F3 fired and the protocol forbids overriding it on post-hoc grounds. Two items (REV-12 and REV-48) require recomputing inclusions under alternative universes, and REV-37 may require a new table. Re-review should check those items first.

## Blocking Issues (immutable source order)

| Transport ref | Blocking issue | Source reviewer(s) | Evidence anchor | Resolving roadmap item |
|---|---|---|---|---|
| R1 | The contribution framing foregrounds what the paper calls readouts; the original insights are not the headline | EIC | text: §4.2 and §5 "Results 1 to 4 are readouts of Table 1, not discoveries" | REV-01 (with REV-02) |
| R4 | Granularity sensitivity is worked out for K only, while P and D carry Results 2 and 5 and the replay-versus-proof claim | R1 (DA M1 and R2 W1 by another route) | text: §4.1 "a correct implementation of C and M, whether in the verifier's code, a delegated program, a measured image or a circuit" | REV-12 (with REV-13, REV-22, REV-48) |
| R6 | The literature search cannot be reproduced from what is reported | R1 (EIC W9 on counts) | text: §3 "Each strand was searched on 2026-10-30 with public topic terms in web search and on primary pages" | REV-16 (with REV-10) |

---

# Part 2: Revision Roadmap

The roadmap is the reviewer-owned core only. Rows follow the fixed source order (seat order EIC, R1, R2, R3, DA, then finding ordinal, then sub-claim ordinal). That order is not a work ranking. Obligation class, severity and cost do not determine row order. The author records triage later in a separate sidecar; this core carries none.

**Machine artifact status.** The closed `revision-roadmap/1.0` JSON core is not emitted here. Its required `block_manifest_sha256` and the `B####` block ids for `proposed_targets[]` need a bound block manifest, and none exists in `runs/paper-panel/`. Inventing block ids would fabricate scope. The `base_draft_sha256` would be `56e022570dff8eca33f6b62f641d83db96b98fe115e9d5b53917ffee51ae7ad5`. Proposed targets are therefore given below as section locators. Once a manifest is bound, `scripts/revision_roadmap.py` should build the core from this table. Likewise, the Schema 6 package with the `review_panel_provenance` carrier is not emitted, and letter prose is not that carrier.

## Required Revisions (must_fix)

| Transport ref | Item | Revision item | Sub-claim(s) | Severity | Evidence anchor | Confidence | Source | Consensus level | Cost scope | Bounded consequence |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | REV-01 | Rewrite the abstract and contribution list around the original insights (S/S′ split, conditional proofs-over-attestation edge, Proof-of-Guardrail boundary reading), and state the order's value as making its assumptions explicit | SC-1 | major | text: §4.2 and §5 "Results 1 to 4 are readouts of Table 1, not discoveries" | 4 (handling-editor reading) | EIC W1 | SINGLE-VERIFIER | section: Abstract; §1 contribution list | interpretive_ambiguity_remains → section: Abstract, §1 |
| R2 | REV-02 | Present contribution 3 only in the form the body supports: as an "order" if REV-37 constructs τ_G/τ_T, otherwise as an "auditor's view" without "reverses" | SC-2 | major (EIC W1) / major (R3 W1) | text: §4.4 "Table 2 reverses much of Figure 1." | 4 / 4 | EIC W1; R3 W1 | SPLIT (arbitrated, Disagreement 1) | section: Abstract; §1; §4.4 | claim_scope_unsupported → claim: "an auditor's order differs from the integrity order" |
| R3 | REV-10 | Report per-strand counts at each stage (identified, screened, included, excluded), ideally as a supplementary table | SC-10 | minor (EIC W9) / major (R1 W4) | absence: Section 3 — expected counts of sources screened, excluded and included per strand; checked Section 3, Section 7.2, Data and Artifact Availability, References | 3 / 3 | EIC W9; R1 W4 | SPLIT (arbitrated, Disagreement 2) | section: §3 plus repository supplement | method_reproducibility_unresolved → section: §3 |
| R4 | REV-12 | Add a sensitivity paragraph or table splitting P (rerun vs circuit) and K (hash/signature/commitment/soundness), and report which of Results 1–5 survive each split; correct §7.2's claim that §4.2 already states which edges depend on granularity | SC-12, SC-14 | major | text: §4.1 "a correct implementation of C and M, whether in the verifier's code, a delegated program, a measured image or a circuit" | 4 (order-theoretic; recomputed inclusions) | R1 W1 (DA M1 corroborates SC-14) | SINGLE-VERIFIER | re_analysis: §4.1–§4.2, §7.2 | claim_scope_unsupported → claim: Results 1–5 |
| R5 | REV-13 | Qualify Result 5, §5.4, the abstract and the conclusion: "replay needs less trust than the proofs" holds only under the named reading (single P; K split or verifier holding the enrolled bytes) | SC-13 | major (R1 W1) / minor (R2 W1) | text: §4.2 Result 5 "less than every other class, proofs included" | 4 / 4 | R1 W1; R2 W1 (DA M1) | SPLIT (arbitrated, Disagreement 3) | sentence: Abstract; §4.2 Result 5; §5.4; §8 | claim_scope_unsupported → claim: "replay needs less trust than the proofs" |
| R6 | REV-16 | Report the query strings and sources searched for each strand; if no log exists, re-run a documented search and say it was re-run | SC-17 | major | text: §3 "Each strand was searched on 2026-10-30 with public topic terms in web search and on primary pages" | 3 (SoK procedure norms) | R1 W4 | SINGLE-VERIFIER | section: §3 plus repository search log (new_data if re-run) | method_reproducibility_unresolved → section: §3 |
| R7 | REV-22 | State that the demonstrated replay identifies weights by SHA-256 digest and therefore relies on the hash part of K, unless the verifier holds the enrolled bytes | SC-23 | minor (R2 W1); DA M1 major | text: §5.4 "replay of an exact integer program needs only {E, P}, while the proof needs {E, P, K} at unqualified parameters" | 4 (R2); 4 (DA) | R2 W1; DA M1 | SINGLE-VERIFIER (DA-corroborated) | sentence: §5.4; Table 1 replay row note | claim_scope_unsupported → claim: τ(replay) ⊂ τ(5) |
| R8 | REV-37 | Either construct τ_G and τ_T for classes 2, 3b and 4 (plus an independent time-source element if needed) and derive the comparison, or rename "order" to "auditor's view" and drop "reverses"; cite or soften "the senses of 'ran' an auditor often cares about most" | SC-38, SC-39 | major | text: §4.4 "Table 2 reverses much of Figure 1." | 4 (assurance practice) | R3 W1 | SINGLE-VERIFIER | section: Table 2; §4.4; §8 (one new table if constructed) | claim_scope_unsupported → table: Table 2 |
| R9 | REV-38 | State both conditions for the pre-release-log composition in gap 1 and in the Table 2 class-2 cell: the log or its timestamps are run or witnessed by a party other than O, and the served answer carries a receipt tying it to the entry | SC-40, SC-41 | major | text: §7.1 gap 1 "would fix the claimed verdict in time for later proofs to match" | 4 (record-keeping design) | R3 W2 | SINGLE-VERIFIER | section: §7.1 gap 1; Table 2 class 2; §8 | claim_scope_unsupported → claim: pre-release log fixes the verdict in time |
| R10 | REV-48 | Settle the premise for replay's trust set: either state that the replaying verifier holds the reference copy by enrollment and give proof roots the same treatment, or add K to replay and re-derive Results 4 and 5, the §4.2 counts, Figure 1 and the abstract | SC-51 | major | text: §4.2 Result 5 "Replay of that computation then needs only {E, P}, less than every other class, proofs included." | 4 (recomputed inclusions and counts) | DA M1 | SINGLE-VERIFIER (DA) | re_analysis: Table 1 replay row; §4.2; Figure 1; Abstract | claim_scope_unsupported → claim: Result 4 unconditional |
| R11 | REV-49 | Rename the first reading of "ran" as value correctness; add an execution-occurred reading to Table 2 or fold it explicitly into T; restate Skip relative to S′ | SC-52 | major | text: Abstract "Every compared class speaks to what was computed." | 4 (close reading) | DA M2 | SINGLE-VERIFIER (DA) | section: §1; §2.2–§2.3; Table 2; §5.4 | interpretive_ambiguity_remains → claim: "Every compared class speaks to what was computed" |
| R12 | REV-50 | Add an attribution or non-repudiation column to Table 2, or exclude that property explicitly in §2.2, and restate the RAILS comparison as a difference in target property | SC-53 | major | text: §6 "for the integrity of a verdict ours merges them, because a signature by the operator authenticates the record, not the computation" | 3 (RAILS read through the manuscript only) | DA M3 | SINGLE-VERIFIER (DA) | section: Table 2 or §2.2; §6 | claim_scope_unsupported → section: §6 RAILS comparison |

### Required Item Details

**R1: Reframe the contribution list (REV-01)**
- **Problem**: The text calls Results 1–4 readouts and the case study a consequence of definitions, yet contributions 2 and 4 headline them, while the original insights are scattered.
- **Source**: EIC W1, "An SoK reader who finishes the abstract and Section 1 cannot easily say what new insight the paper offers beyond the definitions it fixes."
- **Requirement**: Rewrite the abstract and the §1 contribution list around the S/S′ split, the conditional edge, the Proof-of-Guardrail reading and contribution 3 (as resolved in R2), and state the order's value as making its assumptions explicit.
- **Acceptance criteria**: The abstract and §1 name the original insights as the contributions, and no listed contribution is one the body calls a readout or a definitional consequence.

**R2: Present contribution 3 in the form the body supports (REV-02)**
- **Problem**: EIC wants the integrity/auditor divergence headlined; R3 finds the "auditor's order" asserted, not constructed.
- **Source**: EIC W1; R3 W1 ("the word 'order' promises a comparison the paper does not supply"); Disagreement 1.
- **Requirement**: Headline contribution 3 as an order only if REV-37 constructs τ_G/τ_T; otherwise present it as an auditor's view and drop "reverses".
- **Acceptance criteria**: Every place that calls contribution 3 an "order" (abstract, §1, §4.4, §8) is backed by derived trust sets for G and T, or the word is replaced with "view" and "reverses" no longer appears.

**R3: Report search counts per strand (REV-10)**
- **Problem**: Section 3 gives strands, a date and inclusion criteria, but no counts at any stage.
- **Source**: EIC W9 (absence anchor on Section 3); R1 W4 ("The paper reports neither the search terms nor any counts").
- **Requirement**: Report identified, screened, included and excluded counts for each strand, in §3 or a referenced repository table.
- **Acceptance criteria**: For each of the four strands, §3 or a referenced supplementary table gives counts at each screening stage that sum consistently to the included set.

**R4: Granularity sensitivity for P and K (REV-12)**
- **Problem**: P is one element shared by replay, delegation, measured images and circuits; the sensitivity of the results to splitting it is not analysed, and §7.2 overstates what §4.2 covers.
- **Source**: R1 W1 ("§7.2 says 'Section 4.2 states which edges depend on its granularity', but §4.2 does this only for K and N"); DA M1 asks for the same §7.2 correction.
- **Requirement**: Add a paragraph or table that splits P (P_rerun, P_circuit) and K (hash, signature, commitment, soundness), report which of Results 1–5 survive each split, and correct §7.2.
- **Acceptance criteria**: A table or paragraph lists Results 1–5 against at least the P-split and the K-split, marking each as surviving or failing, and §7.2's granularity sentence matches what that table covers.

**R5: Qualify the replay-versus-proof claim (REV-13)**
- **Problem**: "Replay needs less trust than the proofs" is stated unconditionally in the abstract and Result 5, but it is strict only under particular readings of P and K.
- **Source**: R1 W1 ("Result 5 then disappears, and so does the abstract's claim"); R2 W1 ("Result 5, §5.4 and the abstract should say which of these readings makes 'less trust' strict"); Disagreement 3.
- **Requirement**: Qualify the sentence in the abstract, Result 5, §5.4 and §8 with the reading under which it holds.
- **Acceptance criteria**: Every occurrence of the replay-versus-proof trust comparison names the reading (single-P convention and K split, or verifier holding enrolled bytes) under which "less" is strict.

**R6: Make the literature search reproducible (REV-16)**
- **Problem**: The search terms and sources are not reported; the search ran on one day through general web search by an automated pipeline.
- **Source**: R1 W4 ("The inclusion rule is stated, but how it was applied cannot be checked").
- **Requirement**: Report the query strings and sources searched for each strand; if no log exists, re-run a documented search and say so.
- **Acceptance criteria**: §3 or a referenced repository file lists, for each strand, the exact query strings, the sources searched and the search date, and states whether it is the original log or a documented re-run.

**R7: Charge the hash assumption the replay path uses (REV-22)**
- **Problem**: The demonstrated replay authenticates weights by SHA-256, which is part of K, yet replay's set omits K.
- **Source**: R2 W1 ("Under the coarse universe, τ(replay) is then {E, P, K}, the same set as τ(5)"); DA M1.
- **Requirement**: State that replay relies on hash collision resistance when weights are identified by digest, and give the condition under which it does not.
- **Acceptance criteria**: §5.4 (and the Table 1 replay row or its note) states that replay with digest-identified weights carries K's hash assumption, and names the case in which it does not.

**R8: Construct or rename the auditor's order (REV-37)**
- **Problem**: Table 2's G/T cells are qualitative, with no trust sets, so no comparison between classes can be derived; the "cares about most" sentence has no cited support.
- **Source**: R3 W1 ("The rigor that makes the integrity order useful ... is missing exactly where the paper addresses auditors").
- **Requirement**: Either derive τ_G and τ_T for classes 2, 3b and 4 from U (adding an independent time-source element if needed), or relabel Table 2 as an auditor's view; and cite or soften the "cares about most" sentence.
- **Acceptance criteria**: Either a table gives τ_G and τ_T for classes 2, 3b and 4 with the derived comparison, or no text calls Table 2 an order; and the "cares about most" sentence carries a citation or is softened.

**R9: State the conditions for the pre-release log (REV-38)**
- **Problem**: As stated, an operator can write the log entry after release and present it as prior (Defer).
- **Source**: R3 W2 ("Without both conditions, an operator can write the entry after release and present it as prior").
- **Requirement**: State, in gap 1 and the Table 2 class-2 cell, that the log or its timestamps must be run or witnessed by a party other than O, and that the served answer must carry a receipt tying it to the entry.
- **Acceptance criteria**: Gap 1 and the Table 2 class-2 T cell both name the independent log or time party and the receipt delivered with Y as conditions.

**R10: Settle the premise behind replay's trust set (REV-48)**
- **Problem**: K is charged to every class above the bottom except replay; charging it changes Result 4 and the incomparability count under the folded reading.
- **Source**: DA M1 ("only 5 of the 10 pairs above the bottom are incomparable, not 'most'").
- **Requirement**: Either state that the replaying verifier holds the reference copy by enrollment and treat proof roots the same way, or add K to replay and re-derive Results 4 and 5, the §4.2 counts, Figure 1 and the abstract.
- **Acceptance criteria**: The paper states one rule for weight authentication, applies it to both replay and proofs, and reports §4.2 counts and Results 4–5 consistent with that rule under each K reading it presents.

**R11: Separate value correctness from execution (REV-49)**
- **Problem**: "Computed" means an event in §1 and a value in Table 2; under the formal definition, Skip with a true allow leaves S true.
- **Source**: DA M2 ("Skip differs from Misreport only under an execution reading the taxonomy omits").
- **Requirement**: Rename the first reading as value correctness, add an execution-occurred reading to Table 2 or fold it into T explicitly, and restate Skip relative to S′.
- **Acceptance criteria**: §1, Table 2 and §2.3 use one defined sense of "computed", and the Skip defence in §5.4 is stated relative to S′.

**R12: Address attribution in the RAILS comparison (REV-50)**
- **Problem**: The claimed difference from RAILS follows from the τ = U convention, while the paper's own gap 8 relies on the attribution property that no column records.
- **Source**: DA M3 ("The counter-argument is not addressed"); Disagreement 5.
- **Requirement**: Add an attribution or non-repudiation column to Table 2, or exclude that property explicitly in §2.2, and restate the RAILS comparison as a difference in target property.
- **Acceptance criteria**: Attribution either appears as a Table 2 column or is explicitly excluded in §2.2, and the §6 RAILS sentence names the target property on which the orders differ.

## Suggested Revisions (should_fix / consider)

| Transport ref | Item | Revision item | Sub-claim(s) | Severity | Evidence anchor | Confidence | Source | Consensus level | Obligation | Cost scope | Bounded consequence |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | REV-03 | Lead the "Search outcome and novelty" paragraph with the systematization's novelty, not the artifact's priority | SC-3 | minor | text: §6 "no peer-reviewed or preprint work reports succinct per-request proofs of a guardrail-classifier verdict composed with an LLM-answer proof" | 4 | EIC W2 | SINGLE-VERIFIER | should_fix | sentence: §6 | interpretive_ambiguity_remains → section: §6 |
| S2 | REV-04 | Move most of Table 4 and the timing-boundary discussion to an appendix, keeping the 738 MB bundle point | SC-4 | minor | table: Table 4, Section 5.5 | 4 | EIC W3 | SINGLE-VERIFIER | should_fix | section: §5.4–§5.5, Table 4 | reader_traceability_reduced → section: §5 |
| S3 | REV-05 | Rename one of the two uses of T (timing clause vs tolerance trust element) | SC-5 | minor | text: §2.2 and §4.1 "T says that V was computed before Y was released" | 5 | EIC W4 | SINGLE-VERIFIER | should_fix | section: §2.2, §4.1, Table 1, Figure 1 | interpretive_ambiguity_remains → claim: notation T |
| S4 | REV-06 | Disambiguate the pair-count sentence (a small table under both readings) | SC-6 | minor | text: §4.2 "all but four comparable pairs (one without the dashed edges) involve the bottom class" | 3 | EIC W5 | SINGLE-VERIFIER | should_fix | sentence: §4.2 | interpretive_ambiguity_remains → section: §4.2 |
| S5 | REV-07 | Replace class numbers with mnemonic labels so the order is not read as a ladder | SC-7 | minor | text: §4.2 "Class numbers are kept only as short keys for the tables, not heights, and the order is not a ladder" | 4 | EIC W6 | SINGLE-VERIFIER | consider | section: §4, Tables 1–2, Figure 1 | interpretive_ambiguity_remains → section: §4 |
| S6 | REV-08 | Define "qualified" at first use and drop config-style flags and profile names from the prose | SC-8 | minor | text: Box 1 "The backend is not qualified" | 4 | EIC W7 | SINGLE-VERIFIER | should_fix | section: Box 1; §5 | reader_traceability_reduced → section: Box 1 |
| S7 | REV-09 | State whether the employer offers or develops products in any compared evidence class | SC-9 | minor | absence: Competing Interests — expected a statement of whether the author's employer offers or develops products or services in any compared evidence class; checked Competing Interests, Funding, Author Contributions, AI-Use Disclosure, Section 7.2 | 3 | EIC W8 | SINGLE-VERIFIER | should_fix | sentence: Competing Interests | reporting_requirement_unmet → section: Competing Interests |
| S8 | REV-11 | Carry rendered Figures 1 and 2 in the submitted version | SC-11 | minor | figure: Figure 1 and Figure 2, Sections 4.2 and 5.2 | 3 | EIC W10 | SINGLE-VERIFIER | should_fix | other (rendered_figures): Figures 1–2 | editorial_conformance_unmet → figure: Figures 1–2 |
| S9 | REV-14 | Add a generic honest-outside-party element to U or drop "auditors" from the Table 1 class-2 cell | SC-15 | minor | table: Table 1, row "2 Signed / logged record", trust-set cell "U (writer is O); permanence: K, auditors" | 4 | R1 W2 | SINGLE-VERIFIER | should_fix | section: §4.1 U; Table 1; §4.3 | interpretive_ambiguity_remains → table: Table 1 |
| S10 | REV-15 | Add a strategy × class table showing which of the seven strategies each class defends against | SC-16 | minor | absence: §4 class analysis — expected a per-class record of which of the seven strategies (Skip, Swap, Substitute, Replay, Misreport, Ignore, Defer) each class defends against under its trust set; checked §2.3, §4.2, §4.3, §4.4, Table 1, Table 2 and §5.4 | 4 | R1 W3 | SINGLE-VERIFIER | should_fix | section: §4 (one new table) | evidence_gap_remains → section: §4 |
| S11 | REV-17 | Tie the §6 negative novelty statement to the documented search (REV-10, REV-16), and revise it if that search finds a qualifying system | SC-18 | major (R1 W4) / minor (R2 W15) | text: §3 "Each strand was searched on 2026-10-30 with public topic terms in web search and on primary pages" | 3 / 2 | R1 W4; R2 W15 | SPLIT (arbitrated, Disagreement 4; completeness unresolved) | should_fix | sentence: §6 | claim_scope_unsupported → claim: §6 negative novelty statement |
| S12 | REV-18 | Give the reading depth for the current 97-entry list, for every source used to place a system | SC-19 | minor | text: §3 "re-read the cited passages from source full texts for 69 of the 81 references then cited" | 3 | R1 W5 | SINGLE-VERIFIER | should_fix | sentence: §3 plus annotation file | reporting_requirement_unmet → section: §3 |
| S13 | REV-19 | Justify that the TinyLlama rerun is integer-exact with the proved profile, or limit the sentence to "reproduced in one run" | SC-20 | minor | text: §5.4 "The same holds for a verifier that holds the TinyLlama weights, since a rerun under the proved relation reproduced the proved answer" | 3 | R1 W6 | SINGLE-VERIFIER | should_fix | sentence: §5.4 | claim_scope_unsupported → claim: LLM replay exactness |
| S14 | REV-20 | Rerun exp-R1 so its record carries commit and CPU model, and repeat the verifier timings warm if they stay | SC-21 | minor | text: §5.5 "The exp-R1 records carry the platform, core count and thread settings but not the code commit or the CPU model" | 4 | R1 W7 | SINGLE-VERIFIER | should_fix | new_data: exp-R1 records; Table 4 | method_reproducibility_unresolved → dataset: exp-R1 records |
| S15 | REV-21 | Cite recorded failures for replay, logs, 3a and 3b, or reword to "failure records of classes 4 and 5, and failure modes of the others" | SC-22 | minor | text: §4.4 "Attacks show where the residual trust goes: to physical security and keys at class 4 [B16]" | 3 | R1 W8 | SINGLE-VERIFIER | should_fix | sentence: §4.4; §1 contribution 3 | claim_scope_unsupported → claim: failure records across classes |
| S16 | REV-23 | Add a short paragraph on class 4 appraisal parameters (TCB levels, debug and migration policy, revocation, nonce freshness, collateral currency), parallel to §5.3 | SC-24 | minor | absence: §4.3 class 4 and Table 1 — expected an account of the appraisal parameters a class 4 verifier must fix (TCB or security-version levels, debug and migration policy, revocation and TCB recovery after disclosed attacks, nonce freshness, currency of collateral), parallel to the proof-parameter analysis of §5.3; checked §2.1, §4.1, §4.3 class 4, Table 1, Table 2, §7.1 gaps 1 and 7 | 4 | R2 W2 | SINGLE-VERIFIER | should_fix | section: §4.3 class 4 | evidence_gap_remains → section: §4.3 |
| S17 | REV-24 | Check attestation-targeting SEV-SNP/SGX attacks (BadRAM, Battering RAM, WireTap, recalled by R2) against primary sources and add any that are confirmed | SC-25 | minor | text: §4.3 "CacheWarp broke the integrity of AMD Secure Encrypted Virtualization with Secure Nested Paging (SEV-SNP) [B15]" | 3 | R2 W3 | SINGLE-VERIFIER | should_fix | section: §4.3 class 4 | evidence_gap_remains → claim: class 4 failure record |
| S18 | REV-25 | State that each SASH segment composes FRI-based STARK and GKR arguments, so the 100-bit figure covers one component | SC-26 | minor | text: §5.1 "an open-source STARK prover for a quantized transformer" | 3 | R2 W4 | SINGLE-VERIFIER | should_fix | sentence: §5.1; §5.3 | interpretive_ambiguity_remains → section: §5.3 |
| S19 | REV-26 | State that enrollment and public inputs are absorbed into the Fiat–Shamir transcript before the first challenge (classifier AIR, and whether SASH does the same) | SC-27 | minor | absence: §4.3 class 5 and §5.1 to §5.3 — expected a statement of whether each proof's enrollment and public inputs are absorbed into the Fiat–Shamir transcript before the first challenge, for the classifier AIR and for the SASH segments; checked §4.3 class 5, §5.1, §5.2, §5.3, §7.1 gap 7, Appendix A | 4 | R2 W5 | SINGLE-VERIFIER | should_fix | sentence: §5.1 | evidence_gap_remains → section: §5.1 |
| S20 | REV-27 | Note that the Mac verifier is a patched SASH variant (residual P includes the patch), and say "shape roots" instead of "model roots" | SC-28 | minor | text: §5.1 "it is verified only by the SASH prover's own pinned implementation" | 4 | R2 W6; DA minor 2 | SINGLE-VERIFIER (DA-corroborated) | should_fix | sentence: §5.1; §5.4; Tables 4–5 | claim_scope_unsupported → claim: verifier implementation |
| S21 | REV-28 | Qualify "spares a verifier the weights" as per request, given enrolled roots, in the abstract and conclusion | SC-29 | minor | text: Abstract "The proofs spare a verifier the weights and re-execution" | 4 | R2 W7; DA minor 3 | SINGLE-VERIFIER (DA-corroborated) | should_fix | sentence: Abstract; §8 | claim_scope_unsupported → claim: "spare a verifier the weights" |
| S22 | REV-29 | Say in the abstract and conclusion that logs supply a timing anchor for a claim, and only a measured program on the serving path supplies G | SC-30 | minor | text: Abstract "needs a mechanism on the serving path that some attestation and logging designs supply and a proof cannot" | 4 | R2 W8 | SINGLE-VERIFIER | should_fix | sentence: Abstract; §8 | claim_scope_unsupported → claim: logs supply G |
| S23 | REV-30 | If 2025 counterexamples to the strong proximity-gap conjecture are confirmed, add one sentence on the conjecture's status | SC-31 | minor | text: §5.3 "a query-and-grinding conjecture that the unanalysed extension-field and hash terms below cap, not a proven bound" | 3 | R2 W9 | SINGLE-VERIFIER | consider | sentence: §5.3 | interpretive_ambiguity_remains → section: §5.3 |
| S24 | REV-31 | Cite [A27] alongside [A40] for the circle-code Johnson-bound regime | SC-32 | minor | text: §5.3 "the regime up to the Johnson bound [A40] gives at most about 50 and 176" | 3 | R2 W10 | SINGLE-VERIFIER | should_fix | sentence: §5.3 | reader_traceability_reduced → section: §5.3 |
| S25 | REV-32 | Say that "strictly logarithmic verifier" is an IOP-model statement; compiled verification costs O(λ · log² n) hashes | SC-33 | minor | text: §4.3 "FRI has a strictly logarithmic verifier [A25]" | 4 | R2 W11 | SINGLE-VERIFIER | should_fix | sentence: §4.3 | interpretive_ambiguity_remains → section: §4.3 |
| S26 | REV-33 | Separate hiding from the verifier from confidentiality against the operator in Table 2 | SC-34 | minor | text: §4.3 "Hiding from the host holds within the stated threat model [B3]" | 4 | R2 W12 | SINGLE-VERIFIER | should_fix | section: Table 2 hiding column; §4.3 | interpretive_ambiguity_remains → table: Table 2 |
| S27 | REV-34 | Change limb-decomposition soundness to "are designed so that", or point to an argument | SC-35 | minor | text: §5.1 "so that no integer alias modulo the Mersenne-31 prime passes" | 4 | R2 W13 | SINGLE-VERIFIER | should_fix | sentence: §5.1 | claim_scope_unsupported → claim: limb-decomposition soundness |
| S28 | REV-35 | Use one name for the [A23] attack throughout | SC-36 | minor | table: Table 1, class 5 row, Characteristic failure column | 5 | R2 W14 | SINGLE-VERIFIER | should_fix | sentence: §4.3; Table 1; §7.1 gap 3 | reader_traceability_reduced → claim: [A23] naming |
| S29 | REV-36 | Check strand A coverage for further 2025 security-venue LLM provers (zkGPT, recalled by R2) | SC-37 | minor | absence: §6 Proofs of ML inference — expected coverage of further succinct LLM-inference provers from 2025 security venues (for example zkGPT, recalled from memory and not checked here); checked §1, §3, §4.3 class 5, §6, Table 6 | 2 | R2 W15 | SINGLE-VERIFIER | consider | section: §6 strand A | evidence_gap_remains → section: §6 |
| S30 | REV-39 | Note that sampled-proof detection of Skip scales with the block base rate; size samples accordingly or seed known-block inputs | SC-42 | minor | text: §7.1 gap 8 "an operator that commits to a verdict before computing it is caught whenever a sampled proof disagrees" | 4 | R3 W3 | SINGLE-VERIFIER | should_fix | sentence: §7.1 gap 8 | interpretive_ambiguity_remains → claim: sampling detection |
| S31 | REV-40 | Add to the Table 2 class-4 capture-provenance cell and gap 2 the condition that the user's client encrypts to an attested key | SC-43 | minor | table: Table 2, class 4 row, Capture provenance column | 3 | R3 W4 | SINGLE-VERIFIER | should_fix | sentence: Table 2; §7.1 gap 2 | claim_scope_unsupported → table: Table 2 |
| S32 | REV-41 | Add a Table 2 note restricting the G/T cells to non-streamed release or input rails | SC-44 | minor | table: Table 2, Gating (G) and timing (T) column, classes 2 and 4 | 4 | R3 W5 | SINGLE-VERIFIER | should_fix | sentence: Table 2 note | claim_scope_unsupported → table: Table 2 |
| S33 | REV-42 | Give the honest-enroller assumption its deployment reading (public, prior, append-only enrollment); say whether a fallback policy is a reference value or appraisal policy; say whether §5.2 used signed enrollment or the signed registry | SC-45 | minor | text: §2.3 "The enroller is honest and completes enrollment before any proof or report is produced." | 3 | R3 W6 | SINGLE-VERIFIER | should_fix | section: §2.3; §5.2; §7.1 gap 5 | evidence_gap_remains → section: §2.3 |
| S34 | REV-43 | Align gap 10's reading of the Code of Practice with the introduction's Measure 5.1 / 7.3 split | SC-46 | minor | text: §7.1 gap 10 "asks providers of general-purpose AI models with systemic risk to implement and document mitigations such as input and output filtering" | 3 | R3 W7 | SINGLE-VERIFIER | should_fix | sentence: §7.1 gap 10 | interpretive_ambiguity_remains → section: §7.1 |
| S35 | REV-44 | Map operator, verifier and enroller onto provider, deployer and authority, taking no position on which applies, and correct the regulator-as-user's-agent phrasing | SC-47 | minor | text: §2.1 "it may be the user who sent the request, an auditor, or a regulator acting for the user" | 3 | R3 W8 | SINGLE-VERIFIER | consider | sentence: §2.1 | interpretive_ambiguity_remains → section: §2.1 |
| S36 | REV-45 | Open §5.3 with one sentence giving its consequence for governance readers | SC-48 | minor | text: §5.3 "the unique-decoding regime gives about 41.5 bits per LLM segment" | 4 | R3 W9 | SINGLE-VERIFIER | should_fix | sentence: §5.3 | reader_traceability_reduced → section: §5.3 |
| S37 | REV-46 | Address prompt disclosure in auditor-side verification and retained evidence, and state whether the bundle reveals the committed prompt without hiding | SC-49 | minor | text: §7.1 gap 3 "With public witnesses, a deployer cannot hand auditors prompts containing user data without a separate privacy basis." | 2 | R3 W10 | SINGLE-VERIFIER | should_fix | section: §7.1 gap 3 | evidence_gap_remains → section: §7.1 |
| S38 | REV-47 | Make the Box 1 caution operational in §7: a receipt should name the enrolled classifier and point to adequacy evidence or say none exists; optionally acknowledge the "Hallmark" connotation | SC-50 | minor | text: §7.1 "A receipt a deployer could hand to an auditor would need more than any single class provides." | 3 | R3 W11 | SINGLE-VERIFIER | should_fix | sentence: §7 | interpretive_ambiguity_remains → section: §7 |
| S39 | REV-51 | Name an enrolled transform from R to the model's tokens in S and count it in E and P | SC-54 | minor [SEVERITY-SOURCE: DA "Minor issues" heading] | text: §2.2 statement S (DA minor issue 1 cites `scripts/composed_input.py`, `check_request`) | not stated [CONFIDENCE-SOURCE: none on the card] | DA minor 1 | SINGLE-VERIFIER (DA) | should_fix | section: §2.2; §5 | claim_scope_unsupported → claim: statement S |
| S40 | REV-52 | Add one sentence in §5.4 that the classifier proofs' shared context binds the response, so an input-rail proof cannot be formed before Y exists | SC-55 | minor [SEVERITY-SOURCE: DA "Minor issues" heading] | text: §5.4 (DA minor issue 4 cites `docs/COMPOSED-DEMO.md`) | not stated | DA minor 4 | SINGLE-VERIFIER (DA) | consider | sentence: §5.4 | evidence_gap_remains → section: §5.4 |
| S41 | REV-53 | Examine the premise that the user-as-verifier holds R when the system prompt and context are hidden (binding vs hiding) | SC-56 | minor [SEVERITY-SOURCE: DA "Minor issues" heading] | text: §2.3 threat model, verifier holds R (DA minor issue 5) | not stated | DA minor 5 | SINGLE-VERIFIER (DA) | consider | sentence: §2.3; §2.4 | interpretive_ambiguity_remains → section: §2.3 |

Severity, evidence anchor and confidence are carried over unchanged from the driving finding on every row. DA minor issues 1, 4 and 5 carry no typed anchor in the DA card. Their anchors above are the manuscript locations the DA names, not typed anchors the DA itself supplied.

## Source-traceability checklist (immutable source order; not a work order)

- [ ] REV-01 (R1), `must_fix`: Reframe the contribution list and abstract around the original insights
- [ ] REV-02 (R2), `must_fix`: Present contribution 3 as an order only if constructed, otherwise as a view
- [ ] REV-03 (S1), `should_fix`: Lead the novelty paragraph with the systematization's novelty
- [ ] REV-04 (S2), `should_fix`: Move most cost material to an appendix
- [ ] REV-05 (S3), `should_fix`: Disambiguate the symbol T
- [ ] REV-06 (S4), `should_fix`: Disambiguate the pair-count sentence
- [ ] REV-07 (S5), `consider`: Mnemonic class labels
- [ ] REV-08 (S6), `should_fix`: Define "qualified"; drop config flags from the prose
- [ ] REV-09 (S7), `should_fix`: Complete the competing-interest statement
- [ ] REV-10 (R3), `must_fix`: Report per-strand search counts
- [ ] REV-11 (S8), `should_fix`: Rendered figures
- [ ] REV-12 (R4), `must_fix`: Granularity sensitivity for P and K; correct §7.2
- [ ] REV-13 (R5), `must_fix`: Qualify the replay-versus-proof claim
- [ ] REV-14 (S9), `should_fix`: Close U under outside parties
- [ ] REV-15 (S10), `should_fix`: Strategy × class table
- [ ] REV-16 (R6), `must_fix`: Report query strings and sources, or re-run a documented search
- [ ] REV-17 (S11), `should_fix`: Tie the novelty statement to the documented search
- [ ] REV-18 (S12), `should_fix`: Reading depth for the current reference list
- [ ] REV-19 (S13), `should_fix`: LLM replay exactness or narrower wording
- [ ] REV-20 (S14), `should_fix`: exp-R1 provenance rerun
- [ ] REV-21 (S15), `should_fix`: Failure-record claim across classes
- [ ] REV-22 (R7), `must_fix`: Charge the hash assumption the replay path uses
- [ ] REV-23 (S16), `should_fix`: Attestation appraisal parameters
- [ ] REV-24 (S17), `should_fix`: Attestation-targeting attacks in the class 4 record
- [ ] REV-25 (S18), `should_fix`: GKR component in the soundness account
- [ ] REV-26 (S19), `should_fix`: Fiat–Shamir public-input absorption
- [ ] REV-27 (S20), `should_fix`: Patched SASH verifier; "shape roots"
- [ ] REV-28 (S21), `should_fix`: Qualify "spares a verifier the weights"
- [ ] REV-29 (S22), `should_fix`: Logs supply timing, not gating
- [ ] REV-30 (S23), `consider`: Status of the proximity-gap conjecture
- [ ] REV-31 (S24), `should_fix`: Cite [A27] for circle codes
- [ ] REV-32 (S25), `should_fix`: IOP-model qualifier for "logarithmic"
- [ ] REV-33 (S26), `should_fix`: Hiding vs confidentiality in Table 2
- [ ] REV-34 (S27), `should_fix`: Limb decomposition as design intent
- [ ] REV-35 (S28), `should_fix`: One name for the [A23] attack
- [ ] REV-36 (S29), `consider`: Strand A coverage check
- [ ] REV-37 (R8), `must_fix`: Construct τ_G/τ_T or rename the auditor's order; support "cares about most"
- [ ] REV-38 (R9), `must_fix`: Conditions for the pre-release log
- [ ] REV-39 (S30), `should_fix`: Sampling and the block base rate
- [ ] REV-40 (S31), `should_fix`: Class 4 capture provenance condition
- [ ] REV-41 (S32), `should_fix`: Streaming caveat on Table 2
- [ ] REV-42 (S33), `should_fix`: Deployment reading of the honest enroller
- [ ] REV-43 (S34), `should_fix`: Consistent reading of the Code of Practice
- [ ] REV-44 (S35), `consider`: Map roles to regulatory roles
- [ ] REV-45 (S36), `should_fix`: Governance takeaway at the top of §5.3
- [ ] REV-46 (S37), `should_fix`: Prompt privacy in retained evidence
- [ ] REV-47 (S38), `should_fix`: Operational receipt caution
- [ ] REV-48 (R10), `must_fix`: One weight-authentication rule for replay and proofs; re-derive Results 4–5
- [ ] REV-49 (R11), `must_fix`: Separate value correctness from execution
- [ ] REV-50 (R12), `must_fix`: Attribution and the RAILS comparison
- [ ] REV-51 (S39), `should_fix`: Enrolled transform from R to model tokens
- [ ] REV-52 (S40), `consider`: Input-rail proof cannot precede Y
- [ ] REV-53 (S41), `consider`: Binding vs hiding for the user-as-verifier

Counts: 53 items, of which 12 are `must_fix`, 35 `should_fix` and 6 `consider`.

## Journal-Supplied Deadline

- **Exact deadline from source letter**: NOT PROVIDED. No deadline, duration or work estimate is inferred.

## Response Letter Instructions

Respond item by item using `templates/revision_response_template.md`. The response must include:
1. A response and change description for each of R1 to R12.
2. A response for each suggested item, saying whether it was adopted or why not. Declining an item is allowed and must stay visible.
3. Change markup in the revised manuscript.
4. A cross-reference table of new section, table and figure locations.

Author triage (`will_address`, `wont_address`, `not_on_point`) is collected later in the separate author-adjudication sidecar, not in this roadmap.

## Closing

We encourage you to consider the reviewers' comments carefully and submit a substantially revised manuscript. The panel finds a real and original contribution, the S/S′ split above all, whose central result survives every challenge raised. The revision mostly needs to make the paper's own assumptions do the work its headline sentences currently claim. The revised manuscript will undergo another round of review, focused first on REV-12, REV-13, REV-22 and REV-48 (the replay and proof trust sets) and on REV-02 and REV-37 (contribution 3).

The Editor

---

# Part 3: Reviewer Report Summary (Appendix)

The full reports are in `runs/paper-panel/`: `eic.phase2.md`, `methodology.phase2.md`, `domain.phase2.md`, `perspective.phase2.md` and `da.phase2.md` (with the matching `*.phase1.md` contract cards).

### Journal-Fit Review Report Summary
- Scores: D5 warn, D6 warn. Overall recommendation not stated. Confidence is per finding (3 to 5).
- Key point: the contribution is real and original in framing, but its citable core (S/S′, the conditional edge, the integrity/auditor gap, the Proof-of-Guardrail reading) is buried under material the paper itself calls derivative. The fix is to reframe and rebalance (W1, Major).

### Reviewer 1 (Methodology) Summary
- Scores: D1 warn, D3 warn. Overall recommendation not stated. Confidence is per finding (3 to 4).
- Key point: the order is correctly constructed and every count reproduces. However, sensitivity to granularity is worked out only for K (W1, Major), and the literature search cannot be reproduced (W4, Major).

### Reviewer 2 (Domain) Summary
- Scores: D2 warn. Overall recommendation not stated. Confidence is per finding (2 to 5).
- Key point: all soundness figures and the attestation-root decomposition are correct. Fifteen local imprecisions remain, none of which a central claim depends on. The most consequential is that replay relies on the hash part of K when weights are identified by digest (W1).

### Reviewer 3 (Perspective) Summary
- Scores: D4 warn. Overall recommendation not stated. Confidence is per finding (2 to 4).
- Key point: S/S′ is the right decomposition for audit questions, but the "auditor's order" is asserted rather than constructed (W1, Major), and the pre-release-log composition omits who keeps time and how release is evidenced (W2, Major).

### Devil's Advocate Summary
- Recommendation: N/A, findings only. D3 warn.
- Key challenge: there is no Critical challenge. The strongest counter-argument is that K is charged to every class above the bottom except replay. Charging it makes Result 4 conditional and turns Result 5's "proofs included" into a tie under the folded reading (M1). M2 (the shifting sense of "computed") and M3 (attribution and RAILS) are the other two Major findings.

## Attachment: Suggested-Reference Check (advisory, #1001)

The suggested-reference check did not run: neither the R2 nor the R3 report contains a `yaml suggested-references` block.

## Attachment: Reviewer Claim Check (advisory, #1002)

The judge answered 47 of 47 findings from 5 reviewers: it marked 1 as contradicted, and 8 cannot be checked from the manuscript alone.

The judge marked these findings as contradicted by the manuscript. The script checked only the words of each quote: that they occur in the manuscript, or, for words the finding quotes, that they do not. The judge gave the locations, and the script did not check them. Read each quote to decide:
- Journal-Fit Reviewer · W1: The contribution framing foregrounds the parts the paper itself calls derivative
  > “Most of the resulting order is a direct reading of the assignments, and we say which results are. Its use is to make the assignments explicit, and to expose the edge readers most often assume, proofs over attestation, as conditional” (Section 1, contribution 2)

The author decides what to do with each row. This check does not change the decision, the consensus counts, or the Revision Roadmap. The judge is the session model; as this judge, the #1002 contrast test passed Claude Opus 5.5 and Claude Fable 5.1 (gpt-6-astra and Gemini 4 Argon passed it in part one, through other transports); other models are untested.

## Attachment: Acronym Check (advisory, #849)

### Acronym check (advisory; no reply needed)
Coverage: body, English abstract (partial)
Not in this input: Chinese abstract.
Not checked:
- Body, line 28: MLP (the initials before its parentheses do not spell it)
- Body, line 36: RATS (the initials before its parentheses do not spell it)
- Body, line 91: opML (the initials before its parentheses do not spell it)
- Body, line 91: zkML (the initials before its parentheses do not spell it)
- Body, line 162: SGX (the initials before its parentheses do not spell it)
- Body, line 162: TDX (the initials before its parentheses do not spell it)
- Body, line 166: STARK (the initials before its parentheses do not spell it)
- Body, line 168: SNARK (the initials before its parentheses do not spell it)
- Body, line 375: CRediT (the initials before its parentheses do not spell it)

| Scope | Line | Rule | Acronym | Uses |
|---|---|---|---|---|
| Body | 13 | Not defined | AI | 13 |
| Body | 15 | Not defined | API | 11 |
| Body | 85 | Not defined | ZKML | 1 |
| Body | 102 | Not defined | CPU | 14 |
| Body | 102 | Not defined | GPU | 13 |
| Body | 102 | Not defined | NVIDIA | 3 |
| Body | 118 | Not defined | KZG | 2 |
| Body | 156 | Not defined | OpenID | 1 |
| Body | 158 | Not defined | SVIP | 1 |
| Body | 158 | Not defined | TOPLOC | 1 |
| Body | 162 | Not defined | AMD | 1 |
| Body | 162 | Not defined | PIC | 1 |
| Body | 162 | Not defined | SEV | 1 |
| Body | 162 | Not defined | SNP | 1 |
| Body | 166 | Not defined | VGG16 | 1 |
| Body | 210 | Not defined | SHA | 2 |
| Body | 210 | Not defined | UTF | 1 |
| Body | 212 | Not defined | SASH | 11 |
| Body | 243 | Not defined | QM31 | 1 |
| Body | 253 | Not defined | GB | 3 |
| Body | 259 | Not defined | CUDA | 2 |
| Body | 259 | Not defined | GiB | 2 |
| Body | 259 | Not defined | SXM4 | 1 |
| Body | 304 | Not defined | GPT | 1 |
| Body | 304 | Not defined | ML | 3 |
| Body | 314 | Not defined | ATT | 2 |
| Body | 314 | Not defined | PROOF | 2 |
| Body | 314 | Not defined | RAILS | 5 |
| Body | 314 | Not defined | REC | 1 |
| Body | 314 | Not defined | SELF | 2 |
| Body | 314 | Not defined | SIGN | 2 |
| Body | 314 | Not defined | WIT | 1 |
| Body | 347 | Not defined | DECO | 1 |
| Body | 347 | Not defined | TLS | 1 |
| Body | 367 | Not defined | MIT | 1 |
