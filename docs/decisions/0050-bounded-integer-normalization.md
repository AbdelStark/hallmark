# 0050 — Bounded integer layer normalization component

Date: 2026-10-21. W18 / issue #19. Synthetic engineering experiment only.

The existing attention block omits layer normalization. Add a separate relation
without changing that block, its fixture, historical setups or proof results.
This component is preparation for an admitted complete encoder, not its admission
or qualification. No floating pretrained model equivalence is claimed.

The two integer input features range from -8 to 8. Round their mean to nearest,
ties to even. Compute squared differences from that rounded mean, then round
their mean by the same rule. Variance is in 0..64. A complete finite table maps
it to `round(256 / sqrt(variance + 1))`, with nearest ties to even. The epsilon
is exactly one in the declared integer scale. Table construction compares integer
squares at half-integer boundaries; it does not depend on floating precision.

Multiply centered features by that inverse, then apply gamma `[1, -2]` and beta
`[1, -1]`. Outputs retain eight fractional bits, so beta contributes `[256, -256]`.
All eleven intermediate values are constrained signed int32. The four public
fields are the two inputs and two outputs, each offset by `2^31`. Explicit finite
selection constrains both the input domain and the inverse table. The existing
assignment parser rejects field aliases and noncanonical integers.

Freeze all 289 input pairs, including constant rows, extrema and mean/variance
rounding boundaries, before proof execution. Check every intermediate against a
separate high-precision Decimal oracle. A smallest real-proof Go fixture precedes
the bounded Mac campaign, which retains a proof and fresh verification for every
pair and rejects intermediate/public/range/proof/key mutations. Pin source,
fixture, binary and controller outside the run; preserve incomplete runs.

Use the owner's standing approval for one foreground Mac campaign with four
threads, 900 seconds, 2 GiB measured worker RSS and 2 GiB output; preparation has
a separate 180-second bound. There is no cloud job, private input, model download
or new dependency. Keep the existing reviewed environment and frozen older
circuit fingerprints. This does not reuse the completed maximum-input experiment
as evidence for the new relation. Setup remains research-only and the verifier
is shared gnark code; `qualified_backend` remains false.
