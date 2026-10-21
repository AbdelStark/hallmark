# Proof backend source review

## 2026-10-21 commitment-scaling extension

The separate [decision 0035](../../../docs/decisions/0035-input-commitment-scaling.md)
uses the already pinned gnark module's indexed log-derivative lookup. Source
inspection followed `Lookup` through its blueprint outputs and deferred
`logderivarg.Build`: queries contain both index and value, and variable table
entries, query tuples and multiplicity hints enter the commitment before the
challenge. The relation constrains canonical byte ranges, every prefix increment,
all active byte reads and zero padding. Lookup hints are not accepted as an oracle.
The exact inspected source hashes are retained with the new run. This adds a
gadget to the circuit review surface; it is not an independent security review,
soundness proof, hiding assessment or backend admission. Historical source reviews
and circuit results below keep their original scope.

## Initial candidate review (2026-10-20)

Observed 2026-10-20 for W18 / issue #19. This is source and dependency
preparation, not backend qualification, legal advice or an independent security
review. The initial review inspected public metadata, source text and audit PDFs;
it preceded the separately recorded installation and rule probes. No model assets
were fetched.

**Recommendation:** prepare a bounded local CPU probe using gnark v0.16.4,
Groth16 and BLS12-381 after the selected build dependencies have been reviewed.
Keep any locally generated setup explicitly research-only. Hold EZKL until an
applicable licence grant is established. Neither candidate has evidence of
Hallmark's full graph, input binding or hiding requirements passing.

## EZKL: no suitable licensed, audited release established

The inspected current source is v23.0.5 at
[`534ff3e6c13d4c2c1aca2358910d62dac466d3cc`](https://github.com/zkonduit/ezkl/tree/534ff3e6c13d4c2c1aca2358910d62dac466d3cc).
Its root has no `LICENSE`; its
[README](https://github.com/zkonduit/ezkl/blob/534ff3e6c13d4c2c1aca2358910d62dac466d3cc/README.md)
contains contribution terms and a warranty disclaimer, not an identified
downstream licence grant. Public source visibility and package availability do
not resolve this admission requirement.

The earlier
[`22689cfdb6c9e571f5a208d164ddd18c638d24f8` tree](https://github.com/zkonduit/ezkl/tree/22689cfdb6c9e571f5a208d164ddd18c638d24f8)
does contain an
[Apache-2.0 licence](https://github.com/zkonduit/ezkl/blob/22689cfdb6c9e571f5a208d164ddd18c638d24f8/LICENSE).
It was removed by
[`0da47d7fb12d8f09ceb9ea4c1d65ee890572c124`](https://github.com/zkonduit/ezkl/commit/0da47d7fb12d8f09ceb9ea4c1d65ee890572c124)
on 2024-01-07. The earlier tree's
[README](https://github.com/zkonduit/ezkl/blob/22689cfdb6c9e571f5a208d164ddd18c638d24f8/README.md)
describes unaudited beta software. Its
[Cargo.lock](https://github.com/zkonduit/ezkl/blob/22689cfdb6c9e571f5a208d164ddd18c638d24f8/Cargo.lock)
does pin Git dependencies, including Halo2
`57b9123835aa7d8482f4182ede3e8f4b0aea5c0a`, but those dependencies and historical
security status have not been qualified here.

The current README identifies v21.0.0 as audited. That release resolves to
[`c48ff1a4e974ebeaf6bb219fe6ef65d309ddda0d`](https://github.com/zkonduit/ezkl/tree/c48ff1a4e974ebeaf6bb219fe6ef65d309ddda0d),
whose root also has no licence file. A Mac universal2 wheel is listed by
[PyPI v21.0.0 metadata](https://pypi.org/pypi/ezkl/21.0.0/json):

```text
ezkl-21.0.0-cp37-abi3-macosx_10_12_x86_64.macosx_11_0_arm64.macosx_10_12_universal2.whl
bytes: 22925718
sha256: b2e00e286a8c275666091b7dfc3d978323e2d01892ec4200576795bc32e6e817
```

This is metadata evidence, not downloaded-byte verification or a successful
Mac execution. The earliest retained file in the inspected
[PyPI release inventory](https://pypi.org/pypi/ezkl/json) is v7.1.4, uploaded
2024-01-09, after the licence removal. No earlier release combining explicit
licensing, audit coverage and an authenticated usable Mac artifact was
established by this review; this is not a claim that none could exist elsewhere.

The [Trail of Bits report, pinned copy](https://github.com/trailofbits/publications/blob/89940dfbec07ad03b0989e67d78e84250765366b/reviews/2025-03-zkonduit-ezkl-securityreview.pdf)
names initial EZKL target `bdcba5ca61ada24f17dd754e6e3c71d0a1ef72d9`,
not either release commit above. Its March 2025 fix review reports 29 resolved,
three partially resolved and two unresolved findings out of 34; some reviewed
fixes were still in private repositories. Relevant findings include unsound
min/max arguments, missing ranges, non-hiding low-entropy commitments and
quantization-triggered backdoors. The report does not establish blanket
coverage for the older licensed tree, v23.0.5, or Hallmark's relation.

## gnark: concrete candidate for a research probe

| Item | Observed pin or constraint |
| --- | --- |
| Source | v0.16.4, `e974abb44722dd201a7f1949baeabca0fef5866e` |
| Root licence | Apache-2.0 |
| Arithmetic dependency | `github.com/consensys/gnark-crypto v0.21.1-0.20260913224755-1409fe592052`, commit `1409fe59205234d1fc62769923623ecba82e1ef7`, Apache-2.0 |
| Toolchain | `go 1.26.8` in `go.mod`; README's `1.25.7` requirement is stale |
| Mac route | Source build; the release has no attached binary assets |
| Selected proof path | CPU Groth16 over BLS12-381; no GPU, recursion or optional commitment gadget assumed |

Sources: [gnark source and licence](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/LICENSE),
[go.mod](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/go.mod),
[README](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/README.md),
[release metadata](https://api.github.com/repos/Consensys/gnark/releases/tags/v0.16.4),
[gnark-crypto licence](https://github.com/Consensys/gnark-crypto/blob/1409fe59205234d1fc62769923623ecba82e1ef7/LICENSE).

The release fixes a high-severity emulated-curve soundness problem and other
correctness issues, and warns that affected circuits need recompilation and
new setup. It should not be replaced with an older version merely to match an
installed toolchain. Those fixes do not certify the selected path.
[Release notes](https://github.com/Consensys/gnark/releases/tag/v0.16.4).

The [pinned crypto README](https://github.com/Consensys/gnark-crypto/blob/1409fe59205234d1fc62769923623ecba82e1ef7/README.md)
documents arm64 optimizations and macOS testing. The official
[Go download metadata](https://go.dev/dl/?mode=json&include=all) lists
`go1.26.8.darwin-arm64.tar.gz`, 64,626,620 bytes, SHA-256
`a012b25b571bd0138a03dcd25375ceba866fe5ca822f426d2c66a4de56fd3f4b`.
This supports a native Mac build route; no build or performance result is
inferred by this source review.

The exact [go.sum](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/go.sum)
contains the arithmetic dependency module checksum
`h1:iw/l5FVYu5PctRwOyooaOjqVWKomojbK+L9u84B9iXM=`.
The selected build's complete module closure, licences, notices and checksums
still require an inventory; reviewing the two root licences does not admit all
transitive dependencies. Avoid `@latest`, automatic toolchain changes and
unreviewed build generators.

### Setup, hiding and verifier constraints

The pinned
[Groth16 API](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/backend/groth16/groth16.go)
documents circuit-specific random setup and warns that leaked setup randomness
can break the protocol. The
[BLS12-381 setup implementation](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/backend/groth16/bls12-381/setup.go)
samples secret setup scalars. A fresh local setup demonstrates mechanics only:
it does not establish independent ceremony provenance or secret destruction.
`DummySetup` is explicitly unsuitable as proof evidence.

The [prover](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/backend/groth16/bls12-381/prove.go)
samples fresh `r,s`; its
[field random sampler](https://github.com/Consensys/gnark-crypto/blob/1409fe59205234d1fc62769923623ecba82e1ef7/ecc/bls12-381/fr/element.go)
uses Go's cryptographic random source. This supports investigation of the
randomized proof path; it does not prove end-to-end witness privacy. Public
witness fields, serialization, logs and process isolation remain Hallmark
obligations.

The [curve source](https://github.com/Consensys/gnark-crypto/blob/1409fe59205234d1fc62769923623ecba82e1ef7/ecc/bls12-381/bls12-381.go)
states an estimated **126-bit** security level, not 128 bits, and disclaims
constant-time and side-channel guarantees. Record that estimate as upstream's
claim rather than a newly validated security bound. Scalar modulus:

```text
52435875175126190479447740508185965837690552500527637822603658699938581184513
```

The [native verifier](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/backend/groth16/bls12-381/verify.go)
checks public witness length, commitment counts, proof subgroup membership and
pairings. Hallmark must additionally enforce byte/count/signed ranges, reject
field aliases, bind every public input and use independently enrolled keys.
A fresh invocation of this library is not an independently implemented verifier.

### Audit coverage is narrower than the candidate

The [September 2024 Least Authority report](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/audits/2024-09%20-%20Least%20Authority%20-%20arithm%20and%20GKR.pdf)
reviewed selected constraint/GKR/polynomial code and crypto paths for BN254,
BLS12-377 and BW6-761. Its verification commits were
`3a0fa0f316437854d56bf10a1e75811df9697f46` and
`703a260c2f991d01e245adf53d20f76af4210c5f`.
That scope does not establish review of current native BLS12-381 Groth16.
The [May 2024 zkSecurity report](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/audits/2024-05%20-%20zksecurity%20-%20gnark%20std.pdf)
covers selected standard-library arithmetic, range, multiplexing and in-circuit
verification gadgets, not the whole current backend or Hallmark circuit.

## Reproducibility observations

SHA-256 values below were computed from fetched source/document bytes, not
inferred from Git object identifiers. The initial source review downloaded no
executable artifact; the subsequent pinned toolchain/build is separately recorded.

| Pinned file | Bytes | SHA-256 |
| --- | ---: | --- |
| gnark `LICENSE` | 11357 | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| gnark `go.mod` | 1667 | `d75a90223e4bb126880eef059ac02b7d9ab52a7c7b92622dcc535f71cccda5b4` |
| gnark `go.sum` | 67140 | `5ffa49a8e0c634dbc17da1a100fc234365785078a6470dd713e944e74010055e` |
| gnark-crypto `LICENSE` | 11357 | `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4` |
| gnark-crypto `go.mod` | 966 | `fc437bc65fcedfb53c21842ccfacd57dbead818a5c73f241cdfa64c1f9e83d97` |
| gnark-crypto `go.sum` | 63914 | `fdc17f4f1462cbfb3d1ed87fbafce9865951147f308f21496d6130e53bc05f00` |
| EZKL audit PDF | 2332461 | `acf86ee1f12418089d3f896f0ef47eee4069ca362da4126e9a1ee0dad13c8bb9` |
| gnark arithmetic/GKR audit PDF | 309285 | `d04febacbd9dc05dd425b173fdd658141dab82bed4f87e0bcc207ae60f6fdc6a` |
| gnark std audit PDF | 3486834 | `2e633851dbe0fd8613612fe269e16dbbc4bbe1a0e838222dfbd05c3e1779caf6` |

## Next engineering action

Finish the selected dependency/toolchain admission, then freeze a tiny
complete-input byte/rule circuit with exact Hallmark public inputs and run one
local CPU setup/prove/verify experiment under the existing budget. Preserve raw
costs and every failure. Test changed witness, every public binding, wrong key,
wrong setup, integer aliases and missing final bytes in a fresh verifier
process. Keep locally generated setup and any successful tiny circuit marked
research-only; W18's full-graph, independent enrollment, security-review and
measured-budget gates remain open until their own evidence exists.

## Additional rule-probe surface

The tiny rule experiment also imports the pinned
[SHA-256 gadget](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/std/hash/sha2/sha2.go),
[byte implementation](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/std/math/uints/bytes.go)
and [integer operations](https://github.com/Consensys/gnark/blob/e974abb44722dd201a7f1949baeabca0fef5866e/std/math/uints/uint8.go).
This expands the installation probe's simple R1CS path to lookup/range-check
gadgets and their commitment machinery. The byte implementation uses
log-derivative precomputation; `ValueOf`/`Value` enforce byte ranges. The SHA
variable-length path constrains padding and length, using a bounded comparator
whose assumptions require separately bounded operands. The experiment constrains
the input count to 0..8 and its encoded preimage length to 92..108 bytes.

Upstream's integer-package header explicitly cautions that soundness is not
ensured. The old audits above do not remove that warning or establish coverage
of this exact version and composition. This is sufficient source admission for
a harmless local experiment, not security qualification. Do not infer hiding,
production soundness, or permission to enroll the backend from a passing probe.
