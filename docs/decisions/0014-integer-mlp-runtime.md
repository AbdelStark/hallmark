# 0014: Bound byte-count MLP exports and exact native execution

Date: 2026-10-20. Status: implemented native software contract, pending owner
protocol adoption. Implements W11 / #12. No previous research result is reused.
Training, policy admission, proof qualification and independent verification
remain separate gates.

## Export and identity

`hallmark.integer_mlp.execute_mlp` accepts an opening, classifier, `MlpProgram`,
input profile, arithmetic profile, exact weight bytes and operator-parameter
bytes. It performs no file or network access. References are checked against the
bytes supplied by the caller; they never authorize fetching a path.

The versioned [program](../schemas/mlp-program-v1.json) contains:

- `schema_id="hallmark/mlp-program/1"`;
- `input_profile` and `arithmetic`, the complete profile identities;
- `weights`, one `FileRef` for the canonical CBOR weight record.

Its identity is `H("program", complete program)`. The classifier must have kind
`mlp` and bind this program and both profiles. `ClassifierManifest.weights`
is the raw SHA-256 of the complete canonical weight file, equal to
`program.weights.sha256`; it is not a new typed hash domain. Changing a weight,
bias, numerical profile, path or input recipe changes the program/classifier
identity. Operator files remain pinned by the arithmetic profile. Weight and
operator paths must be distinct; repeated affine parameter references retain
the existing exact-file identity checks.

The [weight record](../schemas/mlp-weights-v1.json) has
`schema_id="hallmark/mlp-weights/1"` and exactly:

| Field | Stored values and shape |
|---|---|
| `hidden_weights` | Signed int8, `[H,256]`, row-major byte order 0..255 |
| `hidden_bias` | Signed int32, `[H]` |
| `output_weights` | Signed int8, `[H]`, interpreted as graph shape `[1,H]` |
| `output_bias` | One signed int32, interpreted as graph shape `[1]` |

`1 <= H <= 64`. Booleans/floats, ragged rows, missing fields and dimensional
disagreement are rejected. The file is bounded to 65,536 bytes and 20,000 wire
items before decoding. Canonical CBOR and the existing strict schemas are required.
This is a format for caller-exported integers, not a quantizer or trainer.

## Fixed numerical graph

The arithmetic profile must contain exactly eight distinct tensors and three
ordered nodes: affine → ReLU → affine. Tensor names are arbitrary identifiers;
the node edges assign these roles:

| Role | Shape | Signed bits | Fractional bits |
|---|---|---|---|
| Byte counts | `[256]` | 32 | 0 |
| First weights | `[H,256]` | 8 | `f1` |
| First bias | `[H]` | 32 | `f1` |
| Hidden affine output | `[H]` | 32 | `fh` |
| ReLU output | `[H]` | 32 | `fh` |
| Output weights | `[1,H]` | 8 | `f2` |
| Output bias | `[1]` | 32 | `fh+f2` |
| Score | `[1]` | 32 | 0 |

All fractional widths must fit the existing 0..30 profile range, including
`fh+f2`. Count bounds are exactly `[0, chunk_size]`. Actual weight and bias values
must lie inside their tensor declarations. Existing topology, parameter-file,
shape, scale and conservative range validation remains mandatory.

For each chunk, compute the mathematical dot product plus bias. Accumulation
starts with the bias and visits byte indices or hidden indices in increasing
order. Products are exact widened integers; every partial accumulated sum must
fit signed int32 **before** rescaling. No wrap or saturation is allowed.
Admission checks bound every partial sum using declared input intervals and
actual weights. Runtime checks repeat the int32 condition on actual sums.
A representable final/rescaled result cannot rescue an overflowing prefix.

After each affine operation, rescale its complete sum exactly once to the output
fractional width using nearest ties-to-even. Negative halfways obey the same rule:
`-1/2 -> 0`, `-3/2 -> -2`, `-5/2 -> -2`. Increasing fractional width is an exact
left shift with the declared output-range check. ReLU computes `max(0, stored)`
without a second rescale. Existing profile checks use conservative independent
intervals and may reject tighter safe exports; this implementation does not
weaken them based on unproved correlations.

## Complete input and bounded result

Only the opening's complete prompt UTF-8 bytes enter features. Response text,
Unicode normalization, character-boundary repair and tokenizer inference do not.
Split bytes contiguously at the declared chunk size. Empty input has one empty
chunk. Count only actual content bytes; masked right-padding contributes zero,
even when the padding ID equals a real byte such as NUL or `A`. Actual NUL bytes
are counted normally. Prefix/suffix tokens and token profiles are inadmissible.

Compute every chunk score and return the maximum. The verdict is strictly
`score < classifier.threshold`; equality blocks. Return the existing salted
complete-input digest from the exact opening/classifier/profile, plus a
[native result](../schemas/mlp-result-v1.json) with per-chunk counts, raw affine
accumulators, rescaled hidden values, ReLU values and scores.

The result checks chunk order/coverage, layer dimensions, maximum score and
threshold consistency. It is a diagnostic record, not authenticated computation:
parsing a result or seeing `verdict:true` does not verify either evidence claim.
Trace fields and weights are omitted from object repr, but serialization discloses
their contents. Keep real traces on authorized private channels; do not attach
them to a public receipt, log or issue.

Input-profile limits still apply. Execution additionally rejects more than
1,024 chunks or 2,097,152 affine products (`chunks * H * 257`) before feature/
layer execution. It never truncates. These local fixture-runtime limits may reject
an input otherwise admitted by a broader input profile; check the intended workload
before enrollment. They do not supply worker isolation, an RSS guarantee or a
performance claim. Changing these execution limits requires a documented decision
and authorized validation, not an implicit escalation for a failed run.

## Reproduction and migration

Run the public, hand-specified marker fixtures:

```sh
uv run --locked python scripts/check_mlp_vectors.py fixtures/wire/integer-mlp-v1.json
uv run --locked pytest tests/test_integer_mlp.py
make check
make package-check
```

The fixture builder writes only a fresh file:

```sh
uv run --locked python scripts/build_mlp_fixture.py --output /tmp/hallmark-mlp-fresh.json
cmp fixtures/wire/integer-mlp-v1.json /tmp/hallmark-mlp-fresh.json
```

Fixed vectors and 60 seeded cases compare all intermediate layers against a
separate direct byte-sum and quotient/remainder formula. That formula shares no
runtime rescaling/affine helper, but its repository provenance and artifact
contracts are shared. It is not the independently developed W34 verifier.
All weights are deterministic synthetic markers under the existing repository
licence; they are not a trained policy or evidence of detection quality.

New exports must pin their exact files, profiles and threshold before evaluation.
Training/calibration changes belong to a new admitted experiment. Existing
byte-linear arithmetic, all prior artifact identities and the frozen W33 corpus
remain unchanged. W11's numerical vectors are a separate fixture; W33 still has
32 unavailable genuine-evidence obligations. A future proof adapter must constrain
this complete computation and binding before any proof acceptance is claimed.
See [numeric results and the preserved file-alias failure](../../research/evidence/w11-integer-mlp-2026-10-20.json).
