# Optional local proof probes

This directory contains bounded real-proof experiments for W18, not a qualified
Hallmark backend. The Python runtime has no new dependency or acceptance path.
See [decision 0022](../../../docs/decisions/0022-local-proof-probes.md) and the
[MLP extension](../../../docs/decisions/0024-bounded-mlp-proof-probe.md) for the
exact relations, resource boundary, failed candidates and remaining gates.

`main.go` implements a cubic installation relation. `rule.go` implements the
fixed marker in `rule-fixture.json`; `mlp.go` implements the frozen integer
MLP in `mlp-fixture.json`. `input.go` binds the complete salted input hash and
100 public fields for both; `graph.go` shares their artifact and process interface.
Classifier enrollment tags and weights are synthetic. A successful result
always contains `qualified_backend: false`.

`block.go` is a separate integer attention/feed-forward relation with five
public fields and 89 private intermediate values. Its fixture exhausts all
64 token/mask inputs. It exercises finite lookup, masking, signed rounding,
residuals and pooling; it does not implement a tokenizer, layer normalization,
the complete input hash or a complete encoder. See
[decision 0025](../../../docs/decisions/0025-integer-attention-block-probe.md).

`normalization.go` is a separate two-feature integer layer normalization relation.
Its four public fields bind the inputs and outputs, and all eleven intermediate
values are constrained. The fixture covers all 289 inputs in `[-8,8]^2` with
explicit rounded mean/variance, epsilon, inverse table and affine parameters.
This is a bounded integer approximation, not floating model equivalence or a
complete encoder. See [decision 0050](../../../docs/decisions/0050-bounded-integer-normalization.md).
The frozen component campaign uses the same network-denied Mac worker:

```text
uv run --locked python scripts/check_gnark_normalization.py \
  --binary BINARY --expected-binary BUILD_SHA256 \
  --fixture research/probes/gnark/normalization-fixture.json \
  --expected-fixture FROZEN_FIXTURE_SHA256 --output FRESH_DIRECTORY
```

The command retains 289 proofs and fresh verifier executions, plus public,
intermediate, range, alias, canonical-encoding, proof and setup-key rejections.
It uses one 900-second budget, four threads, 2 GiB worker RSS and 2 GiB output.
The older block and staged qualification relations remain unchanged. Future HF
source inventories include the normalization source required by the shared
dispatcher; this does not retroactively change any cloud experiment.

`input_scale.go` separately measures the salted complete-byte commitment with
indexed CBOR packing. It uses 33 public fields and a synthetic fixed profile,
with candidate capacities 8, 32, 256 and 32,768 bytes. It leaves the original
rule/MLP/block relations unchanged. Its small proofs, boundary proving attempts and
maximum compilation attempt are different kinds of evidence; none qualifies
the full encoder. See [decision 0035](../../../docs/decisions/0035-input-commitment-scaling.md).
The current candidate replaces per-position coverage comparisons with Boolean
prefix masks whose exact sums bind both input count and encoded length. The private
assignment has `78 + 7 * capacity` fields; the public assignment remains 33.
New candidate identities and setups are mandatory. See
[decision 0037](../../../docs/decisions/0037-prefix-coverage-commitments.md).

The [initial evidence](../../evidence/w18-proof-probes-2026-10-20.json) retains
the original failed/corrected rule candidate. The
[MLP and regression evidence](../../evidence/w18-backend-contract-and-mlp-2026-10-20.json)
records the changed circuit identities and new setups. No historical proof is
reassigned to a changed source graph.
The [block evidence](../../evidence/w18-integer-attention-block-2026-10-20.json)
records the exhaustive block run and reproduction of those earlier circuit
identities under the shared worker.

Before building, review the
[source](../../proposals/backend-v1/candidate-review.md) and
[dependency pins](../../evidence/w18-backend-dependencies-2026-10-20.json).
Use the admitted isolated Go 1.26.8 toolchain, frozen module cache and a fresh
output directory. The recorded build uses:

```text
go build -trimpath -buildvcs=false -mod=readonly -o FRESH_DIRECTORY/probe .
```

The build environment fixes `GOTOOLCHAIN=local`, `CGO_ENABLED=0`,
`GOTELEMETRY=off`, `GOFLAGS=-p=2`, `GOMAXPROCS=2` and `GOMEMLIMIT=1GiB`,
with isolated `GOROOT`, `GOPATH`, `GOMODCACHE`, `GOCACHE` and temporary storage.
Build/module acquisition is separate from the network-denied proof worker.
Do not use `@latest`, an unreviewed replacement dependency or automatic toolchain
downloads. This documentation does not authorize a new host or budget.

The optional [Boolean-wire cache patch](patches/README.md) uses a separately
inventoried module copy and explicit modfile replacement. The default dependency
is unchanged. Compare full serialized circuit fingerprints and run fresh actual
proof checks before using that candidate; its small-fixture equivalence does not
qualify arbitrary circuits or a complete encoder.

From the repository root, under a recorded approved local protocol:

```text
uv run --locked python scripts/check_gnark_probe.py \
  --binary BINARY --expected-binary BUILD_SHA256 --output FRESH_DIRECTORY

uv run --locked python scripts/check_gnark_rule_probe.py \
  --binary BINARY --expected-binary BUILD_SHA256 \
  --fixture research/probes/gnark/rule-fixture.json \
  --expected-fixture FROZEN_FIXTURE_SHA256 --output FRESH_DIRECTORY

uv run --locked python scripts/check_gnark_rule_probe.py \
  --binary BINARY --expected-binary BUILD_SHA256 \
  --fixture research/probes/gnark/mlp-fixture.json \
  --expected-fixture FROZEN_FIXTURE_SHA256 --output ANOTHER_FRESH_DIRECTORY

uv run --locked python scripts/check_gnark_block_probe.py \
  --binary BINARY --expected-binary BUILD_SHA256 \
  --fixture research/probes/gnark/block-fixture.json \
  --expected-fixture FROZEN_FIXTURE_SHA256 --output BLOCK_FRESH_DIRECTORY
```

Take pins from the reviewed build/protocol record, independently of worker
outputs. Fresh directories are mandatory; failures are retained. The rule
runner checks native vectors, every public field, byte/count/Boolean aliases,
padding, changed private input, missing final input, proof bytes and a second
setup's key. Read the raw result and failure records; an exit code alone is
insufficient evidence. The same controller recognizes the pinned MLP fixture
and adds a real invalid-prover attempt for each of its 22 private layer values.
The MLP is one fixed three-unit graph with signed ties-to-even rescaling,
ReLU and complete chunk aggregation; it is not an arbitrary graph importer.
Run these experiments sequentially under the recorded budget.
The block controller proves every input/mask combination, checks every recorded
intermediate, and rejects field aliases, malformed assignments, changed proofs
and the wrong setup key. It uses explicit finite selection for its small tables.

The separate commitment-scaling run uses the same isolated worker, with a
420-second total limit, 120-second setup/batch caps and a 90-second maximum
compilation cap:

```text
uv run --locked python scripts/check_gnark_input_scale.py \
  --binary BINARY --expected-binary BUILD_SHA256 --output FRESH_DIRECTORY
```

This command exits 3 and reports incomplete even when its component checks pass.
Read `result.json`, batch outcome files and each `cost.json` to distinguish actual
proofs, rejected witnesses, compilation and resource failures. No source edit or retry belongs to
the same frozen experiment. Independently retain the source/build/binary pins
and approved remaining budget before execution.

`make check` runs offline boundary and fixture-reproduction tests. It does not
download Go, build the backend or prove these relations. OS sandbox tests skip
on hosts other than macOS arm64; they do not establish Linux isolation. Actual
proof execution is an explicit, separately budgeted command above.

The generated fixtures reproduce with:

```text
uv run --locked python scripts/build_gnark_rule_fixture.py
uv run --locked python scripts/build_gnark_mlp_fixture.py
uv run --locked python scripts/build_gnark_block_fixture.py
```

Do not commit toolchains, module caches, binaries, proving keys or local run
directories. Public synthetic proof/key examples and numeric costs may be
retained as explicit research evidence; they are not operational trust anchors.

The artifact reader streams within a 256 MiB default cap, rejects unsafe
file types/links and requires exact decoder consumption. Only the 32,768-unit
commitment profile allows up to 24 GiB per artifact under an explicit parent budget. Commitment-scaling
setup files move through pinned exclusive copies; worker inventories hash in
bounded chunks. Detected mutations and failed copies reject before dependent
workers. Gnark's constraint decoder still buffers internally; this is not a
maximum-size setup/prover qualification. See
[decision 0041](../../../docs/decisions/0041-streamed-proof-artifacts.md).

## Maximum commitment artifacts and proofs

`input-export CAPACITY` writes a compiled `circuit.r1cs` and numeric `capacity.json`;
`input-inspect CAPACITY` reloads a caller-pinned circuit and writes its counts.
`input-setup-compiled CAPACITY` reads that circuit and exclusively creates setup
keys. It does not authenticate the supplied circuit: the controller must pin it
against independently retained inputs before use. Failed setup no longer requires
recompilation. The tiny export/reload/setup path has a real-proof unit test.

The Mac maximum export and fresh reload pass; see
[decision 0045](../../../docs/decisions/0045-standing-approval-and-maximum-artifacts.md)
and [numeric evidence](../../evidence/w18-maximum-artifacts-2026-10-21.json).
The larger-memory Linux campaign is a separate optional controller,
`python -m hallmark._gnark_maximum --binary BINARY --expected-binary SHA256 --output FRESH_DIRECTORY`.
It requires the explicit [HF run plan](../../../docs/decisions/0046-bounded-maximum-hf-proof.md),
passes a tiny real-proof fixture first, and never sets `qualified_backend` true.
The existing compilation-only command keeps its original limits. A prepared
controller, native fixture agreement or CI test does not establish that the
maximum setup or proof has executed.

The separately retained [maximum result](../../evidence/w18-parallel-maximum-result-2026-10-21.json)
now records actual proofs for empty, 32,767-byte and 32,768-byte inputs, all frozen
negative cases and two fresh Mac replays. The original-dependency replay checks
compatibility using the same verifier implementation. Setup takes 2,195.581
seconds; the batch takes 1,791.308 seconds against its 1,800-second limit, with
87,162,712,064-byte peak worker RSS. This single CPU-host observation has narrow
time headroom and does not qualify a full encoder, independent verifier, setup
ceremony or security/hiding claim. No automatic rerun follows from this result.

## Run the staged qualification command

The installed command uses the same controllers and a single protocol/budget:

```text
uv run --locked hallmark qualify APPROVED_PROTOCOL.json \
  --expected-protocol EXTERNALLY_RETAINED_HPROTOCOL --output FRESH_DIRECTORY
```

Prepare the strict [protocol schema](../../../docs/schemas/qualification-protocol-v1.json)
with `hallmark.qualification.QualificationProtocol`. Its `identity().hex()` is the
typed `H(protocol)` pin, not the JSON file SHA-256. File references are relative to
the protocol's trusted parent. `controller_sha256()` pins the installed controller
and local boundary helper sources; the eight file references pin the exact binary,
rule/MLP/block fixtures, source/licence review, dependency review, build and authority
records. Review and retain that protocol identity outside the output before execution.
The shipped protocol fixture is a structural marker and must never be executed.

The stages run installation → rule → MLP → block without skipping or retrying.
The command preserves snapshots, plans, setup/proof artifacts, costs and failures.
The output must be new. Shared wall/verifier deadlines and measured CPU/RSS/storage
bounds apply across stages. All worker commands sample live RSS every 10 ms and
request termination at seven eighths of the declared ceiling (14 GiB by default).
Monitor failures reject; exit races retain the actual child status. Inspect
`memory_limit_exceeded`, `memory_monitor_failed`, `memory_sample_process_missing`,
sampled peak and post-exit peak
in each cost receipt. Sampling can overshoot; see
[decision 0036](../../../docs/decisions/0036-live-proof-worker-memory.md).
Native `ESRCH` followed by a normal reaped exit resolves the missing-process
sample; a killed live child or unresolved sampling error still rejects.
Process CPU/per-file limits and the macOS sandbox do
not provide a hard aggregate memory/storage quota. Use a trusted output parent and
account for existing runs within the owner's total storage/time envelope.

Even all 541 checks passing returns exit **3**, `status: incomplete` and explicit
missing qualification gates. Read the JSON result; exit 3 alone may instead be a
resource or execution failure. No complete encoder or independent setup/security
review is supplied. See [decision 0026](../../../docs/decisions/0026-staged-qualification-command.md).
