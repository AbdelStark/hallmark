contract_role: perspective
## Dimension Scores

### D1: methodology_rigor
score: not_assessed

### D2: domain_accuracy
score: not_assessed

### D3: argumentative_coherence
score: not_assessed

### D4: cross_disciplinary_relevance
score: warn
trigger: "secondary cross-field implications are overstated or weakly supported, but the central argument stays sound and the gaps can be fixed in a revision"

### D5: writing_and_structure
score: not_assessed

### D6: venue_fit_and_contribution
score: not_assessed

## Review Body

I read this manuscript as its intended end user: an auditor or assurance practitioner who has to decide what to ask a deployer for. On that reading the paper does something the verifiable-inference literature rarely does. It splits "the classifier ran" into what was computed, whether the verdict gated the served answer, and whether it did so before release (S versus S′). It also states plainly that every class in its integrity order speaks only to the first. The regulatory readings are restrained. The paper's own case, in which classifier proofs made two days after the answer were accepted, is reported against its own interest. The central argument, an integrity order over explicit trust sets, is not something I am placed to verify formally, and nothing in it depends on another field's practice. So I see no block-level misrepresentation of the governance side.

The weaknesses lie where the paper reaches into audit practice. The "auditor's order" is named in the abstract and in Section 4.4, but it is never built the way the integrity order is. The pre-release-log composition, which the conclusion recommends as a next step, leaves out the two conditions that decide whether it gives an auditor any timing evidence. Several Table 2 "possible" entries carry conditions an auditor cannot act on as written. All of these are secondary implications and can be fixed in revision without touching the integrity analysis, so D4 is `warn`.

No target venue is bound (criteria_binding_unavailable), so this card makes no venue-alignment claim and has no constructive-findings sidecar. I found no instruction-like text in the manuscript addressed to reviewers.

### S1: The computed / gated / before-release split is the right decomposition for audit questions

**Evidence Anchor**: text: §2.2 "G says that Y was released only if V allowed it, and T says that V was computed before Y was released"

An auditor's question is usually whether the safeguard was in effect for this request, not whether some function evaluated to some value. The paper makes that difference formal and adds Ignore and Defer to the adversary list (§2.3). It then records the property for each class in a separate auditor-facing table (Table 2) and does not fold it into the integrity order. This is the paper's most transferable idea for governance readers, and it explains why "evidence of execution" from proofs alone cannot meet an "in effect at serve time" audit question.

### S2: Regulatory readings disclaim the mandate they could have implied

**Evidence Anchor**: text: §7.1 gap 10 "Neither text, as read, mandates cryptographic per-request evidence, so the systematization offers possible forms of evidence rather than meeting a stated demand"

The paper cites AI Act Arts. 12(1), 19(1) and 26(6) and Code of Practice Measures 5.1 and 7.3. Each time it disclaims the high-risk classification ("We do not argue that a guardrailed chat service is high-risk"), declines to claim a retention cost, and states the version of the Regulation it read. That is the right register for a technical paper citing regulation, and an adjacent-field reader will not take it as a compliance argument.

### S3: The paper's own composition is used as a counter-example for audit practice

**Evidence Anchor**: text: §5.4 "For this statement, proving after the fact cannot be told apart from proving in line."

Two facts are reported where a deployment paper would have hidden them: the composed verifier accepted classifier proofs produced two days after the answer proofs, and the CNN's verified block verdict sits next to a verified answer to the same prompt. Together they show auditors concretely that a valid per-request proof bundle is consistent with Defer and with Ignore. This is the most useful practical lesson in the paper.

### S4: Degraded modes and misconfiguration are treated as missing evidence, not intent

**Evidence Anchor**: text: §2.3 "A declared degraded mode, such as a classifier timeout that fails open, is likewise indistinguishable from Skip unless S names an enrolled fallback policy"

Fail-open fallbacks are a routine audit finding in deployed rail pipelines. The paper names them, says what would make them distinguishable from Skip (an enrolled fallback policy plus a pre-release record that it was taken), and states that the systematization "supports detecting missing evidence, not attributing intent". That is exactly the evidentiary posture an auditor needs.

### S5: Box 1 and Table 5 keep execution evidence apart from safety evidence

**Evidence Anchor**: text: Box 1 "Evidence that a guardrail ran says nothing about whether its decisions are adequate"

The paper repeats Jin et al.'s warning against advertising an attested guardrail as proof of safety. It reports that its own MLP never blocks and that its CNN blocks a benign prompt, and Table 5 marks "Adequate safety policy: Not reached". These disclosures are prominent enough that a careful reader will not mistake the artifact for a safeguard.

### W1: The "auditor's order" is asserted, not constructed

**Severity**: Major
**Evidence Anchor**: text: §4.4 "Table 2 reverses much of Figure 1."
**Confidence**: 4 (assurance practice; this is the reading I would bring to an evidence-requirements specification)

The abstract says "an auditor's order differs from the integrity order", and §4.4 says Table 2 "reverses" Figure 1. But Table 2 assigns no trust elements to G or T. Its cells are qualitative: "Possible", "Asserted only", "bounded by the challenge window". The rigor that makes the integrity order useful, where a reader can see which assignment each edge depends on, is missing exactly where the paper addresses auditors. Two examples:

- Class 4's "G and T possible" rests on W, on correct gating code inside the measured wrapper (P), and on that wrapper's measurement being enrolled as the reference value (E).
- Class 2's "T possible" rests on whoever assigns the time to the entry (see W2), while the entry's content still rests on O.

Without these sets, an auditor cannot tell whether a class-4 gating claim needs more or less trust than a class-2 timing claim, and the word "order" promises a comparison the paper does not supply. The conclusion's claim that gating and timing are "the senses of 'ran' an auditor often cares about most" also has no support from the audit literature the paper cites ([D15], [D16], [D18]). It is plausible, but it is asserted.

Minimum remedy: call Table 2 an "auditor's view" rather than an order, drop "reverses", and cite or soften the "cares about most" sentence. Stronger option: give τ_G and τ_T for classes 2, 3b and 4 using U, plus an element for an independent time source if one is needed, and derive the comparison. This costs one table and a few paragraphs and would make contribution 3 as checkable as contribution 2.

### W2: The pre-release-log composition omits who keeps time and how release is evidenced

**Severity**: Major
**Evidence Anchor**: text: §7.1 gap 1 "would fix the claimed verdict in time for later proofs to match"
**Confidence**: 4 (record-keeping and log-based evidence design)

The conclusion recommends this composition ("a pre-release log composed with proofs"), and gap 8 reuses it for the IMMACULATE-style sampling pattern. As stated, it fixes nothing in time against this paper's adversary unless two conditions hold, and the paper states neither.

1. The log, or at least its timestamps and inclusion, must be run or witnessed by a party other than the operator. If O writes the entry, runs the log and stamps the time, then T rests on O. Class 2's own trust set is τ = U, and the paper notes that permanence rests on auditors comparing views (§4.3).
2. Release time must be evidenced to the verifier. "Before release" can only be checked if the served answer carries something that ties it to the log entry, such as an inclusion receipt or promise over commitments to R, V and a hash of Y, which the user receives with Y and can keep. An auditor arriving later has no independent knowledge of when Y was released.

Without both conditions, an operator can write the entry after release and present it as prior. This is the Defer strategy again. The "T possible" cell of Table 2 for class 2 has the same gap. Minimum remedy: state both conditions in gap 1 and in the Table 2 class-2 cell. Stronger option: add a short "what to request" list for this composition (log operator identity, entry contents, the receipt delivered with the answer, and the retention period for that receipt). That list is the part a deployer or auditor would actually procure against.

### W3: Sampled-proof detection of Skip depends on the block base rate, not only the sampling fraction

**Severity**: Minor
**Evidence Anchor**: text: §7.1 gap 8 "an operator that commits to a verdict before computing it is caught whenever a sampled proof disagrees"
**Confidence**: 4 (audit sampling design)

The sentence is literally true but invites a wrong sizing of the audit. An operator that skips C and commits "allow" for every request is caught only on sampled requests that C would have blocked. The per-request detection probability is therefore roughly the sampling fraction times the block rate, and block rates on real traffic are low. The paper's own MLP shows the limit case: it never blocks, so Skip-with-allow is undetectable under any sampling rate. One sentence noting that sample sizes must be set against the expected block rate, or that audits should seed known-block inputs, would make the pattern usable by an auditor.

### W4: Class-4 capture provenance needs the user's channel to terminate inside the measured boundary

**Severity**: Minor
**Evidence Anchor**: table: Table 2, class 4 row, Capture provenance column
**Confidence**: 3 (deployment of attested services; I do not verify TEE internals)

"Possible, if the measured program captures R" is necessary but not sufficient. If the operator's front end receives the user's request before it reaches the enclave, the operator can still choose R. Capture provenance holds only if the user's client encrypts to an attested key and checks the attestation before sending. The paper's own description of Private Cloud Compute ([B26], §6), where user devices send data only to attested nodes, is the illustration. This changes who can establish the property: the user's client, at request time, not an auditor afterwards, unless the client keeps a record. Gap 2's "attested capture service" inherits the same condition. A clause in the table cell and in gap 2 would fix this.

### W5: Table 2's gating and timing cells carry no streaming caveat

**Severity**: Minor
**Evidence Anchor**: table: Table 2, Gating (G) and timing (T) column, classes 2 and 4
**Confidence**: 4 (deployed LLM service architecture)

§2.2 and §2.4 correctly put streaming release out of scope. But §4.4 tells auditors to "read Table 2 first", and many chat deployments stream. For an input rail, G and T only need the verdict to precede the first released token. For an output rail, they need a check on every released prefix or a buffered answer. As written, the "possible" entries read as unconditional for streamed services. A table note restricting the G and T cells to non-streamed release, or to input rails, would stop an auditor from carrying them over to settings the paper deliberately excluded.

### W6: The honest-enroller assumption is left without its deployment reading, although the artifact implements part of one

**Severity**: Minor
**Evidence Anchor**: text: §2.3 "The enroller is honest and completes enrollment before any proof or report is produced."
**Confidence**: 3 (governance of reference values; RATS reading limited to what the manuscript quotes)

In practice, the party that knows the deployed classifier, threshold and fallback policy is the operator, which is this paper's adversary. When O enrolls, "honest enroller" cannot be assumed. What still protects the verifier is that enrollment is public, prior and append-only: the operator is held to what it declared before the requests it governs. That turns E from trust in a party into a checkable property of a record, and it is worth one paragraph in §2.3 instead of a full deferral to future work (§2.1, gap 5).

Two related points. First, gap 5 lists fallback policies among enrolled reference values, while §2.1 notes that in RATS appraisal is a policy decision. The paper should say whether a fallback policy is a reference value (what the operator committed to do) or appraisal policy (what the verifier will accept), because different parties own each. Second, the repository documents signed LLM enrollment with a validity interval that relies on "the caller's trusted clock" and has no revocation service (`docs/LLM-PROOF.md`), as well as a signed registry with dual-authorized key rotation (`research/evidence/w09-registry-rotation-2026-10-20.json`). §5.2 does not say whether the composed case used either. These are exactly the design choices an auditor would ask about (who signs, whose clock, how a threshold change is revoked), and describing them, even as out of scope for the case, would make gap 5 concrete.

### W7: The Code of Practice is read slightly more strongly in gap 10 than in the introduction

**Severity**: Minor
**Evidence Anchor**: text: §7.1 gap 10 "asks providers of general-purpose AI models with systemic risk to implement and document mitigations such as input and output filtering"
**Confidence**: 3 (internal comparison only; I did not consult the Code's text)

The introduction says Measure 5.1 "lists" input and output filtering as a mitigation and puts the documentation duty under Measure 7.3. Gap 10 attributes both implementation and documentation to Measure 5.1, and "asks ... to implement ... such as input and output filtering" can be read as a filtering mandate. Aligning gap 10 with the introduction's wording and its 5.1/7.3 split would remove the inconsistency. This matters because the paper otherwise takes care not to imply a mandate.

### W8: The paper's roles are not mapped to regulatory roles, and the regulator is cast as the user's agent

**Severity**: Minor
**Evidence Anchor**: text: §2.1 "it may be the user who sent the request, an auditor, or a regulator acting for the user"
**Confidence**: 3 (AI governance practice)

A market-surveillance or supervisory authority acts under statutory powers, not as an agent of the user. It can usually compel disclosure, which changes the practical force of §2.4's "an operator can always refuse to serve evidence". "Operator" also merges roles the cited texts keep apart: the Code of Practice addresses providers of general-purpose AI models, while the Act's log-keeping duties split between providers (Art. 19(1)) and deployers (Art. 26(6)), and a guardrailed service may be run by a downstream deployer outside the Code's scope. A sentence mapping operator, verifier and enroller onto provider, deployer and authority, with the caveat that the paper takes no position on which applies, would let policy readers place the analysis.

### W9: §5.3 is not accessible to governance readers and lacks a one-line takeaway for them

**Severity**: Minor
**Evidence Anchor**: text: §5.3 "the unique-decoding regime gives about 41.5 bits per LLM segment"
**Confidence**: 4 (accessibility judgement only; I do not assess the cryptographic figures)

Unique decoding, the Johnson bound, grinding, extension-field caps, KZG and Fiat–Shamir (§4.3) appear without a gloss. That suits the cryptography reviewers. The consequence an auditor needs is short and already in the paper: the parameters are unqualified, so the reading that separates proof soundness from K applies, and Hallmark sits level with attestation, not above it. One sentence at the top of §5.3 stating that consequence would let a governance reader skip the rest safely.

### W10: Prompt privacy in retained or shared evidence is under-specified

**Severity**: Minor
**Evidence Anchor**: text: §7.1 gap 3 "With public witnesses, a deployer cannot hand auditors prompts containing user data without a separate privacy basis."
**Confidence**: 2 (data-protection implications are my competence; whether the proof bundle itself discloses the prompt is outside it)

Three things an adjacent reader needs are missing:

1. The threat model requires the verifier to hold R, so any auditor-side verification discloses user prompts by design.
2. The paper's own suggestion of retaining logs and proof bundles would turn them into retained personal data, which bears on how long they may be kept, and not only on their size.
3. A reader may take "salted SHA-256 commitment" as confidentiality. The paper should say explicitly whether, without hiding, the proof bundle reveals the committed prompt to anyone holding it. I flag this as a question for the cryptography seats rather than as a finding of fact.

### W11: The "receipt" framing invites the misuse Box 1 disclaims

**Severity**: Minor
**Evidence Anchor**: text: §7.1 "A receipt a deployer could hand to an auditor would need more than any single class provides."
**Confidence**: 3 (assurance-practice judgement)

"Auditor-ready receipt" is compliance language. A valid receipt for a classifier that never blocks, as the paper's MLP does, would be a flawless-looking artifact certifying a safeguard that does nothing. The paper's own case illustrates this better than any hypothetical, and saying so in §7 would make the Box 1 caution operational. Concretely, a receipt for S or S′ should name the enrolled classifier and point to separate evidence on adequacy, or say that none exists. The artifact's name, Hallmark, also carries a certification-of-quality connotation in English that cuts against Box 1. The paper does not need to rename it, but it is worth one line acknowledging the connotation.
