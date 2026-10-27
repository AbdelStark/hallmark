# 0081 — Publish the documentation site on GitHub Pages

Date: 2026-10-27. Status: owner-requested public documentation deployment.

The owner requested `for-the-badge` header badges, badges linking both published
Hugging Face models, and a research/educational documentation site deployed on
GitHub Pages. Publish the existing public documentation/evidence plus the new
educational and presentation sources at `https://abdelstark.github.io/hallmark/`.
Keep the repository public. This authorizes Pages setup and main-branch
documentation deployment; it adds no research scheduler or paid inference job.

Use Zensical 0.0.73 in a separately locked `website/` project. The inference
`uv.lock` is part of the native verifier identity and must remain byte-identical.
Do not modify enrolled verifier/runtime/evaluator sources or numeric evidence.
The original signed enrollment therefore needs no identity migration.

Build from a tracked-file allowlist: canonical Markdown, public evidence JSON,
documentation images and explicit site assets. Reject unsafe staging inputs;
never copy ignored runs, credentials, private notes, untracked research or model
checkpoints. Preserve canonical source files, rewriting only staged link targets
and heading-separator compatibility for the generated site.

Reuse existing research claims with their measurement boundaries and evidence
links. Educational formulas are explanations, not a protocol change. Distinguish
completed fixed-case integrity from hiding, hardware, general-model or backend
qualification. Preserve historical results and failures; the current GPU result
may be placed before its historical fallback section without altering numbers.

Pin dependency/action versions. Self-host reviewed font/math assets with licences
and integrity hashes. No analytics, external search account, custom domain or
ongoing research compute is needed. PRs build/test; only main can deploy through
the standard Pages artifact/OIDC workflow. Verify local links, privacy boundary,
browser behavior, responsive layout and the final hosted artifact before closure.
