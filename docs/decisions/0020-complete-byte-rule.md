# 0020: Complete-byte literal rule execution

Date: 2026-10-20. Status: native engineering contract.
Scope: [W10 / #11](https://github.com/AbdelStark/hallmark/issues/11).
No historical experiment or frozen conformance corpus is changed or reused.

`hallmark.rule` implements `RuleProgram`, `RuleResult` and `execute_rule`.
The program uses the existing `program` hash domain with schema
`hallmark/rule-program/1`. It binds the input/arithmetic identities, a sorted
unique nonempty tuple of nonempty byte patterns and a provenance `FileRef`.
Total pattern bytes are at most 4,096; provenance is 1–16,384 exact bytes.
CBOR stores byte strings; JSON stores even-length hex strings of 2–8,192 characters.
Neither decoding nor execution reads files or fetches a source.

The classifier is `kind=rule`, has no weights/tokenizer, and has threshold one.
Its byte profile allows chunks of 1–512 bytes and at most 32,768 complete UTF-8
prompt bytes. Excess input rejects; nothing is truncated. The response is unused.
No Unicode normalization, case folding, regex, tokenization or implicit padding
enters matching. Invalid or bypass-constructed records are revalidated at entry.

## Native computation

Let `L` be the longest pattern length. Keep at most the final `L-1` content bytes
after each chunk. Search `suffix + content` for each literal pattern, counting a
match only if its final byte belongs to the current chunk. This covers patterns
longer than one or two chunks and avoids recounting a match wholly in the suffix.
For `L=1`, keep an empty suffix. Empty input creates one empty chunk with score
zero. Continue processing all chunks after an early match.

The feature is Boolean: one if any pattern ends in that chunk, zero otherwise.
For compatibility with the existing arithmetic contract, require exactly two
scalar signed-two-bit tensors, zero fractional bits and bounds `[0,1]`, connected
by one parameter-bound ReLU node. Execute that identity projection on the feature.
The literal feature extractor and cross-chunk state belong to `RuleProgram`;
they are **not encoded by the scalar arithmetic DAG**. A proof of that DAG alone
cannot satisfy W19. The complete future proof must constrain matching, suffix
transitions, all prompt bytes, the input commitment and aggregation.

The final score is the maximum chunk score; `verdict = score < 1`, so equality
blocks. `RuleResult` checks counts, aggregation and threshold consistency.
Its classifier identity resolves the exact program, while its input digest binds
the complete prompt through the existing classifier-specific salted commitment.
Results are private diagnostics: chunk scores reveal match locations.
The runtime verifies supplied identities and bytes, not external enrollment,
execution provenance or a proof.

## Provenance and coverage

The fixture contains only hand-authored `NUL`, `ABCDEF`, `MARK` and UTF-8 `é`
markers under the repository licence, with a hashed purpose/provenance document.
They are authorized harmless engineering fixtures, not an operational
`inj.direct/1` pattern set. The owner-approved study delegates future selection;
actual patterns must be selected using train only and pinned with source,
rubric-subset rationale and review evidence before measurement.

Literal equality is a narrow rubric subset. Quoted benign text may match;
paraphrases, capitalization and unlisted attack strings may not. No injection
quality, intent recognition, safety coverage or policy-adoption claim follows.
The provenance hash checks bytes, not their truth, legal sufficiency or approval.

## Validation

Fixed public vectors cover empty input, multi-chunk patterns, Unicode byte
boundaries, distinct normalization, real NUL versus padding and late matches.
An independent oracle enumerates matches by complete-input byte slices and their
ending positions. Seeded comparisons check every chunk, and the maximum-size
case places a 4,096-byte pattern across 4,096 one-byte chunks at the end of a
32,768-byte prompt.

Negatives reject malformed patterns, changed profile/program identities,
unsupported arithmetic, altered/missing/extra parameter files, provenance
substitution/path aliasing, resource excess and inconsistent result records.
Both package gates execute the fixed vectors against the freshly installed wheel.
These are software checks, not independently implemented proof verification.
