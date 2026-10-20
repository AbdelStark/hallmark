# Optional local proof probes

This directory contains two real-proof experiments for W18, not a qualified
Hallmark backend. The Python runtime has no new dependency or acceptance path.
See [decision 0022](../../../docs/decisions/0022-local-proof-probes.md) for the
exact relations, resource boundary, failed candidate and remaining gates.

`main.go` implements a cubic installation relation. `rule.go` implements the
fixed marker and complete salted input hash in `rule-fixture.json`. The latter
fixture's classifier enrollment tags are synthetic. A successful result always
contains `qualified_backend: false`.

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

From the repository root, under a recorded approved local protocol:

```text
uv run --locked python scripts/check_gnark_probe.py \
  --binary BINARY --expected-binary BUILD_SHA256 --output FRESH_DIRECTORY

uv run --locked python scripts/check_gnark_rule_probe.py \
  --binary BINARY --expected-binary BUILD_SHA256 \
  --fixture research/probes/gnark/rule-fixture.json \
  --expected-fixture FROZEN_FIXTURE_SHA256 --output FRESH_DIRECTORY
```

Take pins from the reviewed build/protocol record, independently of worker
outputs. Fresh directories are mandatory; failures are retained. The rule
runner checks native vectors, every public field, byte/count/Boolean aliases,
padding, changed private input, missing final input, proof bytes and a second
setup's key. Read the raw result and failure records; an exit code alone is
insufficient evidence.

`make check` runs offline boundary and fixture-reproduction tests. It does not
download Go, build the backend or prove these relations. OS sandbox tests skip
on hosts other than macOS arm64; they do not establish Linux isolation. Actual
proof execution is an explicit, separately budgeted command above.

The generated fixture reproduces with:

```text
uv run --locked python scripts/build_gnark_rule_fixture.py
```

Do not commit toolchains, module caches, binaries, proving keys or local run
directories. Public synthetic proof/key examples and numeric costs may be
retained as explicit research evidence; they are not operational trust anchors.
