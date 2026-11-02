# Phase 2 Review Card — Peer Reviewer 1 (methodology seat)

Venue binding: criteria_binding_unavailable. No target venue is bound, so this card makes no venue-alignment claim and emits no constructive-review-findings companion.

contract_role: methodology
## Dimension Scores

### D1: methodology_rigor
score: warn
trigger: "an underspecified threat model that does not change any headline result"

The formal construction is sound as stated: ⪯ is a correctly defined preorder, the quotient is a partial order, and the pair counts in §4.2 follow from Table 1 (checked by hand below). The case study keeps its timings away from any cost conclusion, and every Table 5 status traces to a named record. What keeps this at warn and not pass is procedural. Sensitivity to how the universe is cut is worked out for K only, not for P or D, which carry Results 2 and 5. The adversary strategies are never applied class by class. The literature search cannot be reproduced from what is reported. And one replay claim about the LLM rests on a single agreement. Each gap can be fixed by rewriting or by reporting what was done. None of them overturns the main result, which is that most classes above the bottom cannot be compared and that the proofs-over-attestation edge is conditional.

### D2: domain_accuracy
score: not_assessed

### D3: argumentative_coherence
score: warn
trigger: "some secondary claims are slightly overstated"

The thesis holds together and is carefully hedged. The headline edge is stated as conditional, the edges that are mere readouts are labelled as such, and the case-study points that follow from definitions are not passed off as tests. The overstatements are in secondary claims. "Replay needs less trust than the proofs" is presented as a finding of the case, but it depends on treating the verifier's own rerun code and a proof circuit as the same trust element P. The LLM version of that claim is drawn from one reproduction. And "every class's failure record" is backed by recorded attacks for only two of the six compared classes.

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

I read the manuscript as a systematization whose method is formal (an inclusion order over hand-assigned trust sets), plus a literature-collection procedure and one worked artifact. I checked the order's construction, the pair counts, the statement and adversary model, the literature procedure, the case study's inferences, and the numbers it reports. Where the manuscript points to repository records, I spot-checked them: `research/evidence/native-rerun-classifiers-2026-10-30.json`, `native-rerun-llm-2026-10-30.json`, `circle-reference-2026-10-28.json` and `research/probes/native-rerun/measure_native_rerun.py`. The values I checked match the manuscript: classifier medians 0.274–0.284 ms, 0.979–0.991 ms and 199.9–203.8 ms; LLM medians 0.769 s and 0.235 s with n = 5; first cold verifier process 0.345 s; S-two proving 24.06 s; prover commands 50.03 s; 16 join-level binding rejections.

Recomputed arithmetic, none of which falls under a bounded statistical procedure:
- Pair counts. Of the 21 pairs, the 11 that involve the bottom are all comparable. Above the bottom, the comparable pairs are 1–3b, 3a–5, 3b–5 and 4–5. That gives 15 comparable pairs, with 6 of the 10 pairs above the bottom incomparable. Without the dashed edges, only 1–3b is comparable above the bottom, giving 12 comparable pairs, with 9 of 10 incomparable. All of this matches §4.2.
- FRI orientation figures. Unique decoding gives 100 × −log₂ 0.75 ≈ 41.5 and 16 + 80 × −log₂(17/32) ≈ 89.0. The Johnson bound gives 100 × 0.5 = 50 and 16 + 80 × 2 = 176.
- Union bound and formula figures. log₂ 23 ≈ 4.52, so the bundle has about 95.5 conjectured bits. The formula figures are 16 + 4 × 80 = 336 and 0 + 1 × 100 = 100.
- Mutation and token counts. 63 + 18 + 3 + 38 = 122 tampering cases; 14 + 20 + 2 + 2 = 38 LLM mutations; 15 + 3 + 3 + 1 = 22 invalid witnesses; 16 join mutations; 25 + 7 = 32 positions; 8 answer tokens with 7 token links.
- Native rerun total. The nine native classifier medians sum to about 0.609 s, which matches "about 0.61 s".

All of these are consistent.

Things I noted but do not count as defects, because the paper discloses them and they do not move a result. Giving operator-reliant classes τ = U places the bottom by convention, and 11 of the 15 comparable pairs come from that convention. Assuming E and P for every class means the case study's conclusion that "residual trust sits in enrollment and host checks" was built in. §4.2 and §5.4 say both things openly and report the incomparability counts above the bottom separately, which is the right control.

### S1: The order is correctly constructed and its non-antisymmetry is acknowledged
**Evidence Anchor**: text: §4.1 "Inclusion is reflexive and transitive, so ⪯ is a preorder. It is not antisymmetric on classes"

The relation is defined as reverse inclusion, called a preorder, and turned into a partial order only through the quotient that Figure 1 draws. Self-report and signed records are merged in that quotient for a stated reason. This is the right formal treatment, and many SoK orderings skip it.

### S2: The paper says which results are readouts and which are conditional
**Evidence Anchor**: text: §4.2 "Results 1 to 4 are readouts of Table 1, not discoveries"

The paper does not present inclusion results as findings. It names the element that separates each pair. It draws the proofs-over-attestation edge with the same weight as its negation, and it states two conditions that defeat that edge: separating proof soundness from K, and needing a structured reference string (N). This is the main protection against the concern my seat had going in, which was whether a headline edge was bought by how K is partitioned.

### S3: Pair counts reproduce from the trust sets
**Evidence Anchor**: table: Table 1, column "Trust set τ"

Every count in §4.2 (21; 15 versus 12; 6 versus 9 above the bottom; four comparable pairs not involving the bottom, one of them without the dashed edges) reproduces from the Table 1 sets under both readings.

### S4: The timing discussion draws no conclusion its boundaries cannot carry
**Evidence Anchor**: text: §5.4 "They support no direction, for three reasons."

The paper lists the boundary mismatches between verification and rerun: process start, model loading, compiled-in roots, a cold first process, and a pure-Python interpreter that also hashes the weights. It then declines to state a direction, and Table 5 marks the cost profile as "Not established". This is the right inferential discipline for single-run figures.

### S5: Every placement status traces to a recorded experiment
**Evidence Anchor**: table: Table 5, column "Basis"

Each row names its experiment or section. The records I opened agree with the reported values.

### S6: The negative evidence is bounded honestly
**Evidence Anchor**: text: Appendix A "These single-value mutations test that the listed constraints exist, not that the gadgets are complete."

The paper separates engineered mutations from witness-level fuzzing and from an adversarial evaluation, so the 122, 16 and 22 counts are not read as evidence of soundness.

### S7: Derived soundness figures are labelled as the author's own approximations
**Evidence Anchor**: text: §5.3 "This is our own derivation, not a statement of any source."

The orientation bits and the union bound are labelled as the author's own, as upper approximations, and as not being a proven bound.

### W1: Granularity sensitivity is worked out for K only, while P and D carry Results 2 and 5 and the replay-versus-proof claim
**Severity**: Major
**Evidence Anchor**: text: §4.1 "a correct implementation of C and M, whether in the verifier's code, a delegated program, a measured image or a circuit"
**Confidence**: 4 (order-theoretic construction; checked by recomputing the inclusions under alternative partitions)

P is one element shared by a verifier-run reimplementation (replay), a delegated program (3b), a measured image (4) and a constraint system (5). These are different artifacts, maintained by different parties, and they fail in different ways: the paper's own §4.3 lists under-constrained circuits and ghost weights for class 5. If P is split by where the implementation lives, P_rerun for replay and P_circuit with the verifier code for proofs, then replay {E, P_rerun} and proofs {E, P_circuit, K} become incomparable. Result 5 then disappears, and so does the abstract's claim that "replay needs less trust than the proofs". In Hallmark itself, the replay uses a pure-Python reference interpreter (§5.4) and the proof uses a gate-level AIR, so the two P's are different code. Result 2 (replay above 3b) likewise depends on D and P being the same element in both classes. §7.2 says "Section 4.2 states which edges depend on its granularity", but §4.2 does this only for K and N. Minimum remedy: add a short sensitivity paragraph or table that splits P (and K into hash/signature/commitment/soundness) and reports which of Results 1–5 survive each split. Then qualify Result 5 and the abstract sentence as holding under the single-P convention. A stronger option, at moderate effort: present the order under two or three named universes side by side, as Figure 1 already does for K. This would likely strengthen the headline "mostly incomparable" result while weakening the replay claim, and which universe to put first is the author's choice.

### W2: The universe is not closed under the parties the classes actually rely on
**Severity**: Minor
**Evidence Anchor**: table: Table 1, row "2 Signed / logged record", trust-set cell "U (writer is O); permanence: K, auditors"
**Confidence**: 4 (definition of U in §4.1 compared against Table 1 and §4.3)

Table 1 makes class 2's permanence depend on "auditors", and §4.3 has to add an element for the third-party classifier API ad hoc. Neither is in U. Class 2's place at the bottom does not change, because τ = U applies anyway. But the table writes a trust set using elements the order does not define, and the third-party case shows that U is missing a generic "honest party outside O" element, which H only partly covers. Remedy: either add such an element to U and say where it enters, or drop "auditors" from the Table 1 cell and explain permanence in prose.

### W3: The adversary strategies are defined but never applied class by class
**Severity**: Minor
**Evidence Anchor**: absence: §4 class analysis — expected a per-class record of which of the seven strategies (Skip, Swap, Substitute, Replay, Misreport, Ignore, Defer) each class defends against under its trust set; checked §2.3, §4.2, §4.3, §4.4, Table 1, Table 2 and §5.4
**Confidence**: 4 (read every section that uses "defends against" or names a strategy)

§2.3 defines "defends against" carefully, but the definition is used only for Hallmark in §5.4. Table 2 records properties (capture provenance, G/T, hiding), not strategies. Defer and Skip interact differently with replay, logs and attestation, so a reader cannot check from the paper whether each class's trust set actually defeats each strategy. Some modelling choices are also only implicit: collusion between operator and enroller is excluded because the enroller is assumed honest, and the case of a request disclosed by the operator is folded into capture provenance. Remedy: a seven-by-seven table (strategy × class) built from the existing definitions. It would also make the S versus S′ split in Table 2 easier to audit.

### W4: The literature search cannot be reproduced from what is reported
**Severity**: Major
**Evidence Anchor**: text: §3 "Each strand was searched on 2026-10-30 with public topic terms in web search and on primary pages"
**Confidence**: 3 (SoK procedure norms; I found no search log under the repository's docs or research records outside research/source, which I did not open)

The paper reports neither the search terms nor any counts (identified, screened, included, excluded per strand). Searches ran on one day, through general web search, and the AI-use disclosure says an automated pipeline did them. The inclusion rule is stated, but how it was applied cannot be checked. Two claims depend on this procedure: that the class list is complete, and the negative novelty statement in §6 ("no peer-reviewed or preprint work reports …"). The statement is hedged with "to our knowledge", but a reader cannot re-run the search that supports it. Minimum remedy: report the query strings for each strand and the sources searched, with counts at each stage, ideally as a supplementary table in the repository. If no log exists, re-run a documented search and say that it was re-run.

### W5: The reading-depth denominators do not match the current reference list
**Severity**: Minor
**Evidence Anchor**: text: §3 "re-read the cited passages from source full texts for 69 of the 81 references then cited"
**Confidence**: 3 (counted 97 entries in the reference list; the stated cohorts cover 81 + 7 + A22)

The reference list now has 97 entries. §3 accounts for 81 then cited and 7 added in the final revision (A22 overlaps the 81). That leaves roughly nine references whose reading depth is not stated, and some of them may place systems in classes. Remedy: give the reading depth for the current list, for example a column in the annotation file, and report it for every source used to place a system in a class.

### W6: The LLM replay claim is inferred from one reproduction, not from exactness by construction
**Severity**: Minor
**Evidence Anchor**: text: §5.4 "The same holds for a verifier that holds the TinyLlama weights, since a rerun under the proved relation reproduced the proved answer"
**Confidence**: 3 (read the exp-R1 script: the rerun is a PyTorch harness model with a bf16 calibration pass; I did not establish whether its forward pass is integer-exact)

Result 5 requires the computation to be an exact integer program, so that D holds by construction. For the classifiers the paper says this outright. For TinyLlama, the support is that a rerun produced the same eight token ids once, on one prompt. The rerun recomputes calibration in bf16 and runs a torch model, and the paper does not state that this path is bit-exact with the proved integer profile. One agreement on the final token ids does not establish D, and the paper itself warns about this for fp32 ("a single case rather than an agreement rate"). Remedy: either state and justify that the harness implements the integer profile exactly, or limit the LLM sentence to "reproduced in one run".

### W7: The exp-R1 provenance was reconstructed after the fact, and verifier timings lack repetition and thread settings
**Severity**: Minor
**Evidence Anchor**: text: §5.5 "The exp-R1 records carry the platform, core count and thread settings but not the code commit or the CPU model"
**Confidence**: 4 (checked the exp-R1 JSON records: no commit field, no CPU model)

The paper discloses this, and no conclusion depends on these timings, so the defect is limited to reproducibility. The commit and CPU model come from the author's statement, not from the record. The verification rows in Table 4 are n = 1 or 2 with thread configuration not recorded. Remedy: rerun exp-R1 with the updated script so the record carries commit and CPU, and if the timings stay in the paper, repeat the verifier runs warm.

### W8: The cross-class claim about failure records is supported by recorded failures for only two classes
**Severity**: Minor
**Evidence Anchor**: text: §4.4 "Attacks show where the residual trust goes: to physical security and keys at class 4 [B16]"
**Confidence**: 3 (compared the §4.4 claim with the evidence cited per class in §4.3 and Table 1)

Contribution 3 and §4.4 say this claim "comes from the failure records, not from the sets". Recorded failures are cited for classes 4 and 5. For replay, logs, 3a and 3b, the "Characteristic failure" column lists failure modes (nondeterminism, a lying writer, in-tolerance perturbation, collusion), not observed incidents. The claim is plausible, but its evidential basis is uneven. Remedy: either cite recorded failures for the other classes, or reword to "the failure records of classes 4 and 5, and the failure modes of the others".

## Arithmetic Receipts

no_recomputable_statistics: The manuscript reports no test statistic, p-value, degrees of freedom or mean of integer-scale data; its quantities are timings (medians and ranges with n = 5 or 50), byte sizes, counts and soundness-bit figures, which I recomputed by hand in the Review Body, and none falls under p_from_test_statistic, grim, grimmer or n_from_df.
