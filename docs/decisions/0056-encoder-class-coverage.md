# Cover the fixed encoder's numerical chunk classes

Status: bounded W18 conformance research under standing owner approval,
2026-10-21. New experiment identity; prior experiments and evaluators stay fixed.

The frozen encoder has four distinct embedding pairs across its 256 byte tokens.
Each chunk has two fixed positions and a prefix mask. Token values enter the
numerical block only through their embedding lookup. With zero-valued padding,
the block therefore has 21 reachable numerical classes: one empty, four singleton
and sixteen ordered pairs. The existing 15-input proof fixture visits ten of
these classes. This is a coverage gap, not an observed arithmetic error.

Freeze a separate fixture using the first byte representative of each embedding
class. Decode and check the original native manifests, run every representative
through the native encoder, and compare all 39 tensors / 121 values with the
existing independent rational/Decimal oracle. Preserve the original graph,
constants, threshold, profiles and fixtures byte for byte. Every new assignment
has the original eight-byte capacity with three empty padded chunks.

Compile the unchanged complete circuit and solve all 21 assignments using both
original and locally patched dependencies. Alter the first private tensor value
in each assignment and require an unsatisfied constraint; an infrastructure error
cannot count as a rejection. Require all eight existing serialized circuit
fingerprints to remain unchanged. Add fixture-reproduction and solver checks to
the existing local/hosted gates, without changing the running maximum experiment.

The local protocol is frozen in `w18-encoder-classes-1792608913125688000` before
execution: at most 1,800 seconds, two compute threads, 4 GiB worker RSS, 1 GiB
outputs and zero spend. Record exact sources, environment, raw costs and failures.
This exercises solver witnesses, not new cryptographic proofs. Numerical class
coverage is conditional on these exact constants and two-position block: it does
not exhaust transcript encodings, full-input commitment bindings, aggregation
sequences, arbitrary learned weights or security properties. No prior result is
relabeled exhaustive. Backend qualification and operational enrollment remain
unavailable; no policy or release decision follows.
