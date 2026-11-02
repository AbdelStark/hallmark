# Response to the revision roadmap

How the revised paper (`docs/paper/`) treats each item of the roadmap in
[editorial-decision.md](editorial-decision.md). Items are in source order, which
is not a priority order. Which items to address and how was decided by the AI
pipeline, as the paper's AI-Use Disclosure states.

Status: **done** (changed as asked), **partly** (changed, but not in the form
asked or not fully), **declined** (not changed, with the reason).

| Item | Status | What changed |
|---|---|---|
| REV-01 | done | Abstract and §1 restated around the same four findings (the split of "ran"; explicit trust sets with mostly incomparable classes and a conditional proofs-over-attestation edge; where attested and proved guardrails stop, including the wrapper reading of Proof-of-Guardrail; the auditor's view). The illustration and gap analysis are no longer numbered contributions, and the order's value is stated as making assignments explicit and disputable. |
| REV-02 | done | "Auditor's order" renamed "auditor's view"; "reverses" dropped (§4.4, abstract, §1). |
| REV-03 | done | §6 "Search outcome and novelty" now opens with the systematization's novelty and then gives the narrow statement about the case. |
| REV-04 | done | Table 4 (now Table B1) and the timer-boundary discussion moved to a new Appendix B; §5.4 keeps a short summary and the bundle-size point. |
| REV-05 | done | The tolerance trust element is now L; T is only the timing clause of S′ (§4.1, Table 1, Figure 1). |
| REV-06 | done | §4.2 pair counts rewritten, naming the comparable pairs under each reading. |
| REV-07 | declined | Class numbers stay. They key Tables 1, 2, 5 and 6 and Figure 1; the text already says they are labels, not heights; mnemonic labels would collide with the RAILS labels compared in §6. |
| REV-08 | done | Box 1 defines "not qualified" in prose and drops the configuration flags. |
| REV-09 | declined for now | Whether the author's employer offers products in a compared evidence class is a fact only the author can state; the competing-interests text is unchanged pending the author. |
| REV-10 | partly | The original searches have no recorded query strings or counts, and §3 now says so. A documented search for the novelty statement was run on 2026-11-02 with per-query counts ([literature-check.md](literature-check.md)); per-strand counts for the original base cannot be reconstructed. |
| REV-11 | done (no change) | The PDF and LaTeX carry the rendered Figure 1 (TikZ) and Figure 2 (`trust-boundary.png`); the Markdown keeps a figure specification by design. |
| REV-12 | done | New "Granularity" list in §4.2: for soundness separated from K, K charged to replay (with and without soundness separated) and P split, which of Results 1–5 and the dashed edges hold and how many pairs above the bottom are incomparable; a further split of K is argued to only remove edges. §1, the abstract and §8 point to it, and §7.2 is now accurate. |
| REV-13 | done | Result 5, §4.4, §5.4, Table 4, the abstract and §8 qualify the replay claim by the conventions it rests on. |
| REV-14 | done | "permanence: K, auditors" removed from the Table 1 class-2 cell; the third-party API case keeps its explicit modelling choice in §4.3. |
| REV-15 | partly | A paragraph in §4.4 maps each strategy to the property that defeats it and to Tables 1 and 2, instead of a separate strategy × class table. |
| REV-16 | partly | See REV-10: a documented search was re-run and logged for the novelty statement, and §3 says the original searches were not logged. |
| REV-17 | done | The novelty statement now rests on the documented search. It found NiyamAI, which proves a guardrail verdict per agent action without proving the model; it is cited in §1, §6 and Table 6, and the composed statement still holds. |
| REV-18 | partly | §3 gives the current count (104) and the depth for the sources added in the last two revisions; per-source depth for earlier additions was not recorded, and §3 says so. |
| REV-19 | done | §5.4 now says the TinyLlama rerun reproduced the answer once and that its bit-exactness with the proved profile was not established. |
| REV-20 | declined | Rerunning exp-R1 needs the retrained exports and the LLM harness again, and no conclusion rests on these timings; the missing commit and CPU fields remain disclosed, and the script now records them for any rerun. |
| REV-21 | done | §1 contribution 3 and §4.4 now say the claim comes from the recorded failures of classes 4 and 5 and the documented failure modes of the others. |
| REV-22 | done | §4.2 and §5.4 state that the demonstration's replay identifies weights by digest and what charging that hash to K changes. |
| REV-23 | done | A paragraph on attestation appraisal policy added to the class-4 discussion (§4.3). |
| REV-24 | done | BadRAM, Battering RAM and WireTap verified on their primary pages and added to the class-4 attack record ([B27]–[B29]). |
| REV-25 | done | §5.3 says the 100-bit figure covers only the FRI query and grinding terms and that the LLM proofs also use LogUp-GKR arguments, which were not analysed. |
| REV-26 | done | §5.2 states that the classifier verifier absorbs enrollment and public values into the Fiat–Shamir channel before any commitment, that SASH was not checked, and what the mutations cannot test. |
| REV-27 | done | §5.1, Table 4, Appendix B: the Mac verifier is a patched build reporting itself as modified, with the 23 shape roots compiled in; residual P includes the patch. |
| REV-28 | done | Abstract, §5.4 and §8: the proofs spare the verifier the weights per request, given enrolled roots. |
| REV-29 | done | Abstract, Table 2, §4.4, gap 1 and §8: a pre-release log kept by another party fixes the claimed verdict in time, which is weaker than T, and gives no G; only a measured program on the serving path can supply G and T. |
| REV-30 | done | §5.3 notes that a 2025 preprint gives counterexamples to the up-to-capacity proximity-gap conjectures as stated ([A47]), that the Johnson-bound results stand, and that the effect at the configurations' rates is not established. |
| REV-31 | partly | The Circle STARKs paper's soundness appendix could not be retrieved; the S-two whitepaper ([A46]), whose abstract states the circle FRI result up to the Johnson bound, is cited instead. |
| REV-32 | done | §4.3 says FRI's verifier is logarithmic in the oracle model and that each compiled query costs O(log² n) hashes. |
| REV-33 | done | Table 2 and §4.3 separate confidentiality from the host and hiding from the verifier. |
| REV-34 | done | §5.1 says the limb decompositions are designed to exclude aliases and points to Appendix A. |
| REV-35 | done | The attack of [A23] is called the Hollow-LLM attack throughout, with "ghost weights" as the source's term for its weights. |
| REV-36 | done | zkGPT ([A45]) verified and cited in §6. |
| REV-37 | done | As REV-02, and "cares about most" replaced in §8 by a statement about when a safeguard was in effect. |
| REV-38 | done | Both conditions (another party keeps the log's time; the answer carries an inclusion receipt) added to §4.3, Table 2 and gap 1, with what an auditor would request. |
| REV-39 | done | Gap 8 explains that detection scales with the block rate and names the never-blocking MLP as the limiting case. |
| REV-40 | done | Table 2 and gap 2: capture provenance needs the user's client to check the attestation and send only to the measured program. |
| REV-41 | done | Table 2 caption restricts the G and T entries to input rails or non-streamed release. |
| REV-42 | done | §2.3 gives the deployment reading of the enroller assumption; gap 5 says a fallback policy is a reference value and its acceptance appraisal policy; §5.2 notes the optional signed enrollment and that the J1 record contains none. |
| REV-43 | done | Gap 10 aligned with the introduction's Measure 5.1 / 7.3 split. |
| REV-44 | done | §2.1 says the roles do not map one-to-one onto provider, deployer and authority, and describes the authority as acting under its own powers. |
| REV-45 | done | §5.3 opens with its consequence for readers who skip the figures. |
| REV-46 | done | Gap 3 covers prompt disclosure to auditors, retained evidence as personal data, and that a commitment without hiding is no confidentiality guarantee for the bundle. |
| REV-47 | done | §7.1 opens with what a receipt certifies and what it should point to, and acknowledges the connotation of the name. |
| REV-48 | done | E now covers the authenticity of the verifier's reference copy, for replay and proofs alike; the alternative (K charged to replay) is worked out in §4.2 with its counts. |
| REV-49 | done | §1 and §2.2: the first reading is the value computed, which says neither who nor when; T now says V was computed on the serving path; Skip is restated relative to S and S′ in §2.3 and §5.4. |
| REV-50 | done | §2.2 names attribution as a property not recorded per class; §6 restates the RAILS difference as one of target property. |
| REV-51 | done | §2.2 names the enrolled transform from R to each consumer's input. |
| REV-52 | done | §5.4 notes that the classifier proofs bind the answer, so they cannot precede it in this design. |
| REV-53 | done | §2.3 notes that for a user-verifier, binding needs disclosure of the hidden context or a hiding commitment. |

An independent check of this revision against the roadmap then led to further corrections: the Granularity results per cut, the definition of T now excluding pre-release logs, the reading depth of NiyamAI, the search's other finds, and wording. Beyond the roadmap, the advisory acronym check led to defining API, CPU and GPU
at first use, and building the PDF exposed two rendering faults now fixed:
author names with umlauts and the section sign in tables.
