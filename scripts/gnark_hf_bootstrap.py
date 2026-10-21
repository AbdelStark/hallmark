"""Public-input-only bootstrap for pinned HF compilation or maximum proof research."""

import base64
import hashlib
import io
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pedersen_candidate(plan):
    if "patched_pedersen" not in plan:
        return None
    raw = base64.b64decode(plan["patched_pedersen"], validate=True)
    if (
        plan["schema_id"] != "hallmark.hf-maximum-inputs/1"
        or digest(raw) != "04d66b48c95d1a55319b3639f1034bd79d6ce6d98bc573723dd983db16249444"
    ):
        raise ValueError("unapproved Pedersen setup candidate")
    return raw


def validate(plan):
    pedersen_candidate(plan)
    maximum = plan["schema_id"] == "hallmark.hf-maximum-inputs/1"
    if (
        plan["schema_id"] not in ("hallmark.hf-compile-inputs/1", "hallmark.hf-maximum-inputs/1")
        or not re.fullmatch("[a-f0-9]{40}", plan["source_commit"])
        or set(plan["files"])
        != {
            *(
                "research/probes/gnark/" + name
                for name in [
                    "artifacts_test.go",
                    "block.go",
                    "cache_test.go",
                    "go.mod",
                    "go.sum",
                    "graph.go",
                    "input.go",
                    "input_scale.go",
                    "input_scale_test.go",
                    "main.go",
                    "mlp.go",
                    "rule.go",
                ]
            ),
            "src/hallmark/__init__.py",
            "src/hallmark/_gnark_probe.py",
            "src/hallmark/_gnark_linux_compile.py",
            *(["src/hallmark/_gnark_maximum.py"] if maximum else []),
        }
        or plan["go_archive"]["filename"] != "go1.26.8.linux-amd64.tar.gz"
        or plan["go_archive"]["size"] != 66897291
        or digest(base64.b64decode(plan["patched_builder"], validate=True))
        != "3cdd1a266ffba596d01b87a6bdcf51e141f92ae17d991bb9fe7f6e2149de01d4"
    ):
        raise ValueError("unapproved job input")
    if maximum and (
        not re.fullmatch(r"[0-9]{19}", plan["experiment"])
        or digest(base64.b64decode(plan["patched_g1"], validate=True))
        != "2c2368587355ffe6747a8fcf0d147180f74fd4b559efeccb428fbe0d2bb026ac"
        or not re.fullmatch(r"[a-f0-9]{64}", plan["crypto_inventory_sha256"])
    ):
        raise ValueError("unapproved maximum setup candidate")
    for pin in [*plan["files"].values(), plan["go_archive"]]:
        if not re.fullmatch("[a-f0-9]{64}", pin["sha256"]):
            raise ValueError("invalid source pin")
    for pin in plan["files"].values():
        if type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= 262144:
            raise ValueError("invalid source size")
    if (
        plan["go_archive"]["sha256"]
        != "d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b"
    ):
        raise ValueError("unapproved toolchain")


def inventory(root):
    return {
        str(p.relative_to(root)): {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def main(plan):
    validate(plan)
    maximum = plan["schema_id"] == "hallmark.hf-maximum-inputs/1"
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("Linux x86-64 required")
    root = Path("/tmp/hallmark-hf-compile")
    root.mkdir(mode=0o700)
    start = time.monotonic()
    (root / "inputs.json").write_text(json.dumps(plan, sort_keys=True))

    def fetch(url, path, pin):
        if time.monotonic() - start > 400:
            raise TimeoutError("bootstrap download deadline")
        size = pin.get("bytes", pin.get("size"))
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(size + 1)
        if len(raw) != size or digest(raw) != pin["sha256"]:
            raise ValueError("download pin mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(raw)
        return raw

    def run(label, command, cwd, env, seconds):
        # Reserve a separate copy window; mutable bucket metadata is not a worker filesystem.
        deadline = (8350 if label == "retain-output" else 7450) if maximum else 1100
        if time.monotonic() - start + seconds > deadline:
            raise TimeoutError("insufficient remaining job budget")
        began = time.monotonic()
        failure = None
        print(json.dumps({"starting_stage": label, "timeout_seconds": seconds}), flush=True)
        with (
            (root / (label + ".stdout")).open("xb") as out,
            (root / (label + ".stderr")).open("xb") as err,
        ):
            child = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                start_new_session=True,
            )
            try:
                code = child.wait(timeout=seconds)
            except BaseException as error:
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait()
                failure = error
        stdout = (root / (label + ".stdout")).read_bytes()
        stderr = (root / (label + ".stderr")).read_bytes()
        receipt = {
            "stage": label,
            "argv": command,
            "exit_code": code,
            "elapsed_seconds": time.monotonic() - began,
            "stdout_sha256": digest(stdout),
            "stderr_sha256": digest(stderr),
            "failure_type": type(failure).__name__ if failure else None,
        }
        print(json.dumps({"receipt": receipt}), flush=True)
        print(stdout.decode(), end="", flush=True)
        print(stderr.decode(), end="", file=sys.stderr, flush=True)
        if failure:
            raise failure
        if code != 0:
            raise RuntimeError(label)
        return stdout

    for name, pin in plan["files"].items():
        fetch(
            "https://raw.githubusercontent.com/AbdelStark/hallmark/"
            + plan["source_commit"]
            + "/"
            + name,
            root / "repo" / name,
            pin,
        )
    sys.path.insert(0, str(root / "repo/src"))
    from hallmark._gnark_linux_compile import container_memory_limit

    required_memory = 170_000_000_000 if maximum else 28_000_000_000
    print(
        json.dumps({"container_memory_limit_bytes": container_memory_limit(required_memory)}),
        flush=True,
    )
    go_raw = fetch(
        "https://go.dev/dl/" + plan["go_archive"]["filename"],
        root / "go.tar.gz",
        plan["go_archive"],
    )
    with tarfile.open(fileobj=io.BytesIO(go_raw)) as archive:
        archive.extractall(root, filter="data")
    del go_raw
    assert digest((root / "go/LICENSE").read_bytes()) == (
        "911f8f5782931320f5b8d1160a76365b83aea6447ee6c04fa6d5591467db9dad"
    )
    go = str(root / "go/bin/go")
    source = root / "repo/research/probes/gnark"
    (root / "tmp").mkdir()
    env = {
        "PATH": str(root / "go/bin") + ":/usr/bin:/bin",
        "GOROOT": str(root / "go"),
        "GOPATH": str(root / "gopath"),
        "GOMODCACHE": str(root / "gomodcache"),
        "GOCACHE": str(root / "gocache"),
        "GOTOOLCHAIN": "local",
        "GOTELEMETRY": "off",
        "GOPROXY": "https://proxy.golang.org",
        "GOSUMDB": "sum.golang.org",
        "GOMAXPROCS": "2",
        "GOMEMLIMIT": "1GiB",
        "CGO_ENABLED": "0",
        "GOFLAGS": "-p=2",
        "LANG": "C",
        "TZ": "UTC",
        "TMPDIR": str(root / "tmp"),
    }
    run("download", [go, "mod", "download"], source, env, 120)
    run("module-verification", [go, "mod", "verify"], source, env, 30)
    for name in ["go.mod", "go.sum"]:
        assert (
            digest((source / name).read_bytes())
            == plan["files"]["research/probes/gnark/" + name]["sha256"]
        )
    module = root / "gomodcache/github.com/consensys/gnark@v0.16.4"
    patched = root / "gnark-patched"
    shutil.copytree(module, patched)
    for directory, _, _ in os.walk(patched):
        os.chmod(directory, 0o700)
    builder = patched / "frontend/cs/r1cs/builder.go"
    assert (
        digest(builder.read_bytes())
        == "d515546fb3442a38edf5487e6d5c0e52173687348408cb4a5ab5852dc9650e03"
    )
    os.chmod(builder, 0o600)
    builder.write_bytes(base64.b64decode(plan["patched_builder"], validate=True))
    actual = inventory(patched)
    assert (
        digest(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode())
        == plan["patched_inventory_sha256"]
    )
    modfile = root / "patched.mod"
    modfile.write_bytes(
        (source / "go.mod").read_bytes()
        + b"\nreplace github.com/consensys/gnark => "
        + str(patched).encode()
        + b"\n"
    )
    shutil.copyfile(source / "go.sum", root / "patched.sum")
    if maximum:
        crypto = root / "crypto-patched"
        shutil.copytree(
            root
            / "gomodcache/github.com/consensys/gnark-crypto@v0.21.1-0.20260913224755-1409fe592052",
            crypto,
        )
        for directory, _, _ in os.walk(crypto):
            os.chmod(directory, 0o700)
        g1 = crypto / "ecc/bls12-381/g1.go"
        assert digest(g1.read_bytes()) == (
            "22544597ca454517d5a4ae788a5349ae2e2ec72380e101bf1d37b4d0ffe50165"
        )
        os.chmod(g1, 0o600)
        g1.write_bytes(base64.b64decode(plan["patched_g1"], validate=True))
        candidate = pedersen_candidate(plan)
        if candidate is not None:
            pedersen = crypto / "ecc/bls12-381/fr/pedersen/pedersen.go"
            assert digest(pedersen.read_bytes()) == (
                "8a9597c6901ad2e67542c475e93ec23f8330f586a835a2dc82d9818eaba1ee0e"
            )
            os.chmod(pedersen, 0o600)
            pedersen.write_bytes(candidate)
        assert (
            digest(json.dumps(inventory(crypto), sort_keys=True, separators=(",", ":")).encode())
            == plan["crypto_inventory_sha256"]
        )
        with modfile.open("ab") as handle:
            handle.write(
                b"\nreplace github.com/consensys/gnark-crypto => " + str(crypto).encode() + b"\n"
            )
    env["GOPROXY"] = "off"
    flags = ["-mod=readonly", "-modfile=" + str(modfile)]
    run("build-tests", [go, "test", "-c", *flags, "-o", str(root / "tests"), "."], source, env, 180)
    fixture = run(
        "small-fixtures",
        [
            str(root / "tests"),
            "-test.run",
            "Test(Artifact|CompiledSetup|BooleanCache|Prefix|InputBatch|"
            "AssignmentReader|CircuitFingerprints)",
            "-test.v",
        ],
        root,
        env,
        30,
    )
    records = [
        json.loads(line.removeprefix("CIRCUIT "))
        for line in fixture.decode().splitlines()
        if line.startswith("CIRCUIT ")
    ]
    assert records == plan["fingerprints"]
    run(
        "build-probe",
        [go, "build", "-trimpath", "-buildvcs=false", *flags, "-o", str(root / "probe"), "."],
        source,
        env,
        120,
    )
    binary_sha = digest((root / "probe").read_bytes())
    print(
        json.dumps(
            {
                "build": {
                    "binary_sha256": binary_sha,
                    "environment": env,
                    "python": sys.version,
                    "platform": platform.platform(),
                    "module_inventory_sha256": plan["patched_inventory_sha256"],
                    "fingerprints": records,
                }
            }
        ),
        flush=True,
    )
    child_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONPATH": str(root / "repo/src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    execution = root / "execution"
    try:
        run(
            "maximum-proof" if maximum else "compilation",
            [
                sys.executable,
                "-m",
                "hallmark._gnark_maximum" if maximum else "hallmark._gnark_linux_compile",
                "--binary",
                str(root / "probe"),
                "--expected-binary",
                binary_sha,
                "--output",
                str(execution),
            ],
            root,
            child_env,
            6650 if maximum else 650,
        )
    finally:
        if maximum and execution.exists():
            run(
                "retain-output",
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; from hallmark._gnark_maximum import "
                    "retain_outputs; import sys; "
                    "retain_outputs(Path(sys.argv[1]), Path(sys.argv[2]))",
                    str(execution),
                    "/output/w18-" + plan["experiment"],
                ],
                root,
                child_env,
                900,
            )


if __name__ == "__main__":
    try:
        plan = json.loads(sys.argv[1])
        if digest(sys.argv[1].encode()) != sys.argv[2]:
            raise ValueError("manifest pin mismatch")
        main(plan)
    except Exception as error:
        print(
            json.dumps(
                {"bootstrap_failure_type": type(error).__name__, "qualified_backend": False}
            ),
            flush=True,
        )
        raise SystemExit(3) from None
