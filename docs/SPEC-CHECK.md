# Specification traceability

`make check-spec` validates the local documentation and the proposed v1 work map.
It also runs inside `make check` and against the extracted sdist in the package
gate. It requires no GitHub access or optional training packages.

The gate checks:

- Local Markdown file targets and fragments, including same-file links, repeated
  headings, explicit anchors and full/collapsed reference links. Fenced examples
  and HTML comments are excluded. External URLs are not fetched.
- Exactly 40 distinct v1 work IDs and 10 RFC trackers, unique repository issue
  URLs, nonempty scope/acceptance, known dependencies and an acyclic graph.
- Agreement between the requirement table, work map and tracker on titles,
  milestones, RFCs and dependencies. Merged tracker rows must link their PR.
- The RFC section template, metadata and open questions with an owner and valid
  resolution checkpoint date. A checkpoint is neither a schedule nor approval.
- Explicit work ownership for every specification section, every RFC design
  section and every named invariant in [coverage.json](roadmap/coverage.json).
  New or removed headings, orphan entries and unknown owners fail.
- The three historical source-text hashes. Existing conformance checks separately
  protect the frozen corpus and legacy research fixtures.

The repository uses ATX (`#`) headings, explicit HTML anchors and inline or
full/collapsed reference links. This is a checker for those forms, not a complete
Markdown renderer. Extend the checker and its fixtures before introducing other
syntax. Local automation checks structural coverage; reviewers must still check
that each mapped implementation satisfies the actual requirement. A green gate
cannot establish scientific, hardware or cryptographic validity.

## Live issue audit

```sh
uv run --locked python scripts/check_spec.py --live --output /tmp/hallmark-spec-audit-new.json
```

Authenticated `gh` reads the repository's paginated issues endpoint with a
45-second timeout. It makes no writes. The audit checks all mapped live issues,
including closed ones, for identity, title, scope, acceptance criteria, exact
specification labels, milestone, dependency edges and RFC tracker children.
Other workflow labels are allowed. Pull requests returned by that endpoint are
excluded. The result records the observed issue states, update times, metadata,
body hashes, response hash and local specification/script hashes.

The output must be new. Failures retain a failed result; missing API access or
metadata drift cannot become an offline pass. A saved audit is a dated observation,
not a current GitHub query. Normal CI explicitly reports `live: "not-checked"`;
run the live audit again when issue mappings change or before a release decision.
Tracker status prose must be refreshed from actual delivery receipts, while the
historical bootstrap packet and old evidence stay immutable.

## Changing the contract

Keep [requirements](spec/11-requirements.md), [work items](roadmap/work-items.json),
[coverage](roadmap/coverage.json), [tracker](roadmap/IMPLEMENTATION.md) and the live
issue consistent in the same review. Every section and invariant needs concrete
work ownership; do not add a catch-all exemption to make the gate pass. New v1
work IDs or a changed RFC template require an explicit contract change and tests.
A claim about completion additionally needs the issue's specified commands,
negative cases and any required real-resource or independent evidence.
