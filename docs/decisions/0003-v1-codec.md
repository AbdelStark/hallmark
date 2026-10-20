# 0003: bounded v1 primitive codec

Date: 2026-10-20. Implements W01 / issue #2 and RFC-0001 under the owner's
autonomous backlog request. Enrollment remains subject to WIRE-REVIEW in RFC-0001.

Keep the research and legacy transcript functions unchanged. Add `hallmark.wire`
for the RFC-0001 value algebra and finite `hallmark/v1/` identity domains.
Canonical encoding uses the already locked cbor2 dependency. A restricted decoder
checks lengths, container depth, total item count, primitive types, key uniqueness
and key ordering before admitting a value, then compares canonical re-encoding.
It never invokes general CBOR tag hooks, shared references or object constructors.

Use the specified 64 MiB and 16-container hard caps. Also cap the total value count
at 1,048,576, including containers and map keys, to bound memory amplification from
small encoded elements. Callers may lower these limits. Encoding validates size and
type before serialization, including bounded temporary UTF-8 conversions.
The raw codec returns values; future artifact-schema decoding must separately
enforce exact field sets and versions. No decoded value supplies trust.

Fixed byte vectors follow [RFC 8949 Appendix A](https://www.rfc-editor.org/rfc/rfc8949.html#appendix-A)
and its [length-first map order](https://www.rfc-editor.org/rfc/rfc8949.html#section-4.2.3).
Tests include negative variants, all truncations of seeded structured examples,
comparison with cbor2's decoder and unchanged fixed legacy hashes. These are
software conformance checks, not independent security review, enrollment,
hardware evidence or a proof. No historical research result is reused as v1 evidence.
