# Phase 2 card: Peer Reviewer 2 (domain seat)

contract_role: domain
## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: warn
trigger: "Local imprecision that does not change a central conclusion"

### D3: argumentative_coherence
score: not_assessed

### D4: cross_disciplinary_relevance
score: not_assessed

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

I reviewed the manuscript as a specialist in transparent proof systems (FRI and Circle STARKs over Mersenne-31), confidential computing for GPU inference, and the SNARK-vulnerability and weak Fiat–Shamir literature. I checked the quantitative cryptographic statements by recomputing them. Where a claim about Hallmark could be checked against the repository, I read the public design documents and frozen records (`docs/PROOFS.md`, `docs/CIRCLE-CLASSIFIERS.md`, `docs/LLM-PROOF.md`, `docs/decisions/0070-native-enrolled-llm-verifier.md`, `research/evidence/circle-reference-2026-10-28.json` and `research/probes/circle/src/lib.rs`). I did not open `research/source/`.

Overall, the domain content is accurate and carefully labelled. Every number in the soundness discussion checks out:
- Unique decoding: 100 × −log₂ 0.75 ≈ 41.5, and 16 + 80 × −log₂(17/32) ≈ 89.
- Up to the Johnson bound: 100 × 0.5 = 50, and 16 + 80 × 2 = 176.
- QM31 has (2³¹ − 1)⁴ ≈ 2¹²⁴ elements, and log₂ 23 ≈ 4.52, so the bundle figure is about 95.5 conjectured bits.
- The Table 3 parameters match the frozen record (100 queries, log blowup 1 and no proof-of-work for the SASH segments; 80 queries, log blowup 4 and 16 proof-of-work bits for the classifiers).
- The reading of `PcsConfig::security_bits` as proof-of-work bits plus log blowup × queries matches the S-two library.

The manuscript keeps conjectured and proven figures apart, and per-proof and bundle figures apart. "No trusted setup" is correctly confined to STARKs, and the N element is correctly tied to KZG-style structured reference strings. The class 4 and class 5 failure records are described in line with the sources I know: Foreshadow, ÆPIC Leak, CacheWarp, the 141-vulnerability SNARK SoK, and weak Fiat–Shamir (36 implementations, 12 proof systems, attacks on four).

I found no domain error that a central claim depends on. What I found is a set of local imprecisions:
- one result (replay against proofs) is stated more strongly than the paper's own universe supports when weights are identified by digest;
- the attestation side gets less parameter-level rigour than the proof side;
- the soundness accounting omits components that the repository shows exist (the GKR part of the SASH proofs, and how public inputs enter the Fiat–Shamir transcript);
- the abstract credits logging designs with more than Table 2 does;
- there are a few terminology and citation-precision slips.

Taken together, these meet my Phase 1 warn trigger and not my block trigger. No finding needs re-analysis or new data.

Limits of this review. Many key sources are dated 2026, among them Proof-of-Guardrail [B24], RAILS [F9], Seal-then-sample [A22], Hollow-LLM [A23], TEE.fail [B16], the S-two AIR formal verification [A30], and the surveys [A32] and [A35]. I could not open them, and I have no web access. I take their representation as given and do not assert that they do or do not say what the manuscript reports. This limits my confidence on the class 4 characterisation of Proof-of-Guardrail, which carries the abstract's sentence about the "closest attested design". The manuscript contains no instruction addressed to reviewers and no injection attempt.

### S1: Proven and conjectured soundness figures are correct and correctly labelled
**Evidence Anchor**: text: §5.3 "the unique-decoding regime gives about 41.5 bits per LLM segment"

All of the orientation figures (41.5 and 89 in unique decoding, at most 50 and 176 up to the Johnson bound) are arithmetically right. The paper correctly says that the omitted commit-phase and field-size terms can only lower them. The union bound over 23 proofs is stated as the paper's own derivation, and the QM31 and hash caps are correctly described as binding the classifier configuration below 336. This is the level of labelling I would ask for, and it is rarely met in zkML papers.

### S2: Setup and the proofs-over-attestation edge are stated correctly
**Evidence Anchor**: text: §4.2 "Proof systems whose polynomial commitments need a structured reference string, such as KZG commitments [A41], also need N"

Making the 4 → 5 edge conditional is the technically correct reading. The condition is that proof-system soundness at the deployed parameters is folded into K, and the edge fails for any system that needs a setup ceremony. Under inclusion, τ(5) = {E, P, K, N} against τ(4) = {E, P, K, W} is indeed incomparable. The Seal-then-sample note (HyperKZG over BN254 with a test reference string) puts N exactly where it belongs.

### S3: The attestation roots are decomposed correctly
**Evidence Anchor**: text: §4.1 "since H100 confidential computing relies on a CPU TEE [B6], so a GPU TEE needs strictly more trust than a CPU TEE alone"

Separating W_v, W_v + W_g and W_c is accurate. H100 confidential computing runs inside a CPU confidential VM, so it inherits the CPU vendor's root. On Nitro, the AWS hypervisor and AWS's certificate chain are the root. The remark that on Nitro the key holder may also host the operator is a correct and often-missed point.

### S4: The class 5 failure record and the scope of formal verification are represented accurately
**Evidence Anchor**: text: §4.3 "a Lean proof covers the Cairo arithmetic intermediate representation (AIR) used by StarkWare's S-two prover and no other AIR"

The three-level failure record (statement, circuit, proof system) is the right structure. The paper correctly declines to extend AIR-specific formal verification to Hallmark's own AIRs.

### S5: Rejection evidence is scoped honestly
**Evidence Anchor**: text: Appendix A "These single-value mutations test that the listed constraints exist, not that the gadgets are complete."

Appendix A separates three things: constraint-existence tests, witness-level fuzzing, and a malicious prover's search for a satisfying witness of a false statement. That separation is what the SNARK-vulnerability literature calls for, and the 122 + 16 + 22 cases are given no more weight than they bear.

### S6: The modelling choice for an external classifier API is made explicit
**Evidence Anchor**: text: §4.3 "Folding the third-party classifier API into O is a modelling choice"

The paper gives both readings: τ = U, or class 4's set plus a third-party element. It also notes that either way the attestation covers the wrapper and not the classifier's computation. This is the correct security-engineering treatment of computation that leaves the measured boundary.

### S7: Separating S from S′ is sound security engineering
**Evidence Anchor**: text: §2.2 "S is a conjunction of two computations, with no gating clause and no temporal clause."

The paper distinguishes integrity of a computation from gating and ordering on the serving path, and its Ignore and Defer strategies show why proofs of S cannot reach S′. Both are correct, and both are under-appreciated in the verifiable-inference literature. The artifact's own acceptance of classifier proofs made two days after the answer proofs illustrates the point well.

### W1: The replay-versus-proof result ignores the hash assumption when weights are identified by digest
**Severity**: Minor
**Evidence Anchor**: text: §5.4 "replay of an exact integer program needs only {E, P}, while the proof needs {E, P, K} at unqualified parameters"
**Confidence**: 4. Basis: direct reading of the paper's own universe against the rerun boundary it reports.

K covers hashes as well as proof-system soundness. In the demonstration, the replay path identifies the classifier exports by SHA-256 digest (§5.5: the loader accepts only the published quantizations, and the CNN rerun "also hashes the weights"). That replay therefore relies on hash collision resistance, which is part of K. Under the coarse universe, τ(replay) is then {E, P, K}, the same set as τ(5), not a strict subset of it. Strictness holds only in two cases: when the verifier holds the enrolled bytes themselves, or under the reading that splits K into hash assumptions and proof-system soundness, which the paper itself offers in §4.2. The substance survives, since the proof additionally needs soundness at unqualified parameters. Still, Result 5, §5.4 and the abstract should say which of these readings makes "less trust" strict.

### W2: The attestation side gets no parameter-level treatment comparable to §5.3
**Severity**: Minor
**Evidence Anchor**: absence: §4.3 class 4 and Table 1 — expected an account of the appraisal parameters a class 4 verifier must fix (TCB or security-version levels, debug and migration policy, revocation and TCB recovery after disclosed attacks, nonce freshness, currency of collateral), parallel to the proof-parameter analysis of §5.3; checked §2.1, §4.1, §4.3 class 4, Table 1, Table 2, §7.1 gaps 1 and 7
**Confidence**: 4. Basis: hands-on SEV-SNP, TDX and H100 CC attestation appraisal.

The proof side is analysed down to queries, blowup, grinding and field caps. The attestation side is represented by its root and its attack record. W is not a static element, however. Whether an attested report deserves trust depends on the verifier's appraisal policy and on the vendor's TCB recovery. TEE.fail, for example, is described as forging quotes "at the UpToDate level", which is a statement about TCB status. RATS [B5] already gives the vocabulary for this. A short paragraph would treat the two sides symmetrically. It would also show that appraisal policy is an E/P-like trust a class 4 verifier carries, just as a class 5 verifier carries unqualified parameters. This does not change the order's structure.

### W3: The class 4 attack record is thin on attacks against SEV-SNP and SGX attestation itself
**Severity**: Minor
**Evidence Anchor**: text: §4.3 "CacheWarp broke the integrity of AMD Secure Encrypted Virtualization with Secure Nested Paging (SEV-SNP) [B15]"
**Confidence**: 3. Basis: familiarity with the TEE attack literature; the works named below are from memory and could not be checked in this review.

CacheWarp attacks the integrity of a guest VM's execution. It does not forge attestation reports. The only SEV-SNP entry in the record therefore supports "vendor roots have failed" less directly than the SGX and TDX entries do. From memory, I recall memory-aliasing and memory-interposition attacks published in 2024–2025 that target SEV-SNP and SGX attestation directly (for example BadRAM, Battering RAM and WireTap). The author should check these against primary sources and add them if confirmed. They would strengthen the paper's point rather than change it.

### W4: The SASH soundness account covers only the FRI query term, though the proofs also contain a GKR component
**Severity**: Minor
**Evidence Anchor**: text: §5.1 "an open-source STARK prover for a quantized transformer"
**Confidence**: 3. Basis: repository documents (`docs/LLM-PROOF.md`, decision 0070) refer to "STARK/GKR proofs"; the SASH source was not opened.

The repository describes the LLM verifier as checking "STARK/GKR proofs". GKR and sum-check, like the LogUp lookups used for the classifiers, add soundness-error terms that depend on field size and degree over QM31. These terms are small at about 2¹²⁴, but they are not the FRI query term. §5.3's "other limits" sentence names the extension field generically. It should say that the per-segment proof composes FRI-based STARK and GKR arguments, so that the 100-bit query-and-grinding figure is clearly the figure for one component only.

### W5: The paper does not say how public inputs enter the Fiat–Shamir transcript, although it cites weak Fiat–Shamir as a class 5 failure
**Severity**: Minor
**Evidence Anchor**: absence: §4.3 class 5 and §5.1 to §5.3 — expected a statement of whether each proof's enrollment and public inputs are absorbed into the Fiat–Shamir transcript before the first challenge, for the classifier AIR and for the SASH segments; checked §4.3 class 5, §5.1, §5.2, §5.3, §7.1 gap 7, Appendix A
**Confidence**: 4. Basis: weak Fiat–Shamir literature, plus reading the classifier verifier code.

In S-two, mixing public values into the channel is the application's job, not the library's. This is exactly the failure class that [F2] documents. The classifier code does it correctly: `begin()` in `research/probes/circle/src/lib.rs` mixes the enrollment and the external public values into the Blake2s channel before any commitment. The manuscript should state this, and it should state whether the same holds for SASH. The 63 public-input mutations cannot show strong Fiat–Shamir, because a weak-Fiat–Shamir attack chooses public inputs adaptively after the challenges, which post-hoc mutation does not exercise. This is a one-sentence fix that turns an implicit strength into a stated one.

### W6: The Mac verifier is a patched SASH variant, and what is compiled into it is misnamed
**Severity**: Minor
**Evidence Anchor**: text: §5.1 "it is verified only by the SASH prover's own pinned implementation"
**Confidence**: 4. Basis: `docs/decisions/0070-native-enrolled-llm-verifier.md` and `docs/LLM-PROOF.md`.

The 3.40–3.53 s path is a verifier-only build of the pinned SASH source that Hallmark patched. It reports `dirty: true` and compiles in the 23 shape (preprocessing) roots and the parameter and calibration digests. The model-root checks stay upstream. Two consequences follow:
- The residual P on that path includes Hallmark's own patch, not only the upstream implementation.
- "model roots compiled in" (§5.4, and implicitly Table 4) should read "shape roots".

The manuscript's statement that the bundle is "verified only by the SASH prover's own pinned implementation" should note the variant.

### W7: "Spares a verifier the weights" holds per request, not for a caller who also enrolls
**Severity**: Minor
**Evidence Anchor**: text: Abstract "The proofs spare a verifier the weights and re-execution"
**Confidence**: 4. Basis: §2.1 (the caller is both enroller and verifier) and `docs/LLM-PROOF.md` (enrollment derives model roots from the checkpoint).

In Hallmark the caller enrolls the model roots, and deriving those roots requires the 2.2 GB checkpoint. A verifier is spared the weights only in two cases: it trusts roots published by a separate enroller (E), or it needed the weights once at enrollment and not per request. §5.5 already says that compiled-in roots belong to E. The abstract and conclusion should carry the same qualifier: "spares a verifier per request the weights, given enrolled roots".

### W8: The abstract credits logging designs with the serving-path property that Table 2 gives only to attestation
**Severity**: Minor
**Evidence Anchor**: text: Abstract "needs a mechanism on the serving path that some attestation and logging designs supply and a proof cannot"
**Confidence**: 4. Basis: internal comparison with Table 2 and §7.1 gap 1.

Table 2 says a pre-release log makes T possible for the claimed verdict, with G "asserted only". §7.1 says such a log "would not show that the classifier ran in line". The abstract and conclusion group logs with attestation as supplying the mechanism for gating and timing. They should say that logs supply a timing anchor for a claim, and that only a measured program on the serving path can supply G.

### W9: The status of the conjecture behind the query-and-grinding formula is not discussed
**Severity**: Minor
**Evidence Anchor**: text: §5.3 "a query-and-grinding conjecture that the unanalysed extension-field and hash terms below cap, not a proven bound"
**Confidence**: 3. Basis: recollection of 2025 proximity-gap work that could not be checked in this review.

The formula's per-query credit of log₂(1/ρ) bits rests on proximity-gap or list-decoding conjectures up to capacity. My recollection is that work in 2025 reported counterexamples to strong forms of the up-to-capacity proximity-gap conjecture for Reed–Solomon codes. I could not verify this here. If it is confirmed, one sentence on the conjecture's current status would show that "conjectured" is a contested label, not only an unproven one. That matters most at rate 1/2, where the SASH segments sit.

### W10: The Johnson-bound analysis for circle codes is attributed only to the Reed–Solomon result
**Severity**: Minor
**Evidence Anchor**: text: §5.3 "the regime up to the Johnson bound [A40] gives at most about 50 and 176"
**Confidence**: 3. Basis: familiarity with the Circle STARKs paper; not re-read here.

[A40] proves proximity gaps for Reed–Solomon codes over multiplicative domains. S-two uses circle codes, and as I recall the Circle STARKs paper [A27] carries the corresponding proximity-gap analysis over to them. Citing [A27] alongside [A40] would attribute the regime that actually applies.

### W11: "Strictly logarithmic verifier" is an IOP-model statement
**Severity**: Minor
**Evidence Anchor**: text: §4.3 "FRI has a strictly logarithmic verifier [A25]"
**Confidence**: 4. Basis: standard FRI and STARK complexity.

FRI's logarithmic query and arithmetic complexity is stated in the IOP model. Once compiled with Merkle commitments, as in every deployed STARK including S-two, verification costs O(λ · log² n) hash operations. The sentence sits next to the verifier-cost comparison of Table 1, so it should say which model it refers to.

### W12: Hiding is defined against the verifier but justified for class 4 by confidentiality from the host
**Severity**: Minor
**Evidence Anchor**: text: §4.3 "Hiding from the host holds within the stated threat model [B3]"
**Confidence**: 4. Basis: §2.2's definition against the class 4 text and Table 2.

§2.2 defines hiding as what the verifier learns about R and the weights. The class 4 "Yes, within threat model" entry in Table 2 is justified by TDX confidentiality against the host, which is a different property. For the closest same-question design, the prompt also leaves the enclave for an external classifier API. Table 2 should separate hiding from the verifier (what the report data reveals) from confidentiality against the operator.

### W13: Limb-decomposition soundness is stated as achieved rather than as a design intent
**Severity**: Minor
**Evidence Anchor**: text: §5.1 "so that no integer alias modulo the Mersenne-31 prime passes"
**Confidence**: 4. Basis: Appendix A's own statement that there is no completeness argument or fuzzing for the gadgets.

The 22 invalid-witness cases change a single witness value each. They do not search for aliasing witnesses. Under-constrained range and limb gadgets are the most common SNARK bug class in [F1]. The sentence should read "are designed so that", or point to an argument.

### W14: One attack is given three names
**Severity**: Minor
**Evidence Anchor**: table: Table 1, class 5 row, Characteristic failure column
**Confidence**: 5. Basis: internal comparison.

[A23] is referred to as "ghost weights" (§4.3), "Hollow weights" (Table 1) and "the hidden-weight attack" (§7.1 gap 3), while the source's own name is the Hollow-LLM attack. One term should be used throughout.

### W15: The LLM-prover coverage may miss a 2025 security-venue system
**Severity**: Minor
**Evidence Anchor**: absence: §6 Proofs of ML inference — expected coverage of further succinct LLM-inference provers from 2025 security venues (for example zkGPT, recalled from memory and not checked here); checked §1, §3, §4.3 class 5, §6, Table 6
**Confidence**: 2. Basis: recollection only.

This does not affect the bounded novelty statement, which concerns guardrail verdicts composed with an answer proof and which I find defensible given the searches described in §3. It would make strand A more complete.

Cross-references for other seats, which I have not scored. For methodology (D1): no finding above needs new data. W4, W5 and W6 concern what the trusted base contains and can be fixed with text. For argumentative coherence (D3): W1 and W8 are the two places where a headline sentence is stronger than the body supports. Both can be repaired by adding a qualifier, without changing the argument.
