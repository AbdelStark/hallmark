# 0068: Select the output head's final normalization

2026-10-23. Correct the extraction plan under the existing complete-response
acceptance gate. The quantized model, arithmetic, Rust source and verifier remain
unchanged.

All 23 non-delayed proofs verified individually, and the prompt/generated IDs
matched. The complete grid rejected the last residual link: the head committed
layer 21's input instead of its output. Its extraction command had combined
`--head` and `--residual-stream`. The dump contained both families, and the pinned
Rust loader chooses the ordinary residual family before considering the final
norm. The head's boundary roots exactly repeated layer 21's roots. Matching
`xin_head.u16` bytes alone did not show which family the proof consumed.

Extract the separate head with `--head` and without `--residual-stream`, into a
fresh directory. Require an empty ordinary `residual_stream` manifest entry and
`head.final_norm: true`. Require every retained numeric array to equal the prior
head extraction and `xin_head.u16` to equal the last layer's output. Do not edit
old manifests or relabel the failed run as successful.

The 22 transformer proofs already verified against roots enrolled before proving;
their exact bytes, roots and statements remain frozen. Reuse those unchanged
segments in a new campaign, enroll a fresh head model/shape root before proving,
and generate a new head proof. Require `params.residual_stream.head_norm: true`
in the caller's head-statement check. Require all 23 proofs, all 22 residual links,
all prompt/generated positions and the final output token to pass. No link is
removed or treated as optional.

The final gate remains a fresh verifier worker with no weights or witness traces,
using the caller's enrolled roots and exact statement parameter digests, followed
by rejection of changed inputs, output, model, calibration, coverage and proof
bytes. This is one disclosed engineering prompt; it does not qualify general
language-model quality, hiding or independent cryptographic security.
