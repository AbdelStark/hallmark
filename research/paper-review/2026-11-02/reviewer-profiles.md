# Field Analysis Report

Phase 0 (field_analyst_agent). No reviewer dispatched; manuscript not edited. No web search or external model call was used.

## Paper Basic Information
- **Title**: Proofs, Attestation and Logs: What a Verifier Must Trust to Know a Safety Classifier Ran
- **Author**: Abdelhamid Bakhta, Lucid Computing (sole author, corresponding)
- **Abstract length**: about 249 words
- **Full text length**: about 16,800 words including references and appendix (8 sections, Box 1, Appendix A, 7 main tables plus Table A1, 2 figures: Figure 1 is given as a `figure1-spec` block, Figure 2 as a pointer to an SVG in the repository)
- **Number of references**: 97 entries in the reference list (bracketed keys in strands A, B, C, D, E, F, plus [SASH]); the text says 81 were cited before the final revision
- **Language**: English; review in English

## Field Analysis

| Dimension | Analysis Result |
|-----------|----------------|
| Primary Discipline | Computer security: verifiable computation and evidence of execution for ML inference (applied cryptography and trusted computing, as applied to LLM guardrails) |
| Secondary Disciplines | Technical AI governance and algorithmic auditing; trusted computing and remote attestation / transparency-log systems; ML systems (quantized LLM inference, determinism) |
| Research Paradigm | Theoretical/conceptual analysis (a systematization-of-knowledge, SoK) with an illustrative case study; no hypothesis-testing quantitative component |
| Methodology Type | Literature-based systematization (four-strand search with stated inclusion rule, annotated per source) + formal modelling (trust universe U, trust sets τ, inclusion preorder, statements S and S′, seven-strategy adversary) + single-instance case study of an author-built artifact (Hallmark) with recorded engineering measurements and engineered-mutation rejection tests |
| Target Journal Tier | `criteria_binding_unavailable`: no author-confirmed Review Target Context was supplied, so no venue/track/article type is bound and the panel makes no venue-alignment claim. Field-general observation only: the manuscript is shaped as a security SoK (explicit trust model, threat model, comparison tables, failure records, "Hallmark contributes no proof system") and is written for a top-tier security or technical-AI-governance readership in ambition; whether its contribution meets that bar is for the panel to judge, not this card |
| Paper Maturity | Pre-submission. Basis: complete structure with abstract, threat model, method section, results, related work, limitations, data/artifact availability, ethics, CRediT, competing interests, funding and AI-use disclosure; references fully formatted with DOIs/identifiers; the text records several prior revision rounds and responses to earlier (simulated) reviewers; claims are heavily scoped (Box 1, Table 5). Remaining production gaps visible to the analyst: Figure 1 exists only as a specification block, Figure 2 is an external file pointer, and the bracketed-key citation style would need conversion for any numeric-citation venue (the text says the PDF/LaTeX version already does this) |

**Cross-disciplinary note.** This paper is highly cross-disciplinary (applied cryptography, trusted hardware, transparency logging, ML systems, AI governance). Disciplinary coverage strategy: Reviewer 2 takes the core security discipline across the mechanism families the title names (proofs and attestation, with logs and delegation as they enter the order); Reviewer 3 takes the governance and audit-practice perspective that the paper's "auditor's order", gap list and regulatory readings address; Reviewer 1 takes neither domain and instead audits the systematization as an argument and as a procedure.

**Manuscript-as-data check.** No text in the manuscript was found that addresses the reviewers or the panel (no directives about reviewer identity, leniency, decision or what to ignore). The AI-Use Disclosure states that a simulated peer review and integrity checks were part of the drafting pipeline and that the author withdrew verify-versus-rerun direction claims "after the final simulated review"; this is a disclosure to be weighed, not an instruction, and the panel should not anchor on the outcomes of those earlier rounds.

## Recommended Target Journals (Top 3)

Not resolved. With `criteria_binding_unavailable`, this analysis does not select or substitute a venue and the Journal-Fit Reviewer is configured field-general. For the author's orientation only, and not used to configure any card, the venue families whose readership matches the manuscript's form are:
1. A security-venue SoK track (systematization papers in computer security and privacy) — the paper's form (trust sets, threat model, failure records, comparison tables) matches that genre most closely.
2. A survey/systematization journal in computing (e.g. *ACM Computing Surveys*, listed in the skill's reference table) — fit would depend on broadening the literature base beyond guardrail verdicts.
3. A technical-AI-governance or accountability venue (the paper already cites works from Technical AI Governance workshops and FAccT) — fit would depend on the auditor-facing material (Table 2, Section 7) carrying the contribution.

If the author confirms a target, Phase 0 should be rerun with that Review Target Context before Phase 1.

## Reviewer Configuration Cards

### Reviewer Configuration Card #1

**Role**: EIC
**Display role**: Journal-Fit Reviewer
**Identity Description**: Field-general handling editor for systematization-of-knowledge papers in computer security, with prior service chairing SoK submissions on verifiable computation and trusted hardware, and experience adjudicating papers in which the authors' own artifact serves as the case study. Configured without a bound venue (`criteria_binding_unavailable`).
**Review Focus**:
  1. Whether the systematization delivers insight beyond its inputs: the paper itself states that Results 1 to 4 are "readouts of Table 1, not discoveries" (Section 4.2), so judge whether the contributions that remain (the statement-first S/S′ split, the conditional proofs-over-attestation edge, the integrity-vs-auditor order divergence, the Proof-of-Guardrail boundary reading) are significant enough to carry an SoK.
  2. Balance and framing: whether the Hallmark case study (Section 5, roughly a third of the body) is proportionate for a paper that says the artifact is "not a system contribution or a test", and whether the four listed contributions match what Sections 2 to 7 deliver.
  3. Novelty statement and positioning: whether the bounded novelty claim (Section 6, "Search outcome and novelty") and the comparison with RAILS [F9], Peng et al. [A32] and Xia et al. [A35] establish a clear delta for a general security readership.
  4. Disclosure and integrity posture as an editorial matter: sole author employed by the company under which the artifact was built, experiments run by the author, trust universe drawn "with the results known" (Section 7.2), and an AI pipeline that drafted and revised the manuscript and made most revision decisions (AI-Use Disclosure).
**Will particularly care about**: Whether, after all the scoping (Box 1, Table 5, Section 7.2), a reader is left with a clear, citable takeaway, or whether the hedging has thinned the contribution to a restatement of definitions. Also whether the paper is readable at its length for readers outside zkML.
**Possible blind spots**: Will not verify the soundness arithmetic of Section 5.3, the TEE attack characterisations, or the internal consistency of the pair counts in Section 4.2; will lean on R1 and R2 for correctness and on R3 for practical value. Without a bound venue, cannot judge format, page-limit or track-specific criteria.

### Reviewer Configuration Card #2

**Role**: Peer Reviewer 1
**Display role**: Peer Reviewer 1
**Identity Description**: Researcher in formal security modelling and SoK methodology, specialising in trust-assumption calculi and order-theoretic comparison of security mechanisms (preorders, lattices of assumptions, threat-model formalisation), who has reviewed SoKs whose taxonomies are later contested. Because this is a conceptual paper, the "methodology" seat is adjusted to argumentation logic and formal method, plus the literature-base procedure that the systematization rests on.
**Review Focus**:
  1. Validity and robustness of the order as a construction (Section 4.1–4.2): whether ⪯ is correctly defined as a preorder with a partial-order quotient; whether the conventions (τ = U for operator-reliant classes, E and P assumed for every class, K bundling hash/signature/commitment assumptions with proof-system soundness) are principled or chosen to produce the results; how sensitive each result is to the granularity of U (the paper concedes U was drawn with results known); and whether the pair counts (21 pairs; 15 vs 12 comparable; 6 vs 9 incomparable above the bottom) follow from Table 1.
  2. The statement and adversary formalisation (Section 2.2–2.3): whether S, S′ = S ∧ G ∧ T and the six properties are well defined and mutually exclusive; whether the seven adversary strategies are complete for the stated goal (e.g. collusion between operator and enroller, a dishonest verifier, a third-party classifier API outside O, which Section 4.3 handles by a modelling choice); and whether "defends against" is defined tightly enough to support Table 2's per-class claims.
  3. The literature-base procedure (Section 3): reproducibility of a four-strand search run on a single date with unspecified search terms, inclusion rule application, the uneven reading depth (69 of 81 re-read; several class placements from abstract or title level only), and whether class assignments of systems the author did not run are adequately qualified.
  4. Inferential discipline of the case study (Section 5.4–5.6, Table 4): whether each claimed "illustration" follows from the definitions as stated, whether the paper avoids drawing any cost or speed conclusion from timings with unmatched boundaries, and whether Table 5 statuses are each traceable to a recorded experiment.
**Will particularly care about**: Whether an inclusion order over hand-assigned trust sets can bear the weight of a headline claim ("proofs sit above attestation only if…"), given that the condition is itself a choice about how K is partitioned. The reviewer will want to see what alternative, equally defensible universes would do to each result.
**Possible blind spots**: Will not judge whether individual trust-element assignments are technically correct for each mechanism (e.g. whether opML truly needs D, whether Nitro's root is correctly characterised, whether the FRI soundness approximations are right); that is R2. Will not weigh practical or regulatory usefulness (R3).

### Reviewer Configuration Card #3

**Role**: Peer Reviewer 2
**Display role**: Peer Reviewer 2
**Identity Description**: Senior applied-cryptography and systems-security researcher working on verifiable and confidential ML inference, with hands-on experience of transparent proof systems (STARKs, FRI-based polynomial commitments, Circle STARKs over Mersenne-31) and of confidential computing for GPU inference (SEV-SNP, TDX, H100 confidential computing, Nitro), and familiar with the SNARK vulnerability and weak Fiat–Shamir literature.
**Review Focus**:
  1. Correctness of the class 5 material and the Hallmark soundness analysis (Sections 4.3, 5.3, Table 3): the S-two `security_bits` formula reading, the 336 / 100 conjectured figures, the proven-regime approximations (about 41.5 and 89 bits in unique decoding, at most about 50 and 176 up to the Johnson bound), the QM31 and hash caps, the union bound over 23 proofs (about 95.5 bits), and whether STARKs' "no trusted setup" and the N element for KZG-style systems are stated correctly.
  2. Correctness of the class 4 and class 2/3 characterisations: the W_v / W_g / W_c attestation roots, the reading of Proof-of-Guardrail [B24] as attesting a wrapper whose classifier runs outside the measurement, the TEE attack record (Foreshadow, ÆPIC Leak, CacheWarp, TEE.fail), and the trust elements assigned to replay, TOPLOC/SVIP, refereed and optimistic delegation, and transparency logs.
  3. Soundness of the Hallmark relations and composition as security engineering (Sections 5.1–5.2, Appendix A): complete-input constraint with prefix mask and padding, limb decomposition against modular aliasing, caller-side enrollment and reconstruction, the host join β as residual P, the linked bundle verified only by the prover's own implementation, and what 122 + 16 + 22 engineered mutations do and do not show.
  4. Completeness of strands A to C and the bounded novelty claim: whether the zkML, TEE-inference, verifiable-inference and audit-log literature is covered well enough that "no peer-reviewed or preprint work reports succinct per-request proofs of a guardrail-classifier verdict composed with an LLM-answer proof" is defensible, and whether Tables 6–7 position competing systems fairly.
**Will particularly care about**: Whether the paper's quantitative cryptographic statements are exactly right and correctly labelled (conjectured vs proven, per-proof vs bundle), and whether the attestation side is treated with the same rigour as the proof side rather than being represented mainly by its attack record.
**Possible blind spots**: May treat the order as obviously true or obviously trivial depending on prior views, without auditing it as a formal construction (R1). May undervalue the governance and auditor-facing contribution and the regulatory readings (R3). May push for qualification work (provable bounds, independent verifier, fuzzing) that is outside an SoK's scope; the synthesizer should weigh such requests against the paper's stated non-claims.

### Reviewer Configuration Card #4

**Role**: Peer Reviewer 3
**Display role**: Peer Reviewer 3
**Identity Description**: Technical AI governance researcher and former third-party AI assurance practitioner, specialising in audit evidence and record-keeping for deployed LLM services (structured access, layered audits, the EU AI Act logging and record-keeping articles and the GPAI Code of Practice), who has designed evidence requirements that operators, auditors and regulators can actually exchange. This seat reads the paper as its intended end user: the auditor who must decide what to ask an operator for.
**Review Focus**:
  1. The auditor's view (Table 2, Section 4.4 third observation, Section 7.1): whether the "computed / gated / before release" split maps onto what audits and regulators actually need, whether Table 2's "possible" entries are usable as procurement or audit requirements, and whether the proposed compositions toward S′ (attested gating wrapper plus proof; pre-release log plus later proofs; IMMACULATE-style sampling) are operationally coherent.
  2. Enrollment and roles as governance (Sections 2.1, 5.2, gap 5): the borrowing of the RATS Reference Value Provider role, who should enroll, threshold and fallback-policy changes, the treatment of declared degraded modes (fail-open) as indistinguishable from Skip, and the paper's deferral of "which institution should enroll" to future work.
  3. Accuracy and restraint of the regulatory readings: AI Act Art. 12(1), 19(1), 26(6) and Code of Practice Measures 5.1 and 7.3 as cited, the "high-risk" disclaimer, the retention-scale remark on a 737,858,641-byte bundle per request, and whether the paper avoids implying a mandate it disclaims.
  4. Real-world transfer and overlooked assumptions: synthetic classifiers (one never blocks, one blocks the benign demonstration prompt), a 96-byte input, single-prompt case, capture provenance left open, privacy of user prompts under public witnesses, multi-rail and output-rail pipelines and streaming, and whether "evidence that a guardrail ran" could be misused as a safety signal despite Box 1.
**Will particularly care about**: Whether a deployer or auditor reading the paper could act on it: what evidence to request for which audit question, and what the paper's own case (classifier proofs accepted two days after the answer) means for audit practice.
**Possible blind spots**: Will not verify cryptographic or TEE technical claims (R2) or the formal properties of the order (R1); may over-weight deployability for a paper that explicitly presents itself as a systematization with an illustration, not a deployment.

### Fifth seat (fixed, no card)

The Devil's Advocate is the fixed fifth execution seat (`devils_advocate_reviewer_agent`). It receives no dynamic configuration card and is not configured by this analysis.

## Review Strategy Recommendations
- **Contribution-vs-hedging tension is the central editorial question.** The manuscript concedes that Results 1–4 are readouts of its own assignments, that the case study is an illustration rather than a test, that timings settle nothing, and that no security level, hiding, attestation or enforcement is claimed. Reviewers should evaluate what survives these concessions rather than re-raise limitations already stated in Box 1, Table 5 and Section 7.2, and should flag only concessions that are missing, misplaced, or inconsistent across sections.
- **Non-overlap of R1 and R2 on the order.** R1 asks whether the order is a sound and non-arbitrary construction given any assignments; R2 asks whether each mechanism's assignment (and each cited failure) is technically correct. Disagreements between them on the conditional proofs-over-attestation edge are expected and informative; the synthesizer should keep the two strands separate.
- **Numbers to check internally (no external sources needed):** pair counts in Section 4.2; soundness arithmetic in Section 5.3 and Table 3; the 122-case total in Appendix A (63 + 18 + 3 + 38); Table 4 boundaries vs the Section 5.4 discussion; the cold-start share of the 0.807 s classifier verification; consistency of dates (answer proofs 2026-10-26, classifier proofs 2026-10-28, rerun 2026-10-30) across Sections 5.4, 5.5 and Data Availability.
- **Citation verification is out of scope for this panel run.** No web access is permitted, and many sources are recent preprints (2026) or tools/blogs; reviewers must not assert that a cited work does or does not exist or says something it does not, and should instead flag places where the manuscript itself reports shallow reading depth (Section 3) and the claim rests on that source.
- **Conflict-of-interest and provenance.** Author-built artifact, author-run experiments, employer-funded, AI-pipeline drafting with delegated revision decisions, and prior simulated review rounds. The EIC should treat these as disclosure-adequacy questions; no seat should let them substitute for evidence-based findings.
- **Expected complementarity and tension.** R2 may ask for qualification work (provable bounds, independent LLM verifier, witness-level fuzzing) that R3 and the EIC may see as beyond an SoK; R3 may ask for actionable audit guidance that R1 may see as diluting the formal contribution. The Devil's Advocate is best placed to test the strongest counter-claim: that the order is a relabelling of assumptions chosen to reach a pre-set conclusion, and that the case study adds no information beyond the definitions.
