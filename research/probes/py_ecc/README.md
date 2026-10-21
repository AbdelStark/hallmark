# Separate synthetic encoder verifier

This research probe checks the fixed Groth16/BLS12-381 encoder profile with
py-ecc arithmetic. It shares no gnark proof decoder, pairing implementation or
verification code. It supports exactly 100 public scalars and one Pedersen
commitment with no publicly committed indices. It does not qualify a backend,
authenticate a model or key, or establish a trusted setup.

`verify.py` exposes `verify(key_bytes, proof_bytes, public_scalars,
expected_key_sha256=...)`. Supply the key pin and public scalars from separately
enrolled expectations. Malformed or unsupported inputs raise `ValueError`;
well-formed proofs return the result of two separate pairing checks. Scalars are
never silently reduced. Canonical infinity points belong to the subgroup and
still must satisfy both equations. Proofs are not byte-unique: jointly negating
A and B preserves their pairing.

Use an isolated CPython 3.12 environment on Mac arm64 or Linux x86_64:

```sh
uv venv --python 3.12 runs/separate-verifier-env
uv pip install --python runs/separate-verifier-env/bin/python \
  --require-hashes --only-binary :all: \
  -r research/probes/py_ecc/requirements.txt
```

The [dependency review](../../evidence/w18-second-verifier-dependencies-2026-10-21.json)
records exact releases, wheel hashes and license notices. The upstream library
is experimental and unaudited; this is not independent human security review.
No dependency is added to the core runtime.

`generate_fixture.py` requires an already built, caller-pinned Go probe and a
fresh output directory. It enrolls the key and the frozen capacity-eight public
vector before proving, preserves worker files/costs, and emits
`generated-unverified`. `check.py --fixture ... --expected-fixture ...
--expected-key ...` checks a pinned JSON fixture and the fixed negative roster.
Run these only within the declared host/time/memory envelope. The
[hosted proof-artifact job](../../../.github/workflows/check.yml) shows the complete
bounded Linux invocation; the fixture contains synthetic inputs only.

The [decision](../../../docs/decisions/0055-separate-synthetic-proof-verifier.md)
separates this implementation evidence from setup, enrollment, model-quality,
security-review and hardware obligations. Keep raw runs and generated keys/proofs
outside git. Do not use the research checker as a production acceptance API.
