# 0071: Reject token aliases and malformed native proof shapes

2026-10-23. Bounded follow-up to decision 0070 and issue #19. The original
Linux verifier, proof generation, quantization and caller enrollment stay frozen.
This changes the optional native verifier and its regression suite.

## Baseline and acceptance

The baseline is PR #101's native executable and the unchanged 23-proof TinyLlama
bundle. A new 24-case probe bypasses the Python caller deliberately, checks two
honest controls, and records acceptance, explicit rejection and process failure
separately. Inputs, mutation code and resource bounds are frozen before execution:
600 seconds, four threads, 4 GiB sampled process-group RSS and no cloud jobs.

The baseline accepts an output token ID increased by the M31 modulus. The Rust
Horner check reduces IDs into the field without a vocabulary-range check. The
changed final EOS token has no successor input to compare against. The existing
Python caller rejects that ID before verification; this is a native-boundary
gap, not an accepted false response through the complete Hallmark workflow.

Four malformed shapes terminate the process: empty commitment, decommitment and
query lists, and an empty preprocessed column-size vector. Six aliases inside
claims and proof fields reject cryptographically. The direct input-token alias
also rejects at the grid's prompt comparison.

Three altered proof configuration records and two unknown JSON fields are
accepted. The verifier uses its own pinned security configuration, so changing
the redundant record does not weaken the actual checks. Unknown fields have no
proved meaning; this work does not add a canonical JSON encoding requirement.

Pass criterion: both honest controls still verify; the original 14 mutations,
two enrollment mutations and 20 new native boundary mutations return explicit
rejections with the expected reason. Crashes and unparsable reports fail the
suite. All original proof bytes must remain unchanged. Record candidate failures
and do not reuse the baseline's measurements as candidate results.

## Change

Before cryptographic processing, reject input/output token IDs outside the
enrolled embedding/head vocabulary; require exact proof-tree counts; compare
preprocessed column sizes against the trusted plan; and check sampled-column
counts. Column log sizes must fit the M31 domain after the pinned one-bit blowup.
Reject mismatched redundant proof configuration rather than silently ignoring it.
Return early when derived trace sizes disagree, before passing them to Stwo.

These checks preserve the existing constraints, transcript, root enrollment and
honest proof encoding. They do not normalize IDs or catch and relabel arbitrary
panics. The new regression cases deliberately bypass the caller and require
structured native failures. A caller regression separately preserves rejection
of the discovered output-token alias.

The native verifier still trusts compiled caller enrollment. This experiment
does not authenticate that enrollment, prove all malformed inputs harmless,
establish hiding or replace independent security review. Issue #19 stays open.

[Numeric evidence and raw artifact hashes](../../research/evidence/native-proof-boundaries-2026-10-23.json)
record each baseline outcome and fresh candidate run.
