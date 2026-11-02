## Contract Paraphrase

D1 (methodology_rigor): From a domain-accuracy seat, I read this as asking whether the study's design, the way it handles and reports data, its statistics, and what it gives others to reproduce the work would satisfy a security and verifiable-computation reviewer. Domain accuracy depends on it because a correct claim about a proof system, an attestation scheme, or a logging mechanism still needs a measurement setup that matches how those mechanisms really behave. This dimension belongs to the methodology seat. I will raise domain-level problems with it as cross-references and will not score it.

D2 (domain_accuracy): This is my dimension, and it is mandatory. It asks whether every technical claim agrees with the current evidence in verifiable computation, trusted execution and remote attestation, transparency and append-only logging, and ML inference security. It asks whether prior systems, protocols, and results are described as their authors and the later literature actually establish them, without overstating or understating them. It also asks whether terms such as soundness, completeness, zero-knowledge, the trusted computing base, measurement, the root of trust, freshness, and binding are used with their accepted technical meanings, and whether any reported or cited quantitative results are stated correctly.

D3 (argumentative_coherence): I take this as asking whether the central thesis holds together: each conclusion should follow from the evidence offered, and no fallacy should carry the main argument. From a domain angle, the main risk is an argument that changes trust or threat models partway through, or that treats different assurance properties as if they were interchangeable. The devil's-advocate and methodology seats score it. I will only point out where a domain misstatement affects the argument.

D4 (cross_disciplinary_relevance): This asks whether readers from neighbouring fields, such as ML practitioners, AI governance and policy readers, or systems engineers, can follow the framing, definitions, and implications, and whether claims that cross field boundaries are backed up. My domain interest is whether simplifying for those readers keeps the precise security meaning intact. The perspective seat scores it.

D5 (writing_and_structure): This covers the manuscript's organisation, the clarity of its exposition, the quality of its figures and tables, and whether it follows venue conventions. From a domain viewpoint, clear writing matters most in how the paper presents threat models, trust assumptions, and protocol flows, because ambiguity there turns into technical ambiguity. The editor-in-chief seat scores it.

D6 (venue_fit_and_contribution): This mandatory dimension asks whether the work suits the configured venue and makes an original, significant contribution for that venue's readers. My domain input would be whether the claimed novelty holds up against the existing literature. The editor-in-chief seat scores it, and I make no venue-alignment claim.

## Scoring Plan

### D2: domain_accuracy
dimension_id: D2
what_to_look_for: Whether claims about proof systems, TEE remote attestation, transparency or tamper-evident logs, and ML inference integrity match established results; whether trust assumptions and the trusted computing base for each mechanism are stated correctly; whether cited prior work, including its security guarantees, known attacks, and performance figures, is represented as its sources support; and whether security terminology (soundness, zero-knowledge, attestation freshness, measurement, binding, root of trust, non-equivocation) is used with its standard meaning.
what_triggers_block: A substantive domain error that a central claim depends on: for example, giving a mechanism a security guarantee it does not provide, misstating the trust assumptions of proofs, attestation, or logs in a way that changes the paper's comparison, or misrepresenting a key prior result. The error must be fixable through revision without invalidating the whole contribution.
what_triggers_warn: Local imprecision that does not change a central conclusion: loose or inconsistent use of security terms, citations that are incomplete or slightly stale for relevant attacks or systems, unqualified generalisations about a class of mechanisms, or small misstatements of peripheral prior work or figures.
what_triggers_fatal: The core thesis rests on a domain-level falsehood that cannot be repaired. For example, the central account of what a verifier must trust contradicts established security results for the mechanisms compared, or the main contribution reproduces or contradicts well-established prior work without acknowledging it, so that the conclusions do not survive correction.

criteria_binding_unavailable

[CONTRACT-ACKNOWLEDGED]
