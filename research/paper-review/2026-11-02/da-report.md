contract_role: da

## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: not_assessed

### D3: argumentative_coherence
score: warn
trigger: "a plausible counter-argument is left unaddressed without defeating the main thesis"

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

### Calibration Status

`NOT_CALIBRATED`. No target venue is bound (`criteria_binding_unavailable`), so no row below carries a criterion pointer and no venue-alignment claim is made. The constructive-findings companion receives the MAJOR rows below with no criterion id, version or digest.

### Criterion-Bound Judgements

Each judgement is criterion-local; none is totalled, weighted or mapped to a band.

- D3 logical consistency of the trust-set assignments (contract D3; DA Phase 1 plan): PARTLY_MEETS. Located at Table 1, replay row, trust-set column. K is charged to every class above the bottom except replay, although the case's own replay authenticates weights by SHA-256 (M1). Scope limit: depends on whether weight authenticity is read into E. Decision bearing: yes, it changes Result 4 and the incomparability count under one reading.
- D3 stability of key terms: PARTLY_MEETS. Located at §1, the three readings of "ran". "Computed" moves between an event in the operator's pipeline and the value C(R) (M2). Decision bearing: yes, it frames the title question.
- D3 strongest counter-position addressed: PARTLY_MEETS. Located at the Figure 1 caption and §6. The proofs-over-attestation counter is pre-empted well; the attribution value of signed records is not (M3). Scope limit: I read RAILS only through the manuscript's description. Decision bearing: yes, for the RAILS comparison only.
- D3 evidence carries the case conclusions: MEETS. Located at Table 5, cost-profile row. Timing direction claims were withdrawn, and the case conclusions are stated as definitional readouts, not tests. Decision bearing: no.
- D3 self-favouring comparison: MEETS. Located at Table 5, replay row. The paper concedes that replay dominates its own artifact for the classifiers. Decision bearing: no.

### What the manuscript does well

Three things survive adversarial reading and should be kept. The proofs-over-attestation edge is made explicitly conditional, drawn with equal weight in both readings, and tied to the case's own unqualified parameters, which is the opposite of the usual zkML framing. The case study is allowed to undercut its own artifact: the paper states that for exact integer classifiers with public weights the classifier proofs add no integrity evidence for this caller. And the numbers I could recompute hold: the pair counts of §4.2 (15 and 12 comparable of 21; 6 and 9 of 10 incomparable above the bottom), the FRI orientation figures of §5.3 (41.5, 89, 50 and 176 bits), the union-bound loss (log2 23 ≈ 4.52, about 95.5 bits), and the 122 tampering cases (63 + 18 + 3 + 38).

### Strongest counter-argument

The order is advertised as a readout of explicit assignments, so its headline results are only as good as the consistency of the rule that assigns elements. That rule is not applied uniformly. K is defined to include hashes and is charged to every class above the bottom, yet replay receives {E, P, D}, and for exact integer programs {E, P}, even though a verifier who replays must first know that the weights it holds are the enrolled ones. In the paper's own case that is done by SHA-256 digests, and the timed CNN rerun literally hashes the weights. Charge K to replay as the paper charges it to everyone else and Result 4 is no longer unconditional: under the folded reading proofs need {E, P, K}, a strict subset of replay's {E, P, K, D}, so a new dashed edge from replay to proofs appears and only 5 of the 10 pairs above the bottom are incomparable, not "most". Result 5's "proofs included" becomes a tie under the folded reading. The paper invites exactly this dispute ("a reader who disputes one can see which result changes"), but the limitation in §7.2 says §4.2 already states which edges depend on granularity, and it states only the soundness split of K. A second counter-position concerns the title. The integrity order certifies the value of C on R, which a verifier holding the weights can compute without the operator; proofs certify it "by someone, at some time". Neither speaks to whether the operator's classifier executed at all, the reading that distinguishes Skip from Misreport. The thesis that integrity and auditor orders differ survives both objections, and is strengthened by them, but two of its stated results and one of its framing sentences do not survive as written.

### Minor issues (not banded above; each is decision-light)

1. The statement S takes R to be the exact byte or token sequence both the classifier and the model consumed, and §2.2 asks that R include the system prompt and context. In Hallmark the classifier reads the opened prompt string while the model reads 25 chat-template tokens, and β is a host equality check of the opened strings against one enrolled case (`scripts/composed_input.py`, `check_request`; `system_ref` must be all zero). S should name an enrolled transform from R to the model's tokens and count it in E and P.
2. §5.1 says the LLM bundle is verified only by the SASH prover's own pinned implementation. The 3.40–3.53 s Mac path is a patched specialization that reports `dirty: true` and `shape_root_source: "compiled-enrollment"` (`docs/decisions/0070-native-enrolled-llm-verifier.md`). The unpatched Linux verifier also accepted the bundle, so the integrity record stands, but Table 5's residual-P row should name the patch.
3. The abstract's "The proofs spare a verifier the weights and re-execution" omits that the roots the weight-free verifier relies on were derived by someone holding the weights; the caveat sits in §5.5, far from the claim.
4. In Hallmark the classifier proofs' shared context binds the response as well as the prompt (`docs/COMPOSED-DEMO.md`). An input-rail proof in this design therefore cannot be formed before Y exists. That strengthens §5.4's point about timing and is worth one sentence there.
5. The threat model lets the verifier hold R "because it sent R or because R was disclosed to it". A user of a real chat service sends only part of R; the operator's system prompt and context are normally hidden. Binding then requires disclosure or a hiding commitment, so request binding and hiding pull against each other for the user-as-verifier. This is an unexamined premise rather than a defect in the order.

### Ignored alternative organising principle

An order by attributability (which party is caught, and by whom, when a claim is later contradicted) would rank signed records, pre-release logs and attestation differently from trust inclusion, and would explain why the paper's own gap list relies on operator-written commitments that its integrity order places at the bottom.

### Observations (non-defects)

The manuscript contains no instruction addressed to reviewers. Box 1 and Table 5 keep scope claims in one place, which made the claims above easy to locate. Confidence values below disclose scope only.

#### CRITICAL

| # | Dimension | Issue Description | Evidence Anchor | Confidence | Minimum Remedy | Field-Norm Boundary | Evidence-Crossing Rationale |
|---|---|---|---|---|---|---|---|

#### MAJOR

| # | Dimension | Issue Description | Evidence Anchor | Confidence | Minimum Remedy | Field-Norm Boundary | Evidence-Crossing Rationale |
|---|---|---|---|---|---|---|---|
| M1 | D3 | K is charged inconsistently. Replay's set omits K although the replaying verifier must authenticate the weights it holds, and the case's own rerun does so by SHA-256. With K charged, Result 4 (replay and proofs incomparable) holds only under the separated reading; under the folded reading proofs need strictly less than replay, only 5 of 10 pairs above the bottom are incomparable, and Result 5's "proofs included" becomes a tie. The case claim for Hallmark survives, because the paper adopts the separated reading for unqualified parameters. | text: §4.2 Result 5 "Replay of that computation then needs only {E, P}, less than every other class, proofs included."; Table 4 "for the CNN the call includes hashing of weights and tokenizer" | 4: recomputed the inclusion relations and pair counts from Table 1 | Either state that the replaying verifier holds the reference copy by enrollment and give proof roots the same treatment, or add K to replay and re-derive Results 4 and 5, the §4.2 counts, Figure 1 and the abstract; correct §7.2's claim about which edges depend on granularity | n/a: internal consistency of the paper's own assignment rule | n/a |
| M2 | D3 | "Computed" shifts meaning. §1 defines the first reading of "ran" as an event (a classifier computed a verdict on the request) and says every class speaks to it; Table 2 then says replay reports only the verifier's own run and proofs only the value, by someone, at some time. Under the formal integrity definition, Skip with a true allow verdict leaves S true, so Skip differs from Misreport only under an execution reading the taxonomy omits, and §5.4's Skip defence is a timing defence. | text: Abstract "Every compared class speaks to what was computed."; Table 2, class 5 row "V = C(R) was computed, by someone, at some time" | 4: close reading of §1, §2.2, §2.3, Table 2 and §5.4 | Rename the first reading as value correctness, add an execution-occurred reading to Table 2 or fold it explicitly into T, and restate Skip relative to S′ | n/a: internal consistency | n/a |
| M3 | D3 | The claimed difference from RAILS (merging signed records with self-report) follows from the τ = U convention and from leaving attribution out of both tables. An operator-signed per-request verdict that is later contradicted by replay, a proof or a sampled check becomes attributable evidence of misconduct; the paper's own gap 8 relies on exactly that property, which no column records. The counter-argument is not addressed. | text: §6 "for the integrity of a verdict ours merges them, because a signature by the operator authenticates the record, not the computation"; §7.1 "an operator that commits to a verdict before computing it is caught whenever a sampled proof disagrees" | 3: RAILS read only through the manuscript's account | Add an attribution or non-repudiation column to Table 2, or exclude it explicitly in §2.2, and restate the RAILS comparison as a difference in target property | n/a: internal consistency | n/a |

