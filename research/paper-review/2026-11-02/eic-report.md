contract_role: eic
## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: not_assessed

### D3: argumentative_coherence
score: not_assessed

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: warn
trigger: "The argument is recoverable but the reader is slowed by problems such as redundant or overlong sections, undefined or inconsistent terminology"

### D6: venue_fit_and_contribution
score: warn
trigger: "its significance or delineation from prior work is understated, partly unclear, or framed in a way that will limit uptake"

## Review Body

This is the Journal-Fit Reviewer's paper-visible card. No target venue is bound (`criteria_binding_unavailable`). I score D6 on originality and significance alone and make no claim about scope, format or track fit. The venue-scope branch of my Phase 1 fatal trigger cannot be applied, and nothing I found reaches the other branch, "no original contribution". I scored the scoring plan as committed, so there is no dissent. I also checked the manuscript for instruction injection, meaning sentences addressed to reviewers or pleas about scoring. I found none.

The paper is a systematization of evidence that a safety classifier "ran" on an LLM request. It has a case study of the author's own artifact, Hallmark. My editorial reading is that the contribution is real, original in its framing, and positioned explicitly against the closest orderings ([F9], [A32], [A35]). It survives its own heavy scoping. Its citable core is narrower than the four-item contribution list suggests. That core is the split between what was computed (S) and whether the verdict gated the answer and when (S′), the conditional proofs-over-attestation edge, the gap between the integrity order and the order an auditor needs, and the boundary reading of Proof-of-Guardrail. The manuscript itself says that Results 1 to 4 are readouts and that the case study's points follow from the definitions. Yet Sections 4 and 5 together make up more than half the body (about 7,200 of about 12,500 words by my count), and the case study alone is about a quarter of it, plus Appendix A. For that reason D6 is warn rather than pass. The repair is to reframe and rebalance, not to add analysis, so it is not block.

On D5, the argument can always be followed, and the scope devices (Box 1, Table 5, the Section 7.2 limitations) are disciplined. A reader outside zkML is slowed by an overloaded symbol, a class numbering the paper itself has to disown, a long section on costs that the text says support no conclusion, and repository-internal flags in the prose. Each of these is a focused fix.

On disclosure and integrity, which my card treats as an editorial matter: the sole author's employment, the author-run experiments, a trust universe "drawn with the results known", and an AI pipeline that made most revision decisions are all stated openly. That is a strength. One gap remains, recorded as W8. I defer to R1/R2 on the soundness arithmetic of Section 5.3, the characterisation of TEE attacks and the pair counts of Section 4.2. My W5 concerns only how the pair-count sentence reads.

### S1: The statement-first split between "computed" and "gated and timely" is the paper's clearest citable takeaway
**Evidence Anchor**: text: §2.2 "G and T concern the serving path, not the two functions."

Defining S and S′ = S ∧ G ∧ T, and carrying the distinction into Table 2 and the Ignore/Defer strategies, gives readers a reusable vocabulary. The artifact's own two-day-late classifier proofs (Section 5.4) make it concrete.

### S2: Explicit, checkable delta against the closest prior ordering
**Evidence Anchor**: text: §6 "ours are readings of explicit trust sets, so a reader can see which assignment each edge depends on"

The comparison with RAILS names the two places where the orders differ (signed records merged with self-report; proofs over attestation made conditional). This is the right form for an SoK novelty claim.

### S3: The Proof-of-Guardrail boundary reading is a sharp, useful observation
**Evidence Anchor**: text: §4.3 "Either way the attestation covers the wrapper, not the classifier's computation."

The section shows that the closest same-question work attests a wrapper whose classifier runs outside the measured code. It treats the modelling choice for the external API both ways. Readers will cite this.

### S4: Scope is stated once and referenced, not repeated
**Evidence Anchor**: table: Table 5, Section 5.6

Box 1 and Table 5 each serve as a single statement of what is and is not claimed. Later sections point back to them. Structurally, this keeps the hedging from spreading even more than it does.

### S5: Disclosure posture is unusually complete
**Evidence Anchor**: text: AI-Use Disclosure "the other revision and checking decisions were delegated to the pipeline"

The paper states which decisions the author made, which the AI pipeline made, and who ran the experiments. Section 7.2 adds that the trust universe was drawn with the results known. An editor can judge the integrity posture from the manuscript alone.

### S6: The gap list turns the systematization into a research agenda
**Evidence Anchor**: text: §7.1 "A receipt a deployer could hand to an auditor would need more than any single class provides."

Each of the ten gaps is tied to a property and to compositions in the literature. This gives readers a usable takeaway beyond the order.

### W1: The contribution framing foregrounds the parts the paper itself calls derivative
**Severity**: Major
**Evidence Anchor**: text: §4.2 and §5 "Results 1 to 4 are readouts of Table 1, not discoveries" and "what it shows follows from the definitions of Section 4"
**Confidence**: 4 — handling-editor reading of contribution structure; I do not judge the correctness of the assignments

Contributions 2 and 4 claim the order and the worked illustration. The text then says that the order's unconditional results follow from the assignments, and that the case study's points follow from the definitions. What remains original is spread across contributions 1, 2 and 3: the S/S′ split, the conditional edge, the integrity/auditor divergence, and the Proof-of-Guardrail reading. These are not presented as the headline. An SoK reader who finishes the abstract and Section 1 cannot easily say what new insight the paper offers beyond the definitions it fixes. The minimum remedy is to rewrite the contribution list and the abstract around those insights, and to state the order's value as making its assumptions explicit rather than as producing results. Shortening Section 5 (see W3) would match the balance to that framing. The core survives, so this is Major rather than Critical.

### W2: The novelty statement claims priority for the artifact while saying priority is not the point
**Severity**: Minor
**Evidence Anchor**: text: §6 "no peer-reviewed or preprint work reports succinct per-request proofs of a guardrail-classifier verdict composed with an LLM-answer proof"
**Confidence**: 4 — reading of the novelty paragraph against the stated contribution type

The "Search outcome and novelty" paragraph ends with a priority claim about the case study, and the next sentence disclaims priority. The paragraph never states the novelty of the systematization itself. That novelty is stated earlier, in "Orderings of evidence". Readers will quote the priority line. A one-paragraph restatement that leads with the novelty of the systematization would fix this.

### W3: Cost material that supports no conclusion takes a large share of the case study
**Severity**: Minor
**Evidence Anchor**: table: Table 4, Section 5.5
**Confidence**: 4 — structural reading; I did not check the timing values

Table 4 has 13 rows of recorded costs. In Section 5.4 the text spends a long paragraph explaining why the timings "support no direction". Section 5 is about 3,300 words for an illustration the paper says is not a test. Moving most of Table 4 and the boundary discussion to an appendix would leave the case study's three trust points easier to find. The one cost-relevant fact, that proofs spare the verifier the weights at the price of a 738 MB bundle, would remain. The claims would not change.

### W4: The symbol T is overloaded across the two central structures
**Severity**: Minor
**Evidence Anchor**: text: §2.2 and §4.1 "T says that V was computed before Y was released" and "empirical soundness of a tolerance check"
**Confidence**: 5 — direct notation check

T is the timing clause of S′ in Section 2.2 and Table 2 ("Gating (G) and timing (T)"). It is also a trust element in Section 4.1, Table 1 and Figure 1 ({E, P, K, T, Q} for 3a). The paper's main contrast is integrity order against timing, so this overload sits exactly where a reader needs to keep the two apart. Renaming one of them, for example the tolerance element, fixes it.

### W5: The pair-count sentence is hard to parse
**Severity**: Minor
**Evidence Anchor**: text: §4.2 "all but four comparable pairs (one without the dashed edges) involve the bottom class"
**Confidence**: 3 — readability judgment only; counts not verified (left to R1/R2)

It is unclear whether "one" means one pair that stays comparable without the dashed edges, or four minus one. A small table of pair counts under the two readings would remove the ambiguity.

### W6: Class numbering contradicts the order it labels
**Severity**: Minor
**Evidence Anchor**: text: §4.2 "Class numbers are kept only as short keys for the tables, not heights, and the order is not a ladder"
**Confidence**: 4 — exposition judgment

Class 2 sits at the bottom with 0a, class 1 sits above 3b, and class 5 may sit level with 3a, 3b and 4. Numbers invite a ladder reading, and the paper then has to warn against it in several places. Mnemonic labels (SELF, LOG, REPLAY, STAT, REFEREE, TEE, PROOF) would remove the need for the warnings.

### W7: Repository-internal flags and undefined qualifiers appear in the prose
**Severity**: Minor
**Evidence Anchor**: text: Box 1 "The backend is not qualified"
**Confidence**: 4 — exposition judgment

Box 1 and later sections use config-style flags (`hiding_claim: false`, `qualified_backend: false`) and profile names (`y-attnout-w12`). They also use "unqualified parameters" without saying in prose what qualification would require. Section 7.1, gap 7 lists the missing pieces later. Defining "qualified" where it first appears and dropping the flag syntax would help general readers.

### W8: The competing-interest statement does not say whether the employer works in any compared evidence class
**Severity**: Minor
**Evidence Anchor**: absence: Competing Interests — expected a statement of whether the author's employer offers or develops products or services in any compared evidence class; checked Competing Interests, Funding, Author Contributions, AI-Use Disclosure, Section 7.2
**Confidence**: 3 — editorial disclosure practice; I make no assumption about the employer's business

The paper ranks attestation, logs and proofs against each other. Readers will want to know whether the author's employer has a commercial stake in any of these, beyond the statement that Hallmark itself is not a product. One sentence would settle it either way.

### W9: The literature base is described without coverage counts
**Severity**: Minor
**Evidence Anchor**: absence: Section 3 — expected counts of sources screened, excluded and included per strand; checked Section 3, Section 7.2, Data and Artifact Availability, References
**Confidence**: 3 — contribution-level concern; method adequacy is D1's call

For an SoK, how complete the systematization is depends on how much of the field it covered. Section 3 gives the strands, one search date and the inclusion criteria, but no screened or included counts. Readers therefore cannot tell how representative the few systems per class are.

### W10: In the panel copy the figures are a specification and a file pointer
**Severity**: Minor
**Evidence Anchor**: figure: Figure 1 and Figure 2, Sections 4.2 and 5.2
**Confidence**: 3 — I checked that `docs/paper/main.tex` draws Figure 1 in TikZ and includes `trust-boundary.png` for Figure 2, but I did not view the rendered PDF

In the review copy, Figure 1 appears as a `figure1-spec` block and Figure 2 as a repository path. A reader of this version cannot judge whether the figures are legible or show the equal weighting of the two readings that the caption promises. The submitted version should carry the rendered figures.
