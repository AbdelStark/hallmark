# Optional Boolean-wire cache experiment

`boolean-wire-cache.patch` is a local research modification of Consensys gnark
v0.16.4, commit `e974abb44722dd201a7f1949baeabca0fef5866e`. Upstream gnark is
Copyright 2020-2025 Consensys Software Inc., licensed under
Apache-2.0; the retained [licence](GNARK-LICENSE) applies to the upstream material.
The patch marks its modified code. It adds no dependency and is not enabled by
this probe's `go.mod` or the Python package.

The reviewed original `frontend/cs/r1cs/builder.go` SHA-256 is
`d515546fb3442a38edf5487e6d5c0e52173687348408cb4a5ab5852dc9650e03`.
After patching it must be
`3cdd1a266ffba596d01b87a6bdcf51e141f92ae17d991bb9fe7f6e2149de01d4`.
The patch SHA-256 is
`5f70f965f4e4443ef32a01b5a2dc0163ae213d5dc86064fecc1f04fdcd52cb8c`.

Under an approved run plan, first run `go mod verify` with the admitted isolated
toolchain/cache. Copy the verified module to a fresh private directory, keep its
licence and inventory, and apply the patch there with `patch -p1`. Never modify
the original module cache. Copy this probe's `go.mod`/`go.sum` to a fresh matching
modfile pair; add a `replace github.com/consensys/gnark => ABSOLUTE_COPY` line.
Build using `-modfile=FRESH.mod -mod=readonly` and the documented offline environment.
Keep the original and patched module/source/binary identities separate.

Before any large run, build the same `cache_test.go` with upstream and patched
modules. Run `TestBooleanCache` and `TestCircuitFingerprints`, and compare all
seven `CIRCUIT` JSON records exactly, including serialized R1CS hashes and lengths.
Then execute fresh actual proof/negative-witness checks under a bounded protocol.
These checks do not establish general compiler correctness, independent security,
full-input proving or encoder qualification. See
[decision 0038](../../../../docs/decisions/0038-boolean-wire-cache-candidate.md).
