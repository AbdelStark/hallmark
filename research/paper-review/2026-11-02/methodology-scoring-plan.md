## Contract Paraphrase

D1 (methodology_rigor, mandatory, owned by methodology): From a rigor standpoint, the work must be built so that a skeptical reader can tell how each claim was produced and could redo the work. Any experiment, measurement, or formal argument needs a stated setup, a stated threat or trust model, and stated assumptions. Data and artifacts must be handled transparently. Quantitative results need their variance, repetition counts, and environment disclosed. Reproducibility affordances such as code, configurations, and recorded provenance must be enough for an independent rerun, judged against what a computer security venue expects.

D2 (domain_accuracy, mandatory, owned by domain): The manuscript's factual content must match the current state of the field. That means cited prior systems, primitives, and results are described the way their sources describe them, technical terms are used correctly, and no claim conflicts with established evidence. From the methodology seat, this dimension matters because an inaccurate baseline or a misdescribed primitive weakens any comparison built on it, but I will not score it.

D3 (argumentative_coherence, mandatory, owned by the devil's advocate, methodology also eligible): The central thesis must hold together internally. Each claim should be backed by evidence of matching strength. Conclusions should not reach past what the method can show, and the argument should not depend on a fallacy, a definition that drifts, or a hidden premise. For methodology rigor, the key question is whether the inference from evidence to claim is valid.

D4 (cross_disciplinary_relevance, high, owned by perspective): A reader from a neighbouring field should be able to follow the framing and definitions. Any claim about implications outside the core field must be supported rather than asserted. Methodologically, terms defined once and used the same way throughout make cross-field claims checkable. I will not score this dimension.

D5 (writing_and_structure, normal, owned by the editor-in-chief): The manuscript must be organised and clearly written, its figures and tables must communicate well, and it must follow venue conventions. Clear presentation of methods and results helps reproducibility, but scoring here belongs to the editor.

D6 (venue_fit_and_contribution, mandatory, owned by the editor-in-chief): The work must suit the target venue and make a contribution that is original and significant to that venue's readers. A contribution's significance depends partly on whether its supporting method is sound, but I will not judge fit or novelty in this phase.

## Scoring Plan

### D1: methodology_rigor
dimension_id: D1
what_to_look_for: An explicit threat and trust model with stated assumptions; for each empirical or formal claim, a described setup, environment, hardware and software versions, repetition counts, and dispersion statistics; a fair baseline or comparison design; transparent data and artifact handling; and reproducibility affordances (released code, configurations, provenance records, rerun instructions) enough for an independent rerun.
what_triggers_block: A headline quantitative or security claim rests on a measurement with no stated repetition count, variance, or environment, or on an unstated or inconsistent trust assumption, so the claim cannot be checked without a major revision of the method or reporting.
what_triggers_warn: The method is sound overall, but there are fixable gaps, such as missing confidence intervals on secondary results, partial environment or version disclosure, incomplete artifact or rerun instructions, or an underspecified threat model that does not change any headline result.
what_triggers_fatal: The central evidence is unsound at its foundation: a core result comes from a design that cannot measure what it claims, a load-bearing number is fabricated or cannot be traced to any described procedure, or the security argument depends on an assumption the work itself contradicts.

### D3: argumentative_coherence
dimension_id: D3
what_to_look_for: Whether each conclusion follows validly from the stated method and evidence, whether claim strength matches evidence strength, whether key terms and trust assumptions stay the same throughout, and whether limitations and scope boundaries are stated where the argument depends on them.
what_triggers_block: A main claim reaches clearly past its evidence, for example generalising from a narrow measurement or treating a conditional guarantee as unconditional, or a key term changes meaning between sections in a way that hides a gap, and fixing it needs substantial rewriting or new evidence.
what_triggers_warn: The thesis holds together, but some secondary claims are slightly overstated, some scope or limitation statements are missing or placed away from the claims they qualify, or some terms are used loosely without affecting the main inference.
what_triggers_fatal: The central thesis contradicts itself or rests on a fallacy or circular premise, so the main conclusion does not follow from the paper's own evidence even under a charitable reading.

criteria_binding_unavailable

[CONTRACT-ACKNOWLEDGED]
