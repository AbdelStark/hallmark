# 0006: classifier identities and parameter-bound arithmetic contracts

Date: 2026-10-20. Implements W04 / issue #5 under the autonomous backlog request.
This makes the draft RFC-0003 graph notation executable. WIRE-REVIEW and
INTEGER-GRAPH owner review still precede enrollment. No prior experiment is
reinterpreted, no graph/backend is qualified, and no classifier is executed.

## Artifacts and identity order

`hallmark.classifier_manifest` exports frozen `InputProfile`, `TensorSpec`,
`NodeSpec`, `ArithmeticProfile` and `ClassifierManifest`. Top-level schema IDs are
`hallmark/input-profile/1`, `hallmark/arithmetic/1` and `hallmark/classifier/1`.
Nested tensors and nodes have no separate schema ID or hash domain.
Identity order is raw parameter/tokenizer files → input/arithmetic profiles →
classifier. The program, weights, backend, setup, tokenizer and verifier-key
digests remain external references; their semantics and enrollment are separate.
There is no classifier self-reference or proof/signature in this hash graph.

Every field is required; nullable references use explicit null. All integers
exclude booleans, all arrays are immutable tuples after parsing, and digest fields
are raw 32-byte CBOR strings. Encoding and hashing revalidate unchecked copies.
The existing model-manifest codec now uses the same record serializer; its fixed
bytes, identity and JSON snapshot remain unchanged.

Classifier labels are two distinct IDs in benign/unsafe order. Scope is prompt.
Rules have no learned weights or tokenizer, and threshold 1. MLPs require weights
and no tokenizer; encoders require both. A tokenizer identity is a reference to
the qualified recipe/implementation, not something inferred from a filename.
`validate_profiles` checks both supplied profile identities, byte encoding for
rule/MLP versus token encoding for encoder, a one-element integer score with zero
fractional bits, and rule output bounds exactly [0, 1]. It then checks parameter
files and the arithmetic contracts below. It does not verify that program bytes
implement the declared classifier kind, that weights match training, or that
external tensor values satisfy their declarations. Those are execution,
qualification and enrollment obligations.

## Input recipes

Tokenizer files are sorted by exact path with no duplicates, at most 64.
Byte profiles have no tokenizer files or prefix/suffix tokens; padding ID is
0..255. Token profiles require at least one pinned tokenizer file. Prefix and
suffix each contain at most eight U64 tokens. Their combined length is strictly
less than chunk size (1..512), leaving positive content capacity. Overlap is
integer zero; padding is right-sided; maximum content units are 1..32768.
Tokenizer vocabulary bounds are checked against the actual admitted tokenizer
later, not guessed from a U64 identifier.

## Graph declarations and resource bounds

Graphs contain 1..4096 tensors and 1..4096 nodes. Tensor ranks are 1..4, dimensions
are positive U64 values, signed widths are 2..32 bits, and fractional bits are
0..30. Stored-integer minimum/maximum must be ordered, int32 and representable
at the declared width. A value with stored integer `q` and fractional bits `f`
represents `q / 2^f`.

Tensor names and node IDs are unique in their respective namespaces. Every
non-root tensor has one producer; tensors without a producer are external inputs
or parameters. Nodes are topologically ordered. Unknown references, cycles,
multiple producers and unconsumed declarations/nodes are rejected. The output
must be produced. Repeated uses of one input are allowed. Parameter references
may be shared only when path, size and hash agree.

Graph parsing checks declarations, arity and topology. Axes and permutations are
in hashed parameter files, so parsing alone cannot establish operation shapes.
`validate_parameters(files)` accepts an exact dictionary of referenced paths to
raw bytes, at most 64 MiB total. It checks each size/SHA-256, canonical CBOR and
parameter schema, then all shapes, scales and ranges. It performs no I/O or
tensor allocation. Dimension counts are metadata, not permission to allocate
those tensors; execution budgets and feasible graph sizes remain W18 obligations.

## Operator parameter files

Every file is a canonical CBOR map with required
`schema_id="hallmark/operator-parameters/1"`, `op` matching its node, and exactly
the extra fields below. These files have raw SHA-256 references, not a new typed
hash domain. `PARAMETERS` is the Pydantic adapter for this discriminated union.

| Operation | Inputs | Extra parameter fields | Shape and value contract |
|---|---|---|---|
| `gather` | table, indices | `axis:0..3` | Replace the table axis with index shape; indices have zero fractional bits and fit that axis. Copy table values/scale. |
| `affine` | x, weights, bias | None | Weights shape `[out,in]`, bias `[out]`, x's last dimension `in`; preserve x's leading dimensions. Bias scale equals the product scale. Compute the mathematical dot product plus bias. |
| `add` | a, b | None | Right-aligned broadcasting; dimensions match or one is 1. Add exact scaled values. |
| `multiply` | a, b | `mode:"elementwise" or "matmul"` | Elementwise broadcasting, or rank-at-least-two matrix multiplication with equal contracted dimensions and broadcast batch dimensions. No implicit vector promotion. |
| `reshape` | x | None | Preserve element count, row-major order and scale. Output tensor declares the new shape. |
| `transpose` | x | `permutation:List[0..3,1..4]` | Each input axis occurs exactly once. Output dimensions follow that permutation; preserve scale. |
| `masked-reduce` | x, mask | `axes:List[0..3,1..4]`, `keep_dims:bool`, `reduction:"sum" or "max"`, `empty_value:I32` | Sorted unique in-range axes; mask broadcasts to x, has zero fractional bits and values constrained to 0/1. Reduce selected values only. Empty sum is 0; empty max uses the explicit stored-integer value in x's scale. |
| `relu` | x | None | Preserve shape and replace negative values with zero. |
| `lookup` | table, indices | `offset:I32` | Table rank is one; stored index plus offset must fit. Output has index shape and table scale/range. This supports fixed-point table inputs without float execution. |

Reducing all axes without keeping dimensions produces shape `[1]`, the scalar
convention. Shapes resulting in rank greater than four are not admissible.
Masks with fractional scale, negative values or values above 1 are rejected.
The later executor/prover must enforce these ranges on actual values.

Gather, lookup, reshape and transpose preserve the declared value scale. Other
operators rescale the exact mathematical result to the output scale using nearest
ties-to-even, including negative halfways, once after the operation. No saturation,
wrapping, float arithmetic, implicit clipping or hidden rounding is permitted.
Affine/matmul sum full products before rescaling. A declared tensor width bounds
that tensor; it does not authorize a runtime to wrap a narrower accumulator.

Static range propagation is conservative: products use endpoint extrema, sums
use independent input bounds, reductions include possible empty masks, and
rescaling is monotone with exact rational rounding. Output declarations must
contain that full envelope and fit their signed width. Correlated inputs can
make the envelope wider than the reachable range; this validator rejects an
unjustified tighter declaration. Backend qualification must still prove actual
input/table constraints, intermediate arithmetic and mask behavior. A hash of a
table reference does not constrain a circuit's returned table values.

## Compatibility and evidence

JSON snapshots are projections with hex digest strings:
[classifier](../schemas/classifier-v1.json),
[input profile](../schemas/input-profile-v1.json),
[arithmetic](../schemas/arithmetic-v1.json), and
[operator parameters](../schemas/operator-parameters-v1.json).
They cannot express all cross-field rules. Untrusted artifacts use canonical
CBOR decoding plus full profile/parameter validation; direct JSON/Pydantic helpers
are local tooling and their validation errors are not safe diagnostics.

The [synthetic fixture](../../fixtures/wire/classifier-v1.json) is a byte-count,
two-unit hidden affine/ReLU/affine graph with conservative integer metadata. It
contains no learned weights. Fixed bytes and identities plus failure cases are
software conformance evidence, not independent verifier agreement.

The existing locked Pydantic uses `TypeForm` for
[TypeAdapter](https://docs.pydantic.dev/latest/api/type_adapter/). Enable the locked
mypy version's [TypeForm support](https://mypy-lang.blogspot.com/2025/11/)
to check the union without a type suppression. This changes static checking only.
