# Literature check: reviewer-raised claims and novelty search

Run date: 2026-11-02. Every query used generic topic terms or the paper titles and names listed in the task. No manuscript text and nothing from `research/source/` went into any query. Quotes are short excerpts taken from the primary page named in each entry.

## Job 1: verification of specific claims

1. **BadRAM**: exists.
   - Title: "BadRAM: Practical Memory Aliasing Attacks on Trusted Execution Environments".
   - Authors: Jesse De Meulemeester, Luca Wilke, David Oswald, Thomas Eisenbarth, Ingrid Verbauwhede, Jo Van Bulck.
   - Venue: 46th IEEE Symposium on Security and Privacy (S&P 2025), May 2025.
   - Primary page: https://badram.eu. CVE-2024-21944, AMD-SB-3015.
   - Summary: A rogue DIMM SPD chip makes the CPU alias "ghost" addresses onto real memory. On SEV-SNP this lets an attacker corrupt or replay ciphertext and directly modify the unencrypted RMP. The project page says this allows "faking remote attestation reports and inserting backdoors into *any* SEV-protected VM". So it breaks both integrity and attestation on SEV-SNP until AMD's boot-time firmware alias check is applied. The page says Intel SGX and TDX already counter this static aliasing.

2. **Battering RAM**: exists. It was disclosed in Oct 2025, but its venue is S&P **2026**, not 2025.
   - Title: "Battering RAM: Low-Cost Interposer Attacks on Confidential Computing via Dynamic Memory Aliasing".
   - Authors: Jesse De Meulemeester, David Oswald, Ingrid Verbauwhede, Jo Van Bulck.
   - Venue: 47th IEEE S&P (2026).
   - Primary page: https://batteringram.eu.
   - Summary: A sub-$50 DDR4 interposer creates memory aliases dynamically at runtime, which gets past the boot-time alias checks added after BadRAM.
     - On Scalable SGX, the page says it "enables arbitrary plaintext access to SGX-protected memory" (read, and write of plaintext into enclaves). That is a confidentiality and integrity break.
     - On SEV-SNP, it "breaks SEV's attestation feature on fully patched systems" by replaying the launch-digest ciphertext, so a backdoored VM attests as genuine.
     - The page does not claim a confidentiality break for SEV-SNP. Press reports of SGX provisioning-key extraction are secondary.

3. **WireTap**: exists.
   - Title: "WireTap: Breaking Server SGX via DRAM Bus Interposition".
   - Authors: Alex Seto, Oytun Kuday Duran, Samy Amer, Jalen Chuang, Stephan van Schaik, Daniel Genkin, Christina Garman.
   - Venue: ACM CCS 2025.
   - Primary page: https://wiretap.fail.
   - Summary: A passive DDR4 bus interposer exploits SGX's deterministic memory encryption. It recovers the **SGX Quoting Enclave ECDSA attestation (quote-signing) key** from a single signing operation. The page says the key "can be used to sign arbitrary SGX enclave reports". The page names DCAP only as the verifier (Intel's DCAP Quote Verification Library) that accepted the forged quote. Calling it "the DCAP key" is loose. "The QE's ECDSA attestation key, so forged quotes pass DCAP verification" is accurate.

4. **Reed–Solomon proximity gaps "up to capacity"**: yes, there are published refutations, all of them preprints.
   - (a) **Diamond & Gruen, "On the Distribution of the Distances of Random Words"**, ePrint 2025/2010 (the page notes CRYPTO 2026). https://eprint.iacr.org/2025/2010
     - It builds infinite RS code families whose ball-volume fraction decays slower than n^c/q.
     - It argues "the capacity conjecture of Ben-Sasson, Carmon, Ishai, Kopparty and Saraf (J. ACM '23) is false".
     - The counterexamples have relative rate tending to 0 and relative radius tending to 1. The authors propose restricting the conjecture to rates bounded below by a constant.
   - (b) **Crites & Stewart, "On Reed–Solomon Proximity Gaps Conjectures"**, ePrint 2025/2046 (Nov 2025, revised Dec 2025). https://eprint.iacr.org/2025/2046
     - It disproves BCIKS's correlated-agreement up-to-capacity conjecture, WHIR's mutual correlated-agreement up-to-capacity conjecture, and the DEEP-FRI list-decodability up-to-capacity conjecture. It says the last one follows from existing results.
     - It proposes minimally modified conjectures, and proves that correlated agreement with small enough error implies RS list decoding.
     - The abstract page gives no concrete parameters.
   - (c) **Krachun, Kazanin & Haböck, "Failure of proximity gaps close to capacity"**, ePrint 2026/782 (April 2026, so not a 2025 paper). https://eprint.iacr.org/2026/782
     - It is a simple counterexample for RS codes over multiplicative subgroups of prime fields, at δ = 1 − ρ − η with η = Θ_ρ(1/log n).
     - An affine line that is not entirely δ-close still contains 2^{Ω_ρ(1/η)} δ-close points. In the page's words, gaps fail "at least not as conjectured by Ben-Sasson, et al., in BCIKS20".
   - **Johnson-bound results still stand. They are theorems, and none of the papers above targets them.**
     - BCIKS, "Proximity Gaps for Reed-Solomon Codes", ePrint 2020/654 (FOCS 2020; the J. ACM 2023 version is the one the refutations cite), proves the gap "to any δ smaller than the Johnson/Guruswami-Sudan list-decoding bound". https://eprint.iacr.org/2020/654
     - Ben-Sasson, Carmon, Haböck, Kopparty & Saraf, "On Proximity Gaps for Reed–Solomon Codes", ePrint 2025/2055 and ECCC TR25-169 (Nov 2025), tightens this. Up to the Johnson radius, zero proximity loss now needs only O(n) exceptional z's instead of O(n²). It also shows that beyond Johnson, some codes need Ω(n^1.99) exceptions. https://eprint.iacr.org/2025/2055
   - Opposite claim: Okamoto, ePrint 2025/1712, claims a full resolution of correlated agreement up to capacity. It is unrefereed and was not checked here. Do not cite it as settled.
   - Safe wording: the up-to-capacity conjectures, in their BCIKS / WHIR / DEEP-FRI form, have been refuted in 2025–26 preprints. Security analyses that rely only on the proven Johnson-bound regime are unaffected.

5. **Circle STARKs** (Haböck, Levit, Papini; ePrint 2024/278, Feb 2024; https://eprint.iacr.org/2024/278): **not verified from the primary page.**
   - The abstract covers only the circle-curve construction and benchmarks (about 1.4× over BabyBear). It does not mention proximity gaps, FRI soundness or the Johnson bound.
   - The full PDF returned HTTP 403 to both WebFetch and curl. Secondary search snippets say the paper has an appendix on soundness of the IOP of proximity to circle codes, but I could not confirm the bound it proves.
   - A citable primary source for a Johnson-bound circle result is the **S-two Whitepaper** (Carmon, Goldberg, Haböck, Lerer, Lesokhin, Papini, Samocha; ePrint 2026/532). Its abstract says: "We show that multi-table circle FRI satisfies this notion up to the Johnson bound of the code" (the notion is cross-domain correlated agreement). https://eprint.iacr.org/2026/532
   - Action: either check 2024/278 by hand before attributing a Johnson-bound proximity gap to it, or cite 2026/532 for that statement.

6. **zkGPT**: exists.
   - Title: "zkGPT: An Efficient Non-interactive Zero-knowledge Proof Framework for LLM Inference".
   - Authors: Wenjie Qu, Yijun Sun, Xuanming Liu, Tao Lu, Yanpei Guo, Kai Chen, Jiaheng Zhang (NUS / HKUST).
   - Venue: 34th USENIX Security Symposium (2025), pp. 2045–2063. Also ePrint 2025/1184.
   - Primary pages: https://www.usenix.org/conference/usenixsecurity25/presentation/qu-zkgpt and https://eprint.iacr.org/2025/1184.
   - Summary: It proves that a committed (private-weight) model ran inference, aimed at providers who swap in cheaper models. The abstract says it "can prove GPT-2 inference in less than 25 seconds", with about 279× and 185× speedups over Hao et al. (USENIX Sec '24) and ZKML (EuroSys '24).

7. **Hollow-LLM**: exists.
   - Title: "Hollow-LLM Attack: Computationally Trivial Weights in Zero-Knowledge Verification of LLM Inference".
   - Authors: Chen Gong, Beijie Liu, Mengyuan Li.
   - Venue: arXiv:2607.28884, v1 dated 30 Jul 2026. The listing notes acceptance at IEEE S&P 2026. https://arxiv.org/abs/2607.28884
   - Naming in the source: the attack is the "**Hollow-LLM Attack**". The weights are "**ghost weights**", as in "embeds ghost weights whose algebraic structure collapses effective computation". The resulting setups are "**hollow deployments**".
   - The abstract does **not** use "hollow weights". Use "Hollow-LLM attack" / "ghost weights".

8. **SASH zk-inference-prover** (https://github.com/sg-ai-safety-hub/zk-inference-prover): partly confirmed.
   - The top README calls it "A STARK prover for the decode step of a quantized transformer", built on "the vendored Circle STARK library".
   - `prover/README.md` describes `--gkr-*` flags that "choose the LogUp-GKR backend for a component and change the proof, not the statement". It also mentions "the five GKR reductions", LogUp kernels, and FRI parameters in the security block.
   - Neither README uses the word "sum-check". So "Circle STARK with LogUp-GKR" is supported by the READMEs. "Sum-check" is true of GKR in general, but the README does not say it. `docs/statement.md` was not checked.

## Job 2: documented novelty search

Claim tested: no peer-reviewed or preprint work reports **succinct per-request proofs of a guardrail/safety-classifier verdict composed with a proof of the LLM's answer on the same request**.

Screening rule: the first 20 results were screened, or all results if there were fewer. A result counts as relevant if it involves cryptographic or TEE evidence that a guardrail, moderation or safety-classifier step ran, or composes ML-inference proofs across models or steps. Any work proving both a classifier verdict and the model's answer for one request would contradict the claim. All queries were run on 2026-11-02.

| # | Source | Exact query | Hits / screened | Relevant results (reason) |
|---|---|---|---|---|
| W1 | Web search | `"zero-knowledge proof" guardrail classifier LLM` | 10 / 10 | zkLLM arXiv 2404.16109 (LLM-only ZK proof; background). Others are formal verification, not cryptographic. |
| W2 | Web search | `"verifiable" "safety classifier" LLM proof` | 10 / 10 | None ("verifiable" used in the formal-verification or RLVR sense). |
| W3 | Web search | `zkML "content moderation" proof` | 10 / 10 | None in the literature. Only vendor docs (Inference Labs) and a hackathon demo (ETHGlobal zkmsocial). |
| W4 | Web search | `"proof of guardrail"` | 21 / 21 | Proof-of-Guardrail, arXiv 2603.05786 (TEE attestation of a guardrail run; see findings). |
| W5 | Web search | `"zero-knowledge" "LLM inference" "safety filter"` | 10 / 10 | zkGPT, zkLLM, NANOZK (ICLR 2026), VerInf. All prove LLM inference only, with no classifier. |
| W6 | Web search | `"verifiable inference" guardrail attestation` | 10 / 10 | Proof-of-Guardrail 2603.05786; Laminator arXiv 2406.17548 (TEE per-inference "inference cards", no guardrail composition). |
| W7 | Web search | `"zkLLM" OR "zero-knowledge LLM" composition classifier` | 10 / 10 | zkLLM only (LLM-only). |
| W8 | Web search | `"attested guardrail" OR "verifiable moderation"` | 10 / 10 | None (E2EE moderation SoK 2303.03979, VARM-Bench, vendor docs). |
| W9 | Web search | `zero-knowledge proof LLM output and Llama Guard safety classifier verdict same request` | 10 / 10 | None (zkLLM, VerInf, Llama Guard taken separately). |
| W10 | Web search | `verifiable LLM inference plus verifiable moderation classifier zkML pipeline proof composition 2026` | 10 / 10 | zkComposer arXiv 2607.08095 (splits one model's proof into sub-proofs, not cross-model); OpenLLM ePrint 2026/1578; DeepProve ePrint 2026/1112. None prove a classifier. |
| A1 | arXiv API | `all:"zero-knowledge" AND all:guardrail` | 3 / 3 | NiyamAI 2608.07167 (**closest; see findings**); Jolt Atlas 2602.17452 (mentions guardrails only as a companion-work use case); "No Certificate, No Execution" 2605.24462 (conceptual; ZK certificates only mentioned). |
| A2 | arXiv API | `all:"zero-knowledge" AND all:"safety classifier"` | 0 | — |
| A3 | arXiv API | `all:verifiable AND all:"safety classifier"` | 3 / 3 | None. |
| A4 | arXiv API | `all:zkML AND all:moderation` | 0 | — |
| A5 | arXiv API | `all:"proof of guardrail"` | 1 / 1 | Proof-of-Guardrail 2603.05786. |
| A6 | arXiv API | `all:"zero-knowledge" AND all:"LLM inference" AND all:"safety filter"` | 0 | — |
| A7 | arXiv API | `all:"verifiable inference" AND all:guardrail` | 1 / 1 | Jolt Atlas 2602.17452 (see A1). |
| A8 | arXiv API | `all:zkLLM AND all:classifier` | 1 / 1 | None (2603.10060 argues for tool receipts instead of ZK). |
| A9 | arXiv API | `all:"attested guardrail"` | 0 | — |
| A10 | arXiv API | `all:"verifiable moderation"` | 1 / 1 | None (VARM-Bench; "verifiable reasoning" is not cryptographic). |
| A11 | arXiv API | `all:"zero-knowledge" AND all:"content moderation"` | 0 | — |
| A12 | arXiv API | `all:verifiable AND all:guardrails AND all:LLM` | 53 / 20 | NiyamAI 2608.07167. The other 19 use "verifiable" in a non-cryptographic sense. |
| A13 | arXiv API | `all:"zero-knowledge" AND all:"LLM" AND all:"moderation"` | 0 | — |
| A14 | arXiv API | `all:zkML AND all:safety` | 0 | — |
| A15 | arXiv API | `all:"zero-knowledge" AND all:"Llama Guard"` | 0 | — |
| A16 | arXiv API | `all:"zero-knowledge" AND all:LLM AND all:guardrails` | 1 / 1 | NiyamAI 2608.07167. |
| E1 | IACR ePrint search | `guardrail` | 1 / 1 | None. |
| E2 | IACR ePrint search | `content moderation` | 22 / 20 | None (E2EE abuse reporting and message franking; no ML classifier). |
| E3 | IACR ePrint search | `LLM inference` | 32 / 20 | DeepProve 2026/1112, OpenLLM 2026/1578 (LLM-only); zkAgent 2026/199 (composes the LLM proof with tool-execution zkTLS/zkVM subproofs, **no classifier**). |
| E4 | IACR ePrint search | `safety classifier` | 3 / 3 | None. |
| E5 | IACR ePrint search | `zkML` | 14 / 14 | zkGPT 2025/1184, zkAgent 2026/199. No classifier+LLM composition. |
| E6 | IACR ePrint search | `zero-knowledge machine learning safety` | 0 | — |
| E7 | IACR ePrint search | `moderation zero-knowledge` | 18 / 18 | None (zk-promises 2024/1260 covers anonymous moderation by credentials, not ML). |
| G1 | Google Scholar (served fr locale) | `"zero-knowledge" guardrail classifier LLM proof` | ~54 / 20 (2 pages) | NiyamAI; "Confidential Prompt Filters for LLMs: … ZK Embedding Gates and TEEs" (Mohammed, Springer LNNS 2026; see findings); ZKMLOps survey arXiv 2505.20136 (review, no system). |
| G2 | Google Scholar | `zkML "content moderation" proof` | 5 / 5 | NiyamAI. The others are conceptual or off-topic. |
| G3 | Google Scholar | `"zero-knowledge" "LLM inference" "safety filter"` | 1 / 1 | None. |
| G4 | Google Scholar | `"Confidential Prompt Filters for Large Language Models"` (title lookup) | 2 / 2 | Same chapter (Springer and Google Books entries). |

Follow-up primary-page checks: arXiv abstract pages for 2608.07167, 2603.05786 (HTML full text), 2602.17452, 2605.24462 and 2606.26686; ePrint pages for 2026/199, 2026/1112 and 2026/1578; Crossref metadata for DOI 10.1007/978-3-032-39783-6_19, which has no abstract. Springer and Google Books did not serve that chapter's abstract.

### Findings

**No work found contradicts the bounded novelty claim.** Nothing in the screened results proves both a guardrail/safety-classifier verdict and the LLM's answer on the same request. The claim survives only in its composed form. The paper should cite the closest works and word the claim so that it does not imply that a per-request succinct proof of a classifier verdict is new in itself:

1. **NiyamAI** (Katkar, Karkele, Mandhane, More, Kashid; arXiv 2608.07167, v1 7 Aug 2026, v2 27 Aug 2026). This is **a per-request succinct ZK proof of a safety-classifier verdict**.
   - For each authorized agent tool action, EZKL compiles a small neural "Judge" (an 11→8→2 MLP) into a Halo2-KZG circuit. The proof binds IntentHash, ActionHash and the Judge weights. It takes about 1.7 s to prove and about 51 ms to verify a proof of about 18.6 KB.
   - The LLM itself is **explicitly not proven**: "Proving inference over a multibillion parameter LLM remains infeasible" (Sec. 1).
   - So it does not contradict the composed claim, but it removes any novelty for "succinct per-request proof of a guardrail verdict" taken alone.
   - Differences from a Llama-Guard-class classifier: the classifier is a toy MLP over hand-built features, the setup uses a local test SRS, and the paper is a non-peer-reviewed preprint.
   - **Must be cited.**
2. **Proof-of-Guardrail in AI Agents and What (Not) to Trust from It** (Jin, Duan, Lin, Chan, Chen, Du, Ren; arXiv 2603.05786, Mar/Jun 2026).
   - It issues a per-input AWS Nitro Enclave attestation, committing to input and output, that an open-source guardrail (Llama Guard 3-8B, plus Loki for factuality) ran.
   - The LLM is an external API (GPT-5.1) and is not attested. The paper frames TEE as the alternative to "prohibitive zero-knowledge proofs".
   - It is the closest TEE-side analogue of a "guardrail ran on this response" record. It is not a succinct proof and does not cover the model's answer. **Must be cited.**
3. **Confidential Prompt Filters for LLMs: Privacy-Preserving Safety Enforcement via ZK Embedding Gates and TEEs** (M. B. R. Mohammed; Springer LNNS, *A New Direction for Informatics and Problem-Solving*, 2026; DOI 10.1007/978-3-032-39783-6_19).
   - From the Scholar snippet only: the *user* proves in ZK that a prompt meets the provider's policy (embedding gate), with a TEE variant.
   - This is input-side, user-proven and private-prompt. It is not a provider proof of a classifier verdict composed with an answer proof.
   - **Abstract not fully retrieved. Check the full text before relying on this reading.**
4. **zkAgent** (Wang, Lou, Li, Yu, Hu; ePrint 2026/199, listed as ACM CCS 2026). It composes one LLM-inference SNARK with zkTLS/zkVM subproofs for tool observations. This is precedent for composing an LLM proof with other per-request proofs, but there is no classifier. Worth citing as composition prior art.
5. **Jolt Atlas** (arXiv 2602.17452) says a companion work outlines zkML "guardrails in agentic commerce". That companion work was **not located** in this search and remains an open lead.

### Limitations

- Web search and Scholar ranking are not deterministic, and Scholar served a French locale.
- arXiv `all:` field search is token-based and can miss paraphrases.
- Not searched: ACM DL, IEEE Xplore, DBLP, OpenReview, or industry product documentation beyond what web search surfaced.
- Screening used titles, abstracts and snippets. Full text was read only for NiyamAI and Proof-of-Guardrail.
