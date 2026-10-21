"""Offline admission checks and actual Linux process-boundary fixtures."""

import errno
import json
import os
import platform
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

from hallmark import _gnark_linux_compile as probe
from hallmark._gnark_probe import PinnedArtifact, RunBudget

linux = pytest.mark.skipif(
    platform.system() != "Linux" or platform.machine() != "x86_64",
    reason="actual kernel checks require Linux x86-64",
)


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_seconds", 7201),
        ("threads", 49),
        ("cpu_seconds", 345601),
        ("max_rss_bytes", 230_000_000_001),
        ("max_output_bytes", 129 * 1024**3),
    ],
)
def test_large_worker_invalid_budget_fails_before_creating_output(tmp_path, field, value):
    budget = RunBudget(tmp_path, time.monotonic() + 30, 10, 5, 40, 4, 1024**3, 1024**2)
    with pytest.raises(ValueError):
        probe.invoke(
            [sys.executable],
            tmp_path / "worker",
            seconds=1,
            budget=replace(budget, **{field: value}),
        )
    assert not (tmp_path / "worker").exists()


@pytest.mark.parametrize("name", ["../escape", "/absolute", ".", "..", ""])
def test_worker_rejects_input_path_before_writing(tmp_path, name):
    with pytest.raises(ValueError):
        probe.invoke([sys.executable], tmp_path / "worker", seconds=1, inputs={name: b"x"})
    assert not (tmp_path / "worker").exists()


@linux
def test_explicit_proof_budget_streams_pinned_input_and_output(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"x" * 131072)
    budget = RunBudget(tmp_path, time.monotonic() + 30, 10, 5, 40, 2, 1024**3, 1024**2)
    code = """import os,pathlib,socket,errno
assert os.environ['GOMAXPROCS']=='2'
assert os.environ['GOMEMLIMIT']==str(3*1024**3//4)
data=pathlib.Path('input.bin').read_bytes()
assert len(data)==131072 and data==b'x'*131072
pathlib.Path('output.bin').write_bytes(data)
try: socket.socket()
except OSError as e: assert e.errno==errno.EPERM
else: raise AssertionError('network available')
"""
    cost = probe.invoke(
        [sys.executable, "-c", code],
        tmp_path / "worker",
        seconds=5,
        budget=budget,
        max_rss=1024**3,
        cutoff=512 * 1024**2,
        max_file=256 * 1024,
        inputs={"input.bin": PinnedArtifact(source, probe.digest(source.read_bytes()), 131072)},
    )
    assert cost["exit_code"] == 0 and cost["within_limits"]
    assert cost["files"]["input.bin"] == cost["files"]["output.bin"]


def test_explicit_worker_rejects_changed_input_before_launch(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"changed")
    with pytest.raises(ValueError):
        probe.invoke(
            [sys.executable],
            tmp_path / "worker",
            seconds=1,
            inputs={"input.bin": PinnedArtifact(source, "0" * 64, 7)},
        )
    assert not (tmp_path / "worker/plan.json").exists()


@pytest.mark.parametrize(
    "arch,number,expected",
    [
        (0xC000003E, 39, 0x7FFF0000),
        *((0xC000003E, n, 0x50000 | errno.EPERM) for n in [41, 53, 101, 425, 438]),
        (0xC000003E, 0x40000000 | 41, 0x80000000),
        (0x40000003, 102, 0x80000000),
    ],
)
def test_filter_rejects_network_and_abi_bypasses(arch, number, expected):
    rules = probe.network_filter()
    pc = value = 0
    for _ in range(len(rules)):
        code, yes, no, operand = rules[pc]
        if code == 0x06:
            assert operand == expected
            return
        if code == 0x20:
            value = {0: number, 4: arch}[operand]
        elif code == 0x15:
            pc += yes if value == operand else no
        elif code == 0x45:
            pc += yes if value & operand else no
        else:
            pytest.fail("unexpected filter instruction")
        pc += 1
    pytest.fail("filter did not return")


@pytest.mark.parametrize("text", ["", "1 2", "1 -2 3 4 5 6 7", "1 ² 3 4 5 6 7"])
def test_invalid_memory_sample_rejects(monkeypatch, text):
    monkeypatch.setattr(Path, "read_text", lambda self: text)
    with pytest.raises(ValueError):
        probe.resident_bytes(123)


def test_memory_units(monkeypatch):
    monkeypatch.setattr(Path, "read_text", lambda self: "123 27 0 0 0 0 0\n")
    monkeypatch.setattr(os, "sysconf", lambda _: 4096)
    assert probe.resident_bytes(123) == 27 * 4096


@pytest.mark.parametrize("value", ["max", "-1", "1000000000", "invalid"])
def test_container_budget_rejects_unknown_or_small_limit(monkeypatch, value):
    monkeypatch.setattr(Path, "read_text", lambda self: value)
    with pytest.raises(ValueError):
        probe.container_memory_limit()


@pytest.mark.parametrize("failure", ["none", "small", "maximum", "mismatch", "bad-report"])
def test_compile_roster_and_incomplete_scope(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    monkeypatch.setattr(probe.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(probe, "container_memory_limit", lambda: 30_000_000_000)
    binary = tmp_path / "binary"
    binary.write_bytes(b"pinned test input")
    names = []

    def invoke(command, work, **kwargs):
        names.append(work.name)
        work.mkdir()
        count = 205547 if work.name == "small" else 1234567
        if failure == "mismatch" and work.name == "confirmation":
            count += 1
        report = {
            "schema_id": "hallmark.gnark-installation-probe/1",
            "status": "passed",
            "constraints": count,
            "elapsed_ns": 100,
        }
        if failure == "bad-report" and work.name == "small":
            report["constraints"] = True
        (work / "stdout.txt").write_text(json.dumps(report))
        return {"exit_code": 0, "within_limits": work.name != failure}

    monkeypatch.setattr(probe, "invoke", invoke)
    result = probe.check(binary, probe.digest(binary.read_bytes()), tmp_path / "out")
    assert result["maximum_compile_reproduced"] == (failure == "none")
    assert result["qualified_backend"] is False and result["full_input_proof"] is False
    assert (tmp_path / "out/result.json").is_file()
    if failure in ["small", "bad-report"]:
        assert names == ["network-smoke", "small"]
    elif failure == "maximum":
        assert names == ["network-smoke", "small", "maximum"]
    else:
        assert names == ["network-smoke", "small", "maximum", "confirmation"]


@linux
def test_kernel_filter_and_no_inherited_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("HALLMARK_SENTINEL_SECRET", "not-a-real-secret")
    code = """import errno,os,socket
assert 'HALLMARK_SENTINEL_SECRET' not in os.environ
for make in (socket.socket, socket.socketpair):
 try: make()
 except OSError as error: assert error.errno == errno.EPERM
 else: raise AssertionError('network socket available')
"""
    cost = probe.invoke([sys.executable, "-c", code], tmp_path / "network", seconds=5)
    assert cost["exit_code"] == 0 and cost["within_limits"]
    assert 0 < cost["max_rss_bytes"] < probe.MAX_RSS


@linux
def test_timeout_stops_worker(tmp_path):
    cost = probe.invoke(
        [sys.executable, "-c", "import time;time.sleep(10)"], tmp_path / "timeout", seconds=0.1
    )
    assert cost["exit_code"] < 0 and cost["timed_out"] and not cost["within_limits"]


@linux
def test_live_memory_cutoff(tmp_path):
    cost = probe.invoke(
        [sys.executable, "-c", "import time;x=bytearray(128*1024**2);time.sleep(10)"],
        tmp_path / "memory",
        seconds=5,
        max_rss=200 * 1024**2,
        cutoff=64 * 1024**2,
    )
    assert cost["exit_code"] < 0 and cost["memory_limit_exceeded"] and not cost["within_limits"]


@linux
def test_lost_sample_fails_closed(tmp_path, monkeypatch):
    def unavailable(pid):
        raise OSError("unavailable")

    monkeypatch.setattr(probe, "resident_bytes", unavailable)
    cost = probe.invoke(
        [sys.executable, "-c", "import time;time.sleep(10)"], tmp_path / "monitor", seconds=5
    )
    assert cost["exit_code"] < 0 and cost["memory_monitor_failed"] and not cost["within_limits"]


@pytest.fixture
def bootstrap_plan(monkeypatch):
    import base64
    import runpy

    bootstrap = runpy.run_path(str(Path(__file__).parents[1] / "scripts/gnark_hf_bootstrap.py"))
    original_digest = bootstrap["digest"]
    # Isolate source-inventory validation from the separately pinned compiler patch.
    monkeypatch.setitem(
        bootstrap["validate"].__globals__,
        "digest",
        lambda raw: {
            b"test builder": "3cdd1a266ffba596d01b87a6bdcf51e141f92ae17d991bb9fe7f6e2149de01d4",
            b"test g1": "2c2368587355ffe6747a8fcf0d147180f74fd4b559efeccb428fbe0d2bb026ac",
            b"test pedersen": "04d66b48c95d1a55319b3639f1034bd79d6ce6d98bc573723dd983db16249444",
        }.get(raw, original_digest(raw)),
    )
    names = [
        "artifacts_test.go",
        "block.go",
        "cache_test.go",
        "encoder.go",
        "encoder-graph.json",
        "go.mod",
        "go.sum",
        "graph.go",
        "input.go",
        "input_scale.go",
        "input_scale_test.go",
        "main.go",
        "mlp.go",
        "normalization.go",
        "rule.go",
    ]
    files = {"research/probes/gnark/" + name: {} for name in names}
    files.update(
        {
            "src/hallmark/" + name: {}
            for name in [
                "__init__.py",
                "_gnark_probe.py",
                "_gnark_linux_compile.py",
            ]
        }
    )
    plan = {
        "schema_id": "hallmark.hf-compile-inputs/1",
        "source_commit": "a" * 40,
        "files": files,
        "go_archive": {
            "filename": "go1.26.8.linux-amd64.tar.gz",
            "size": 66897291,
            "sha256": "d0f743b33e8d8945e6b1f432edd15785c70507121d6e2a723b21285eddf8b57b",
        },
        "patched_builder": base64.b64encode(b"test builder").decode(),
    }
    for pin in files.values():
        pin.update(bytes=1, sha256="a" * 64)
    bootstrap["validate"](plan)
    return bootstrap["validate"], plan


@pytest.mark.parametrize("mutation", ["revision", "files", "toolchain", "builder"])
def test_bootstrap_rejects_unapproved_manifest(bootstrap_plan, mutation):
    validate, plan = bootstrap_plan
    if mutation == "revision":
        plan["source_commit"] = "../main"
    elif mutation == "files":
        plan["files"] = {"../../.env": {}}
    elif mutation == "toolchain":
        plan["go_archive"]["filename"] = "unreviewed.tar.gz"
    else:
        plan["patched_builder"] = "!"
    with pytest.raises(ValueError):
        validate(plan)


@pytest.mark.parametrize(
    "name,size,accepted",
    [
        ("encoder-graph.json", 1048576, True),
        ("encoder-graph.json", 1048577, False),
        ("encoder.go", 262144, True),
        ("encoder.go", 262145, False),
        ("encoder-graph.json", True, False),
        ("encoder-graph.json", 0, False),
    ],
)
def test_bootstrap_enlarges_only_embedded_encoder_data(bootstrap_plan, name, size, accepted):
    validate, plan = bootstrap_plan
    plan["files"]["research/probes/gnark/" + name]["bytes"] = size
    if accepted:
        validate(plan)
    else:
        with pytest.raises(ValueError, match="size"):
            validate(plan)


def test_bootstrap_requires_embedded_encoder_data(bootstrap_plan):
    validate, plan = bootstrap_plan
    del plan["files"]["research/probes/gnark/encoder-graph.json"]
    with pytest.raises(ValueError, match="input"):
        validate(plan)


@pytest.mark.parametrize("failure", [None, "fixture", "patch", "large", "scope"])
def test_encoder_bootstrap_requires_exact_fixture_and_reviewed_patch(bootstrap_plan, failure):
    import base64

    validate, plan = bootstrap_plan
    plan.update(
        schema_id="hallmark.hf-encoder-maximum-inputs/1",
        experiment="1792603925159848000",
        patched_g1=base64.b64encode(b"test g1").decode(),
        patched_pedersen=base64.b64encode(b"test pedersen").decode(),
        crypto_inventory_sha256="a" * 64,
    )
    fixture = "research/probes/gnark/encoder-maximum-fixture.json"
    plan["files"][fixture] = {"bytes": 99588, "sha256": "a" * 64}
    plan["files"]["src/hallmark/_gnark_maximum.py"] = {"bytes": 1, "sha256": "a" * 64}
    if failure == "fixture":
        del plan["files"][fixture]
    elif failure == "patch":
        del plan["patched_pedersen"]
    elif failure == "large":
        plan["files"][fixture]["bytes"] = 262145
    elif failure == "scope":
        plan["schema_id"] = "hallmark.hf-maximum-inputs/1"
    if failure:
        with pytest.raises(ValueError):
            validate(plan)
    else:
        validate(plan)


def test_optional_pedersen_candidate_is_pinned():
    import base64
    import runpy

    bootstrap = runpy.run_path(str(Path(__file__).parents[1] / "scripts/gnark_hf_bootstrap.py"))
    candidate = bootstrap["pedersen_candidate"]
    assert candidate({"schema_id": "hallmark.hf-maximum-inputs/1"}) is None
    for schema in ["hallmark.hf-compile-inputs/1", "hallmark.hf-maximum-inputs/1"]:
        for raw in ["!", base64.b64encode(b"unreviewed").decode()]:
            plan = {"schema_id": schema, "patched_pedersen": raw}
            with pytest.raises(ValueError):
                candidate(plan)
            with pytest.raises(ValueError):
                bootstrap["validate"](plan)


@pytest.mark.parametrize("exit_code", [0, 3])
def test_bootstrap_relays_live_bytes_and_preserves_tail(tmp_path, monkeypatch, exit_code):
    import io
    import runpy
    import subprocess
    from types import SimpleNamespace

    bootstrap = runpy.run_path(str(Path(__file__).parents[1] / "scripts/gnark_hf_bootstrap.py"))
    acknowledgement = tmp_path / "ack"

    class Acknowledge(io.BytesIO):
        def write(self, raw):
            if raw:
                acknowledgement.touch()
            return super().write(raw)

    relayed = [Acknowledge(), io.BytesIO()]
    paths = [tmp_path / "stdout", tmp_path / "stderr"]
    command = (
        "import os,sys,time;from pathlib import Path\n"
        "os.write(1,b'ready\\xe2');deadline=time.monotonic()+3\n"
        "while not Path(sys.argv[1]).exists():\n"
        " assert time.monotonic()<deadline\n"
        " time.sleep(.01)\n"
        "os.write(1,b'\\x82\\xac'+b'x'*70000+b'\\n');os.write(2,b'error\\xff\\n')\n"
        "raise SystemExit(int(sys.argv[2]))\n"
    )
    offsets = [0, 0]
    with paths[0].open("wb") as out, paths[1].open("wb") as err:
        child = subprocess.Popen(
            [sys.executable, "-c", command, str(acknowledgement), str(exit_code)],
            stdout=out,
            stderr=err,
        )
        try:
            with monkeypatch.context() as patch:
                patch.setattr(sys, "stdout", SimpleNamespace(buffer=relayed[0]))
                patch.setattr(sys, "stderr", SimpleNamespace(buffer=relayed[1]))
                assert bootstrap["wait_with_progress"](child, paths, 5, offsets) == exit_code
        finally:
            if child.poll() is None:
                child.kill()
            child.wait()
    assert acknowledgement.exists()
    expected = [b"ready\xe2\x82\xac" + b"x" * 70000 + b"\n", b"error\xff\n"]
    for index, path in enumerate(paths):
        raw = path.read_bytes()
        assert raw == expected[index]
        assert relayed[index].getvalue() == raw[: offsets[index]]
        assert relayed[index].getvalue() + raw[offsets[index] :] == expected[index]


def test_bootstrap_live_relay_preserves_deadline(tmp_path, monkeypatch):
    import io
    import runpy
    import subprocess
    from types import SimpleNamespace

    bootstrap = runpy.run_path(str(Path(__file__).parents[1] / "scripts/gnark_hf_bootstrap.py"))
    paths = [tmp_path / "stdout", tmp_path / "stderr"]
    with paths[0].open("wb") as out, paths[1].open("wb") as err:
        child = subprocess.Popen(
            [sys.executable, "-c", "import time;time.sleep(10)"], stdout=out, stderr=err
        )
        try:
            with monkeypatch.context() as patch:
                for stream in ["stdout", "stderr"]:
                    patch.setattr(sys, stream, SimpleNamespace(buffer=io.BytesIO()))
                with pytest.raises(subprocess.TimeoutExpired):
                    bootstrap["wait_with_progress"](child, paths, 0.05, [0, 0])
        finally:
            child.kill()
            child.wait()
