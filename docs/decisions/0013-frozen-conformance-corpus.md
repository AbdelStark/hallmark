# 0013: Frozen component conformance and unavailable evidence

Date: 2026-10-20. Status: implemented software contract, pending owner protocol
adoption. Implements W33 / #34. Prior research results are not reused as v1 evidence.

## Scope and result semantics

The frozen [corpus](../../tests/vectors/v1/corpus.json) has 188 cases:
156 executable component checks and 32 unavailable real-proof, real-hardware or
hybrid obligations. Every original PRD cheat has a negative hybrid obligation,
even where an executable component mutation also exists. The requirement map
includes all 19 error codes, parser bounds and types, immutable identities,
arithmetic boundaries, retirement/rotation and B1/B2 claims.

`Outcome.accepted` means that the **named component check** succeeded. Every
executable case reports both evidence claims `not-accepted`. Decoding a proof
declaration, receipt or bundle supplies no cryptographic or hardware acceptance.
The legacy linear runtime supplies exact score/verdict vectors; arithmetic-profile
checks validate static parameters. Neither executes a v1 classifier graph.
Full graph rounding/masks and proof boundaries remain unavailable.

Unavailable cases contain no fabricated evidence inputs and produce no observed
outcome. Their expected claim states and reason codes are normative obligations
for future implementations, not measured results. Their mutation names describe
the intended one-field change from a future genuine parent. They require a new
corpus revision with actual evidence before they can execute.

## Frozen identity and provenance

`Corpus.identity()` is `H("corpus", complete typed manifest)`. The manifest sorts
unique case and requirement IDs and pins every source, trust, request and input
file by raw SHA-256 and byte size. The reviewed pin is
[corpus.id](../../tests/vectors/v1/corpus.id); external callers must retain their
own approved pin. A pin supplied by an untrusted corpus author is not authority.

Each case fixes its check, input references, fixture trust identity, expected
request identity, clock, exact outcome, requirement, mutation parent and missing
dependencies. Trust uses `TrustPolicy.identity()`. `expected_request` is raw
SHA-256 of the complete canonical `RequestExpectation` CBOR; it is not a transcript
context or a new hash domain. The fixture trust/request records are independently
supplied to the component and never extracted from the evidence under test.

The three source documents are copied byte-for-byte under `sources/` with stable
locators. They are evidence snapshots, not a second editable specification.
Inputs derive from the repository's existing public harmless wire fixtures,
literal restricted RFC 8949 encodings and deterministic synthetic mutations.
No real transcript, checkpoint, operational key, model or hardware evidence is
included. Existing repository licence terms still apply; corpus publication does
not grant a new licence or authorize future private evidence publication.

Expected hash values use literal encodings and separately written hashlib
preimages, and integer outcomes are explicit constants. The builder never calls
the runner to manufacture expected outcomes. This separation helps catch mistakes
but is not independent verification: both remain repository-maintained code,
and artifact fixtures share primary contract provenance.

## Runner and failure boundary

`hallmark.conformance.run_corpus` checks the external corpus pin before file access,
then verifies source/context/input hashes. File reads reject traversal, symlinks,
hardlinks, nonregular files, size mismatches and detected concurrent changes.
The manifest is bounded to 8 MiB, 1,024 cases and 64 MiB of unique referenced bytes.
Check names select a finite adapter list, never executable paths or shell commands.
Expected outcomes and requirements are not inputs to adapters.

Complete observed outcomes are compared, including code, claim statuses, digests
and integer vectors. Unexpected implementation exceptions abort the run instead
of matching a planned `INTERNAL_ERROR` case. Diagnostic vectors separately check
the established exception-sanitization boundary.

The report records corpus and primary implementation identities, each result,
counts and unavailable IDs. The primary identity hashes loaded package source
files plus the supplied `pyproject.toml` and `uv.lock`; it is not an attestation
that the environment obeyed them. The evidence ledger separately records installed
versions. `independent` is explicitly null; W34 must introduce a separately
versioned comparison report and reviewed implementation provenance.

The default script scope is all required evidence: mismatch exits 1, malformed
input exits 2, and required unavailable evidence exits 3. Unexpected failures use
the established sanitized error mapping. The explicit `--software-only` scope
exits 0 when at least one component executes and all component outcomes match,
while still reporting all 32 unavailable cases and `all_required_executed:false`.
An all-unavailable run cannot pass. This is not a full-conformance acceptance.

`--self-test` changes one expected integer result under a new candidate identity
and requires exactly one mismatch/exit 1. It also checks that unavailable required
evidence forces exit 3. It never modifies frozen inputs. `make check-conformance`
selects this software scope and self-test; `make check` includes it. Installed-wheel
validation checks both software and default scopes.

These bounds are for a local, caller-approved fixture runner, not hostile proof
worker isolation, wall-clock/RSS enforcement or a full verifier.

## Migration and reproduction

Build only into a fresh directory. To reproduce the frozen source snapshot:

```sh
uv run --locked python scripts/build_conformance.py --output /tmp/hallmark-corpus-fresh --sources tests/vectors/v1/sources
diff -r tests/vectors/v1 /tmp/hallmark-corpus-fresh
```

The builder refuses an existing destination. Changing any case, expected result,
source, clock or context requires a new corpus identity and reviewed decision;
preserve previous corpora and reports. New default sources come from the current
repository; reproducing an old corpus uses its frozen source directory.
Schema/meaning changes require a new schema ID. Missing genuine evidence cannot
be supplied by relabeling a software fixture or rewriting a historical report.

The preserved failed candidate expected the inclusive 32,768-byte profile limit
to reject. The correct component accepted it. A new candidate added explicit
exact-limit, max-plus-one and complete-tail checks. See the
[numeric evidence](../../research/evidence/w33-conformance-2026-10-20.json).
Finite corpus agreement, even after future independent review, will not prove
policy quality, completeness, provenance or safety.
