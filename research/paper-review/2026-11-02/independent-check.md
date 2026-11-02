# Independent verification of the 2026-11-02 revision

Scope: `docs/paper/proofs-attestation-logs.md` (working tree) against `28f1fc3`, the roadmap (REV-01..REV-53), `response.md` and `literature-check.md`. Line numbers refer to the revised Markdown.

## Order-theoretic recomputation (task 3)

Trust sets: bottom = U; 1 = {E,P,D}; 3a = {E,P,K,L,Q}; 3b = {E,P,K,D,H}; 4 = {E,P,K,W}; 5 = {E,P,K}.

- Pair-count sentence (l. 118): correct. All 11 pairs that involve 0a or 2 are comparable. Above the bottom, the folded reading has 4 comparable pairs (1–3b, 3a–5, 3b–5, 4–5) and the separated reading has 1 (1–3b). That gives 15 and 12 comparable pairs in total, and 6 and 9 incomparable pairs above the bottom.
- K charged to replay (1 = {E,P,K,D}), folded reading: 5 ⊂ 1, so proofs need strictly less than replay. The comparable pairs above the bottom are 1–3b, 1–5, 3a–5, 3b–5 and 4–5, so 5 of 10 are incomparable. Correct.
- Result 5's refinement with K charged: replay = {E,P,K}, the same set as proofs under the folded reading, so it is a tie. Correct. It is strict when soundness is separated ({E,P,K′} ⊂ {E,P,K′,Σ}). It is also strict for proofs that need N, so "only when soundness is separated" is slightly too strong (item 20).
- K charged and soundness separated: not stated in the paper. The result is 9 of 10 incomparable (only 1–3b remains comparable).
- P split: all 10 pairs above the bottom become incomparable only if 3a's implementation element differs from the circuit element, and 3b's set does not contain the verifier's rerun code. The paper's list names four locations for five classes (item 6). "Only the placement of the bottom class survives" is wrong, because Results 3 and 4 survive as well (item 1).

## Findings

1. **Location:** §4.2 "Granularity" (l. 120), the P-split sentence.
   **Problem:** "Result 2 and the refinement disappear, and only the placement of the bottom class survives" is false. Splitting P only removes comparabilities. Result 3 (3a, 3b and 4 pairwise incomparable) and Result 4 (replay and proofs incomparable) both still hold, and become part of the "all 10 incomparable" claim. The dashed edges also disappear, which the sentence does not say.
   **Suggested fix:** "Result 2, the dashed edges and the refinement disappear; Results 1, 3 and 4 survive."
   **Severity:** must-fix.

2. **Location:** `docs/paper/main.tex`, `docs/paper/proofs-attestation-logs.pdf`, `docs/paper/README.md`.
   **Problem:** The LaTeX and PDF were not regenerated and are unchanged since `28f1fc3`. `main.tex` still has the old abstract ("an auditor's order differs from the integrity order"), Table 1's "E, P, K, T, Q (… one of T and Q)", and §4.4's "The integrity order and the auditor's order differ. Table 2 reverses much of Figure 1." The TikZ Figure 1, which the response cites under REV-11, therefore still shows the old sets. README already says "36 pages" for an unchanged PDF. The response's claim that building the PDF exposed rendering faults "now fixed" cannot be seen in the working tree.
   **Suggested fix:** Regenerate `main.tex` and the PDF from the revised Markdown, including the Figure 1 sublabel L. Check the page count, then commit all three together.
   **Severity:** must-fix.

3. **Location:** §3 (l. 85), Data and Artifact Availability (l. 354), README.
   **Problem:** The paper says the search log and the review records "are in the repository" under `research/paper-review/2026-11-02/`. That folder is untracked (`git status`: `?? research/paper-review/`), so the claim is false until it is committed.
   **Suggested fix:** Commit `research/paper-review/2026-11-02/` in the same change as the paper.
   **Severity:** must-fix.

4. **Location:** Abstract (l. 7), §1 (l. 21–26), response REV-01.
   **Problem:** The counts disagree. The abstract says "Three findings follow" and folds the auditor's view into the first. §1 says "Its contributions are four findings and the explicit assignments behind them". The response lists four different findings (split, conditional edge, wrapper reading, auditor's view), which do not match §1's four items either: §1 item 2 is trust sets plus the conditional edge, and item 4 is auditor's view, illustration and gap analysis. REV-01's acceptance criterion also says no listed contribution may be one the body calls a definitional consequence. §1 item 4 headlines the worked illustration, which §5 and §5.4 say "follows from the definitions".
   **Suggested fix:** Use one list of findings in the abstract, §1 and the response, with the same count. Move the illustration and the gap analysis out of the numbered findings, for example into a closing sentence.
   **Severity:** must-fix.

5. **Location:** §3 (l. 85), "It found one work this paper had missed, NiyamAI [A44]", and l. 87, "which for NiyamAI [A44] was its abstract only".
   **Problem:** Two contradictions with `literature-check.md`.
   (a) The documented search also surfaced zkGPT (W5, E5). The paper had also missed zkGPT and now cites it as [A45]. The search further surfaced Laminator (TEE per-inference cards) and "Confidential Prompt Filters for LLMs" (ZK embedding gate on prompts). Neither is cited or set aside in the text, so "one work this paper had missed" is untrue.
   (b) The literature check says "Full text was read only for NiyamAI and Proof-of-Guardrail" and quotes NiyamAI's Section 1, while the paper says NiyamAI was read at abstract level only. The paper's details (an "11→8→2 feedforward network", "for each authorized agent action", "committed intent contract") come from the literature check's full-text summary. If only the abstract is the paper's basis, these details may exceed it.
   **Suggested fix:**
   - Say the search surfaced NiyamAI as the one work bearing on the novelty statement, plus zkGPT (added in §6) and two adjacent works.
   - Cite or explicitly set aside the two adjacent works. The Springer chapter's abstract was not retrieved, so say so.
   - State NiyamAI's actual reading depth, and keep only details the read text supports.
   **Severity:** must-fix.

6. **Location:** §4.2 "Granularity" (l. 120), the P split.
   **Problem:** The list of implementation locations ("the verifier's rerun code, a delegated program, a measured image, a circuit") has four entries for five classes. 3a's element is unnamed, although TOPLOC-style checks run verifier-side model code, and sampled-proof schemes such as IMMACULATE use circuits. If 3a's element is the circuit element, 3a–5 stays comparable. In refereed delegation the referee executes the disputed step itself. If 3b's set includes the verifier's own code, 1–3b stays comparable and Result 2 survives. "All 10 incomparable" therefore depends on unstated assignments.
   **Suggested fix:** Name 3a's element, and state the assumption that the referee's step code is not charged to 3b. Alternatively, say "up to all 10".
   **Severity:** should-fix.

7. **Location:** §4.2 opening (l. 110) and §1 contribution 2 (l. 24).
   **Problem:** "The order has four unconditional results" and "Two results depend on stated choices" contradict the new Granularity paragraph. Charging K to replay breaks Result 4, and the P split breaks Result 2.
   **Suggested fix:** Say "four results that hold on this universe under either reading of the dashed edges", and in §1 say which results each finer cut changes, or point to the Granularity paragraph.
   **Severity:** should-fix.

8. **Location:** Response REV-12 ("done") against the roadmap's acceptance criterion.
   **Problem:** The criterion asks for Results 1–5 listed against the P split and the K split (hash, signature, commitment, soundness), each marked as surviving or failing. The paragraph separates only soundness and charges only the hash to replay. It never names Result 4 as failing under the K-charged reading, and gives no count for the K-charged plus separated reading (9 of 10). "Done" overstates what changed.
   **Suggested fix:** Add a small table, Results 1–5 by {folded, soundness separated, K charged to replay, P split}, or mark REV-12 "partly" in the response.
   **Severity:** should-fix.

9. **Location:** Abstract (l. 7) "most pairs of classes are incomparable"; §8 (l. 350) "most pairs … cannot be ranked".
   **Problem:** Under the K-charged reading the paper now presents, exactly 5 of 10 pairs are incomparable, which is not "most". That was DA M1's point. Neither sentence is qualified.
   **Suggested fix:** Use "at least half, and most under the paper's default cut", or attach the convention.
   **Severity:** should-fix.

10. **Location:** Table 4, row "Class 1, replay" (l. 281); §4.4 first paragraph (l. 202).
    **Problem:** Both remain unqualified: "Gives the same classifier integrity with less trust in the demonstration" and "replay of an exact integer program needs only E and P". REV-13's acceptance requires every occurrence to name the reading.
    **Suggested fix:** Add "under the conventions of Result 5 (§4.2)" in both places.
    **Severity:** should-fix.

11. **Location:** §1 contribution 3 (l. 25), "the failure records of every class leave trust in some party or assumption"; §4.4 bold lead (l. 202), "Every class's failure record leaves trust somewhere."
    **Problem:** REV-21 was fixed only in §4.4's body ("recorded failures of classes 4 and 5 and … documented failure modes of the others"). The §1 sentence and the §4.4 heading still claim recorded failures for every class, and the roadmap named §1 contribution 3 explicitly.
    **Suggested fix:** Use "the recorded failures of classes 4 and 5, and the documented failure modes of the others, leave trust …", and retitle the §4.4 lead to match.
    **Severity:** should-fix.

12. **Location:** Table 2, rows 2 and 3a ("T possible for the claimed V", "T possible if commitments precede release"); §4.4 (l. 206), "pre-release logs … can observe or anchor the serving path"; gap 1 (l. 333), "a timing anchor for the claim, not G".
    **Problem:** T now says V "was computed on the serving path before Y was released" (REV-49). A pre-release log fixes the claimed V before release but does not show it was computed on the serving path. Gap 8 concedes this: Skip with a committed allow survives on allow-requests. So these cells, and "not G" (which implies T), grant logs more than the new definition allows. A log anchors the claim, not the serving path.
    **Suggested fix:** Write "claimed V fixed before release (weaker than T)" in Table 2 rows 2 and 3a and in gap 1, and use "anchor the claim in time" in §4.4.
    **Severity:** should-fix.

13. **Location:** §5.2 (l. 228), "absorbs the enrollment and the public values … before any commitment …, as weak Fiat–Shamir attacks require [F2]".
    **Problem:** The sentence says the attacks require the absorption, which inverts the meaning. The code claim itself checks out: `begin` in `research/probes/circle/src/lib.rs` mixes the serialized enrollment and public values into a fresh `Blake2sChannel` before the first `scheme.commit`.
    **Suggested fix:** "as the defence against weak Fiat–Shamir attacks requires [F2]".
    **Severity:** should-fix.

14. **Location:** §4.3 class 5 (l. 170), "each query also costs a logarithmic number of hash evaluations".
    **Problem:** With Merkle-committed FRI, each query opens one authentication path, of length about log n, in each of about log n layers. A query therefore costs O(log² n) hashes, not a logarithmic number. This is the O(λ·log² n) total that REV-32 asked for.
    **Suggested fix:** "each query also costs O(log² n) hash evaluations (a Merkle path per folding layer)".
    **Severity:** should-fix.

15. **Location:** §5.4 (l. 257), "a rerun under the proved relation reproduced the proved answer once".
    **Problem:** "Under the proved relation" asserts what the next clause disclaims ("we did not establish that this rerun path is bit-exact with the proved integer profile"). The script also recomputes attention calibration from `calibration_texts` at runtime rather than reading the enrolled calibration (`measure_native_rerun.py`, `llm()`). "Once" is accurate: the answer match is checked in one untimed call.
    **Suggested fix:** "a native rerun of the quantized profile (`y-attnout-w12`, calibration recomputed) reproduced the proved answer in one run".
    **Severity:** should-fix.

16. **Location:** §3 reading-depth paragraph (l. 87).
    **Problem:** The sentence chains four semicolon clauses. "For [A43] only the ePrint record … could be retrieved" now follows the clause about earlier revisions, so it reads as if [A43] were an earlier-revision source, though it is in the [A39]–[A47] range. "Checked the same way, but their reading depth was not recorded" contradicts itself, because "the same way" is a reading depth. [A44] was found by the documented search, not added "at reviewers' request".
    **Suggested fix:** Split into separate sentences: last two revisions (with the [A43] and [A44] exceptions); earlier revisions ("depth not recorded"); [A22].
    **Severity:** should-fix.

17. **Location:** Table 6, NiyamAI row, "5"; Table 5 caption.
    **Problem:** `literature-check.md` records that NiyamAI uses Halo2-KZG with a local test SRS, so it needs N. Table 6 marks N for Seal-then-sample but not for NiyamAI. The convention that N is marked "only where we checked" is stated in Table 5's caption, not Table 6's.
    **Suggested fix:** Mark "5; needs N", or add "setup not checked" to Table 6's caption.
    **Severity:** should-fix.

18. **Location:** §5.3 (l. 249), "have been disproved in the form in which they were stated [A47]".
    **Problem:** [A47] is an unrefereed ePrint whose abstract gives no concrete parameters. The literature check's safe wording is "refuted in 2025–26 preprints". It also records counterexamples at rate tending to 0 or radius near capacity, and an opposing unrefereed claim (Okamoto). Nothing shows the refutation reaches rates 1/2 or 1/16.
    **Suggested fix:** "a 2025 preprint gives counterexamples to … in the form in which they were stated [A47]; their effect at these rates is not established."
    **Severity:** should-fix.

19. **Location:** Competing Interests (l. 366), REV-09.
    **Problem:** This is still unresolved. The editor asked whether the employer offers products in a compared evidence class, for example attestation. The response defers it to the author, which is honest, but the paper cannot go out without the statement.
    **Suggested fix:** The author adds one sentence.
    **Severity:** should-fix (blocking for submission).

20. **Location:** §4.2 Granularity, "it stays strict only when soundness is separated"; §5.4 same clause.
    **Problem:** The refinement is also strict against any proof system that needs N.
    **Suggested fix:** "only when soundness is separated or the proof system needs a setup".
    **Severity:** nit.

21. **Location:** REV-10 and REV-16 (both must_fix), response "partly".
    **Problem:** The response is accurate, but the acceptance criteria (per-strand counts; per-strand query strings) are still unmet for strands A–D. The re-run covers only the novelty statement.
    **Suggested fix:** Run and log a short documented search per strand, or have the editor accept the partial record explicitly.
    **Severity:** should-fix.

22. **Location:** §1 contribution 1 (l. 23), "no proof of the computation can establish the latter two".
    **Problem:** Three things precede "the latter two": ran on the serving path, gated, preceded release. The referent is ambiguous.
    **Suggested fix:** "can establish any of the three".
    **Severity:** should-fix.

23. **Location:** Abstract (l. 7), "…needs a mechanism on that path, which some attestation designs supply, a pre-release log can anchor in time, and a proof cannot."
    **Problem:** The relative clause has three verbs with different objects; a log does not anchor "a mechanism". The opening sentence also attaches "and compare their trust sets" after a purpose clause.
    **Suggested fix:** "…needs a mechanism on that path. Some attestation designs supply one; a pre-release log kept by another party can only fix the claimed verdict in time; a proof cannot."
    **Severity:** should-fix.

24. **Location:** §2.2 (l. 53), attribution "is where our order and the closest prior order differ".
    **Problem:** §6 says the orders differ "in two places", and attribution is one of them.
    **Suggested fix:** "is one of the two places where …".
    **Severity:** nit.

25. **Location:** Table 1 replay row (l. 180), REV-22.
    **Problem:** The acceptance criterion names "the Table 1 replay row or its note". No note says that digest-identified weights put the hash in E under this paper's convention, or in K under the alternative. The response does not claim Table 1, so this is not an overstatement.
    **Suggested fix:** Add the note "weight authenticity by digest is booked to E (§4.1); charging it to K: §4.2 Granularity".
    **Severity:** nit.

26. **Location:** §4.2 (l. 118), "The 11 pairs that involve the bottom class".
    **Problem:** The bottom class is a merged class. The 11 pairs are those involving 0a or 2, including 0a–2.
    **Suggested fix:** "that involve 0a or 2".
    **Severity:** nit.

27. **Location:** §5.3 opening (l. 234), "for readers who skip the figures".
    **Problem:** "Figures" can be read as Figures 1–2; the numbers are meant.
    **Suggested fix:** "who skip the numbers".
    **Severity:** nit.

28. **Location:** §5.3 (l. 247) and response REV-25.
    **Problem:** The response says "LogUp-GKR" and the text says "GKR (sum-check)". The SASH README supports LogUp-GKR, not the word sum-check, per the literature check. GKR is never expanded.
    **Suggested fix:** Use "LogUp-GKR arguments", and expand GKR once.
    **Severity:** nit.

29. **Location:** Gap 1 (l. 333), "Deployed attested services [B26] and attested audit workflows [B25] show that the attestation half has been built at production scale [B26] and composed into audit workflows [B25]".
    **Problem:** Each citation appears twice and each claim is stated twice.
    **Suggested fix:** "The attestation half has been built at production scale [B26] and composed into audit workflows [B25]".
    **Severity:** nit.

30. **Location:** §4.3 class 4 appraisal sentence (l. 166).
    **Problem:** "How the vendor recovers its trusted computing base" is a vendor action, not a verifier policy. "As forgeries that pass at the UpToDate level show" leaves unsaid what they show.
    **Suggested fix:** "…and whether it accepts a platform before the vendor's TCB recovery after a disclosed attack; forgeries that pass at the UpToDate level [B16] show that current status alone is not enough."
    **Severity:** nit.

31. **Location:** §4.3 class 4, "BadRAM and Battering RAM used memory aliasing to replay SEV-SNP launch measurements".
    **Problem:** The literature check confirms the launch-digest replay for Battering RAM. For BadRAM it confirms only "faking remote attestation reports" via aliasing and ciphertext replay or RMP modification, not the launch-measurement mechanism specifically.
    **Suggested fix:** "used memory aliasing to make a modified SEV-SNP virtual machine attest as genuine [B27], [B28]".
    **Severity:** nit.

32. **Location:** §2.1 (l. 36), "a supervisory authority … which can usually compel the disclosure".
    **Problem:** A legal generalisation with no citation.
    **Suggested fix:** Use "may be able to compel", or cite the relevant AI Act powers.
    **Severity:** nit.

33. **Location:** REV-08 (Box 1).
    **Problem:** The roadmap also asked to drop profile names and config flags from the §5 prose. `y-attnout-w12` and `all-pass` remain in §5.1 and §5.2. The response claims Box 1 only, so this is not an overstatement.
    **Suggested fix:** Optionally move the profile name to a footnote or the DAA.
    **Severity:** nit.

34. **Location:** Gap 3 (l. 335), "a proof without hiding may reveal information about its witness".
    **Problem:** Box 1 says the witnesses are public, so the bundle reveals the witness rather than merely "may reveal information".
    **Suggested fix:** "with public witnesses the bundle reveals the witness, so it should be handled as R is".
    **Severity:** nit.

35. **Location:** Table 2 class 5 cell, "V = C(R) was computed, by someone, at some time".
    **Problem:** This is event wording, against the value reading that §1 and §2.2 now define ("says neither who computed it nor when").
    **Suggested fix:** "V = C(R) holds; says nothing of who computed it or when".
    **Severity:** nit.

## Items checked and found as stated

- **REV-02, REV-05, REV-37:** no "auditor's order" or "reverses" anywhere; L replaces the tolerance T in §4.1, §4.2, Table 1 and Figure 1.
- **REV-35:** "Hollow-LLM attack" is used throughout, with "ghost weights" as the source's term; no "Hollow weights" or "hidden-weight" remains.
- **REV-04:** Table B1 and Appendix B are present; no stale "Section 5.5" pointer for costs.
- **Renumbered tables:** Table 4 is the placement table, Tables 5 and 6 are the published figures and positioning, and gap 4 points to Table B1.
- **Citations:** cited keys and listed keys match, with 104 entries.
- **REV-27:** ADR 0070 supports the patched verifier, "dirty: true" and the 23 compiled shape roots.
- **REV-42:** `docs/LLM-PROOF.md` supports the signed Ed25519 enrollment with no revocation service.
- **REV-52:** `docs/COMPOSED-DEMO.md` supports the classifier proofs binding the response through the shared context.
- **REV-51:** `scripts/composed_input.py` (`check_request`) supports "tokenization was enrolled separately".
- **REV-20:** `measure_native_rerun.py` now records the commit and CPU model.
- **REV-36:** the zkGPT description is supported.
- **WireTap:** the description matches the literature check.
- **REV-31:** the S-two whitepaper [A46] is used as the literature check recommends, and the response labels it "partly".
- **§5.3 arithmetic:** 41.5, 89, 50 and 176 bits recompute correctly.
