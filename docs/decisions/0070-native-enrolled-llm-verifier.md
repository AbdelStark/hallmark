# 0070: Verify the fixed LLM case with compiled shape enrollment

2026-10-23. Research verifier variant for the pinned TinyLlama response. The
Linux verifier and `make e2e-llm` continue to derive shape roots at runtime.
Backend qualification and operational adoption remain open under issue #19.

## Problem and failed approaches

SASH's CPU verifier rebuilds each preprocessed shape tree through the shared
trace generator. That generator retains CUDA code in a native Mac link.
A verifier-only entrypoint and two macOS linker guards failed. A second candidate
also forced device modes off at compile time; GPU fields and destructors still
retained ten unresolved CUDA symbols. Both failed builds are preserved.

## Change and trust boundary

Compile the 23 `(shape_key, pre_root)` pairs from the caller-owned
`response-case.json` into a verifier-only executable. The shape key hashes the
exact parameters and calibration using SASH's existing encoding. Every lookup
must match an enrolled key, and its root must equal the statement's root.
Unknown shapes fail before constraint construction or proof processing.
Proof-supplied roots cannot extend this table.

The enrolled roots were derived and checked by the original Linux implementation
in the recorded full-response run. This variant treats that preprocessing output
as verification parameters. It does **not** repeat shape-tree construction on the
Mac or authenticate enrollment. A different case needs separately derived and
reviewed parameters and a newly built verifier. Do not generate this table from
untrusted proof statements.

STARK and GKR checks, constraints, Fiat–Shamir transcripts, security parameters,
model-root checks and residual/token links retain their upstream implementation.
The caller still checks exact tokens, parameters, coverage and the final head.
The binary truthfully reports `dirty: true` and
`shape_root_source: "compiled-enrollment"`. Existing `shape_root_ok` fields mean a
match to the compiled enrollment in this variant, not fresh derivation.

The change introduces no CUDA substitutes, GPU calls or general-purpose VM.
It changes preprocessing authority and receives a separate experiment identity;
old Linux timings are not measurements of this verifier. Independent review of
this specialization remains required before operational qualification or reuse of
its research results as security-admission evidence.

## Command and acceptance

`make verify-llm LLM_RUN=runs/llm-e2e-...` builds the patched, pinned source and
checks retained proofs without model weights, witnesses, an HF token or paid jobs.
The command takes expectations from the repository's public case, not from an
`expected.json` file beside the submitted proofs. It retains each attempt in a
new directory and freezes source/input hashes before verification.

Builds use four threads and a 30-minute limit. The full verification suite has a
10-minute limit. A foreground monitor stops the process group above 4 GiB sampled
RSS; sampling is not an OS memory quota. Verification runs in a Mac sandbox with
network access denied and filesystem access limited to its proof-only directory,
Python runtime and system libraries. Rust may fetch its locked dependencies while
building. No model files are downloaded.

The accepted variant must verify the same 23 proofs twice, reject the original
14 mutations and reject changed parameters/calibration directly in Rust with the
caller guard deliberately bypassed for those two negative cases. The original
proof files must remain unchanged. The first sandbox attempt failed before any
cryptographic check because its Python worker could not fork; the corrected
profile permits child creation within the same restrictions. The first packaged
run then exposed an upstream panic when a deliberately unknown rounding shape
reached constraint code before the enrollment check. The corrected native
variant checks enrollment first and requires an explicit rejection report.

[Numeric evidence](../../research/evidence/native-llm-verification-2026-10-23.json)
records exact builds, commands, failures, timings and the validation scope. These
are fixed-case integrity proofs, without a hiding, independent-audit or hardware
provenance claim.
