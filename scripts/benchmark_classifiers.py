"""Frozen same-host gnark/STWO/native measurements; provisioning is separate."""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import signal
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import circle_backend as circle
import classifier_comparison as comparison
import trained_common_input as common
from check_circle_engine import encode
from check_gnark_encoder import assignment
from run_circle_classifiers import trace_parity

from hallmark._gnark_probe import (
    PinnedArtifact,
    RunBudget,
    invoke,
    json_new,
    limits,
    read_regular,
    stream_regular,
    write_new,
)
from hallmark.integrity import parse_json

ROOT = Path(__file__).resolve().parents[1]
PREFIX = {"rule": "scaled-rule-", "mlp": "trained-mlp-", "encoder": "contextual-"}


def sha_file(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def tree_processes(root_pid):
    if platform.system() == "Linux":
        rows = {}
        for path in Path("/proc").glob("[0-9]*"):
            try:
                fields = (path / "stat").read_text().rpartition(")")[2].split()
                rows[int(path.name)] = int(fields[1]), int(fields[21]) * os.sysconf("SC_PAGE_SIZE")
            except (FileNotFoundError, ProcessLookupError):
                continue
    else:
        raw = subprocess.check_output(["/bin/ps", "-axo", "pid=,ppid=,rss="], timeout=5, text=True)
        rows = {
            int(p): (int(parent), int(rss) * 1024)
            for p, parent, rss in (line.split() for line in raw.splitlines())
        }
    if root_pid not in rows:
        raise ValueError("benchmark controller missing from memory sample")
    owned = {root_pid}
    while True:
        expanded = owned | {p for p, (parent, _) in rows.items() if parent in owned}
        if expanded == owned:
            break
        owned = expanded
    return rows, owned


def storage(root):
    files = [p.stat() for p in root.rglob("*") if p.is_file() and not p.is_symlink()]
    return dict(
        logical_bytes=sum(s.st_size for s in files),
        allocated_block_sum_bytes=sum(s.st_blocks * 512 for s in files),
        filesystem_free_bytes=shutil.disk_usage(root).free,
        physical_unique_bytes=None,
        physical_unique_reason="Shared APFS blocks repeat in stat; free space includes other work",
    )


def spread(values):
    if not values:
        return dict(successful=0, median=None, minimum=None, maximum=None, iqr=None)
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("invalid timing sample")
    q = (
        statistics.quantiles(values, n=4, method="inclusive")
        if len(values) > 1
        else [values[0]] * 3
    )
    return dict(
        successful=len(values),
        median=statistics.median(values),
        minimum=min(values),
        maximum=max(values),
        iqr=q[2] - q[0],
    )


def summarize(samples, plan):
    report = dict(workflows=[], proofs=[], native=[])
    for phase in ("fresh", "warm"):
        for backend in ("gnark", "circle"):
            selected = [s for s in samples if s["phase"] == phase and s["backend"] == backend]
            if len(selected) != plan["repetitions"][phase] or any(
                s["status"] != "passed" for s in selected
            ):
                raise ValueError("incomplete matched repetition matrix")
            if {s["repetition"] for s in selected} != set(range(plan["repetitions"][phase])):
                raise ValueError("duplicate or missing repetition identities")
            for sample in selected:
                if [c["case_id"] for c in sample["cases"]] != plan["case_ids"]:
                    raise ValueError("incomplete matched request coverage")
                for case in sample["cases"]:
                    if [p["kind"] for p in case["proofs"]] != list(circle.KINDS):
                        raise ValueError("incomplete matched classifier coverage")
            report["workflows"].append(
                dict(
                    phase=phase,
                    backend=backend,
                    attempted=len(selected),
                    full_wall_seconds=spread([s["full_wall_seconds"] for s in selected]),
                    sampled_process_tree_peak_rss_bytes=spread(
                        [s["sampled_process_tree_peak_rss_bytes"] for s in selected]
                    ),
                )
            )
            for case_id in plan["case_ids"]:
                cases = [c for s in selected for c in s["cases"] if c["case_id"] == case_id]
                report["native"].append(
                    dict(
                        phase=phase,
                        backend=backend,
                        case_id=case_id,
                        scope="all three classifiers on one request",
                        **{
                            name: spread([c[name] for c in cases])
                            for name in (
                                "native_inference_seconds",
                                "native_plus_binding_seconds",
                                "caller_binding_seconds",
                            )
                        },
                    )
                )
                for kind in circle.KINDS:
                    rows = [p for c in cases for p in c["proofs"] if p["kind"] == kind]
                    proving_key = "stark_proving" if backend == "circle" else "groth16_proving"
                    report["proofs"].append(
                        dict(
                            phase=phase,
                            backend=backend,
                            case_id=case_id,
                            kind=kind,
                            **{
                                name: spread([p[name] for p in rows])
                                for name in (
                                    "witness_seconds",
                                    "materialization_seconds",
                                    "serialization_seconds",
                                    "proof_bytes",
                                )
                            },
                            proving_seconds=spread(
                                [
                                    p["worker_timing"]["engine"]["stages_seconds"][proving_key]
                                    for p in rows
                                ]
                            ),
                            complete_prover_command_seconds=spread(
                                [p["prover_cost"]["elapsed_seconds"] for p in rows]
                            ),
                            complete_verifier_command_seconds=spread(
                                [p["verifier_cost"]["elapsed_seconds"] for p in rows]
                            ),
                            prover_worker_peak_rss_bytes=spread(
                                [p["prover_cost"]["max_rss_bytes"] for p in rows]
                            ),
                        )
                    )
    return report


class Campaign:
    def __init__(self, prepared, enrollment_pin, output, *, fixture=False, profile="mac"):
        self.plan, self.corpus = comparison.documents()
        if profile == "hf":
            candidate = parse_json(
                read_regular(ROOT / "configs/circle-classifiers/hf-plan.json", 65536).decode()
            )
            for key in ("case_ids", "repetitions", "capacity_bytes", "circle", "gnark"):
                if candidate[key] != self.plan[key]:
                    raise ValueError("HF profile changes the frozen relation or repetitions")
            self.plan = candidate
        expected_host = ("Darwin", "arm64") if profile == "mac" else ("Linux", "x86_64")
        if (platform.system(), platform.machine()) != expected_host:
            raise ValueError("campaign host differs from selected frozen profile")
        if shutil.disk_usage(ROOT).free < self.plan["limits"]["min_free_storage_bytes"]:
            raise MemoryError("free disk space below frozen 8 GiB boundary; no run started")
        self.exported, self.originals, self.old_policy, self.frozen_circuits, _ = (
            comparison.admitted(prepared, enrollment_pin)
        )
        self.prepared = prepared
        self.linux = profile == "hf"
        self.fixture_mode = fixture
        self.output = output.resolve()
        if not self.output.is_relative_to(ROOT / "runs"):
            raise ValueError(
                "keep benchmark keys and raw artifacts under the ignored runs directory"
            )
        self.output.mkdir(mode=0o700)
        input_root = self.output / "inputs"
        input_root.mkdir()
        self.requests = {}
        input_pins = {}
        for case in self.corpus["requests"]:
            opening, expected = comparison.request(prepared / "proofs", case["id"])
            if opening.prompt != case["prompt"]:
                raise ValueError("caller prompt differs from frozen comparison case")
            self.requests[case["id"]] = opening, expected
            raw = comparison.encoded(
                dict(
                    opening_cbor_hex=opening.encode().hex(),
                    expected_cbor_hex=expected.encode().hex(),
                )
            )
            name = case["id"] + "-request.json"
            write_new(input_root / name, raw)
            input_pins[name] = comparison.sha(raw)
        for kind, relative in (
            ("mlp", "mlp-training/seed-17/quantization.json"),
            ("encoder", "cnn-training/17/quantization.json"),
        ):
            raw = read_regular(prepared / relative, 65536)
            name = kind + "-quantization.json"
            write_new(input_root / name, raw)
            input_pins[name] = comparison.sha(raw)
        self.started = time.monotonic()
        lim = self.plan["limits"]
        self.budget = RunBudget(
            self.output,
            self.started + lim["campaign_seconds"],
            lim["command_seconds"],
            240,
            4 * lim["command_seconds"],
            4,
            lim["sampled_rss_stop_bytes"],
            lim["additional_storage_bytes"],
        )
        self.failure = None
        self.monitor_stop = threading.Event()
        self.sample_id = None
        self.peaks = {}
        self.costs = []
        self.samples = []
        self.preparations = {}
        self.boundary()
        old_root = ROOT / "scripts"
        script_names = (
            "benchmark_classifiers.py",
            "classifier_comparison.py",
            "trained_common_input.py",
            "common_input.py",
            "composed_input.py",
            "run_e2e.py",
            "run_trained_mlp.py",
            "run_contextual_proof.py",
            "contextual_cnn.py",
            "check_gnark_encoder.py",
            "check_gnark_input_scale.py",
            "circle_backend.py",
            "circle_classifiers.py",
            "circle_circuit.py",
            "circle_integer.py",
            "run_circle_classifiers.py",
            "check_circle_engine.py",
        )
        paths = [
            *sorted((ROOT / "src/hallmark").glob("*.py")),
            *(old_root / n for n in script_names),
            *sorted((ROOT / "research/probes/gnark").glob("*.go")),
            ROOT / "research/probes/gnark/go.mod",
            ROOT / "research/probes/gnark/go.sum",
            ROOT / "research/probes/py_ecc/verify.py",
            ROOT / "research/probes/py_ecc/requirements.txt",
            ROOT / "research/probes/circle/verify_gnark_one.py",
            ROOT / "research/probes/circle/materialize_worker.py",
            ROOT / "research/probes/circle/gnark-timing.patch",
            ROOT / "research/probes/circle/dependencies.json",
            ROOT / "uv.lock",
            ROOT / "configs/circle-classifiers/plan.json",
            ROOT / "configs/circle-classifiers/corpus.json",
        ]
        if self.linux:
            paths.append(ROOT / "configs/circle-classifiers/hf-plan.json")
        _, engine_sources = circle.source_identity()
        paths = sorted(set(paths) | {ROOT / p for p in engine_sources})
        self.sources = {str(p.relative_to(ROOT)): sha_file(p) for p in paths}
        self.source_sha = comparison.sha(comparison.encoded(self.sources))
        for p in paths:
            destination = self.output / "source" / p.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            write_new(destination, p.read_bytes())
        self.environment = dict(
            python=sys.version,
            host=platform.platform(),
            machine=platform.machine(),
            threads=4,
            packages={p: importlib.metadata.version(p) for p in ("numpy", "pydantic")},
            command=sys.argv,
            toolchain_cache="Installed tools/downloads reused; fresh object cache per workflow",
        )
        go = prepared / "toolchain/go/bin/go"
        go_version = subprocess.check_output([go, "version"], text=True, timeout=10).strip()
        if "go1.26.8" not in go_version:
            raise ValueError("frozen Go toolchain version mismatch")
        self.environment["tools"] = dict(
            python_sha256=sha_file(Path(sys.executable).resolve()),
            go_version=go_version,
            go_sha256=sha_file(go),
            rustc_version=subprocess.check_output(
                ["rustup", "run", "nightly-2025-07-14", "rustc", "--version", "--verbose"],
                text=True,
                timeout=10,
            ).strip(),
            cargo_version=subprocess.check_output(
                ["cargo", "+nightly-2025-07-14", "--version"], text=True, timeout=10
            ).strip(),
        )
        if self.linux:
            self.environment["hardware_software_report"] = dict(
                cpu_model=next(
                    (
                        line.split(":", 1)[1].strip()
                        for line in Path("/proc/cpuinfo").read_text().splitlines()
                        if line.startswith("model name")
                    ),
                    "unknown",
                ),
                online_cpus=os.cpu_count(),
                cgroup_memory_max=Path("/sys/fs/cgroup/memory.max").read_text().strip()
                if Path("/sys/fs/cgroup/memory.max").is_file()
                else "not available",
            )
        else:
            self.environment["hardware_software_report"] = {
                key: subprocess.check_output(
                    ["/usr/sbin/sysctl", "-n", key], text=True, timeout=10
                ).strip()
                for key in ("machdep.cpu.brand_string", "hw.memsize", "hw.ncpu")
            }
        self.environment_sha = comparison.sha(comparison.encoded(self.environment))
        json_new(
            self.output / "protocol.json",
            dict(
                schema_id="hallmark.classifier-backend-campaign/1",
                plan=self.plan,
                source_sha256=self.source_sha,
                sources=self.sources,
                environment=self.environment,
                environment_sha256=self.environment_sha,
                original_enrollment=enrollment_pin,
                frozen_input_pins=input_pins,
                protocol_commit=(ROOT / "SOURCE_COMMIT").read_text().strip()
                if (ROOT / "SOURCE_COMMIT").is_file()
                else subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10
                ).strip(),
                memory_sampling_seconds=0.25,
                storage_at_start=storage(self.output),
                benchmark_sample=not fixture,
                fixture_scope="Single rule AIR and measurement plumbing only" if fixture else None,
            ),
        )
        self.monitor = threading.Thread(target=self.monitor_memory, daemon=True)
        self.monitor.start()

    def boundary(self, *, inventory=True):
        if self.failure:
            raise RuntimeError(self.failure)
        if inventory:
            self.budget.inspect()
        elif time.monotonic() >= self.budget.deadline:
            raise TimeoutError("campaign deadline")
        if shutil.disk_usage(ROOT).free < self.plan["limits"]["min_free_storage_bytes"]:
            raise MemoryError("free disk space below frozen 8 GiB boundary")

    def monitor_memory(self):
        while not self.monitor_stop.wait(0.25):
            try:
                rows, owned = tree_processes(os.getpid())
                rss = sum(rows[p][1] for p in owned)
                key = self.sample_id or "campaign-admission"
                self.peaks[key] = max(self.peaks.get(key, 0), rss)
                if (
                    rss > self.budget.max_rss_bytes
                    or shutil.disk_usage(ROOT).free < self.plan["limits"]["min_free_storage_bytes"]
                ):
                    self.failure = "campaign process-tree memory or free-storage boundary exceeded"
                    for p in owned - {os.getpid()}:
                        if rows[p][0] == os.getpid():
                            try:
                                if os.getpgid(p) == p:
                                    os.killpg(p, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                    return
            except BaseException as error:
                self.failure = "campaign memory monitor failed: " + type(error).__name__
                return

    def inputs(self, work, inputs):
        started = time.perf_counter()
        for name, value in inputs.items():
            destination = work / name
            if isinstance(value, PinnedArtifact):
                if stream_regular(value.path, value.size) != {
                    "sha256": value.sha256,
                    "bytes": value.size,
                }:
                    raise ValueError("canonical input artifact pin mismatch")
                subprocess.run(
                    ["/bin/cp", "-c", str(value.path), str(destination)], check=True, timeout=60
                )
                if destination.stat().st_nlink != 1 or stream_regular(destination, value.size) != {
                    "sha256": value.sha256,
                    "bytes": value.size,
                }:
                    raise ValueError("cloned input artifact pin mismatch")
            else:
                write_new(destination, value)
        return time.perf_counter() - started

    def worker(self, work, binary, args, inputs, read_paths=()):
        self.boundary()
        if self.linux:
            from hallmark._gnark_linux_compile import invoke as linux_invoke

            staging = work.with_name(work.name + "-input-source")
            staging.mkdir()
            files = {}
            for name, value in inputs.items():
                if isinstance(value, PinnedArtifact):
                    ref = value
                else:
                    write_new(staging / name, value)
                    ref = PinnedArtifact(staging / name, comparison.sha(value), len(value))
                files[name] = dict(path=str(ref.path), sha256=ref.sha256, bytes=ref.size)
            manifest = comparison.encoded(
                dict(
                    schema_id="hallmark.classifier-worker-inputs/1",
                    binary=str(binary),
                    binary_sha256=sha_file(binary),
                    arguments=args,
                    files=files,
                )
            )
            cost = linux_invoke(
                [
                    sys.executable,
                    str(ROOT / "research/probes/circle/materialize_worker.py"),
                    "input-manifest.json",
                    comparison.sha(manifest),
                ],
                work,
                seconds=self.budget.case_seconds,
                max_rss=self.budget.max_rss_bytes,
                cutoff=self.budget.max_rss_bytes * 7 // 8,
                budget=self.budget,
                max_file=2 * 1024**3,
                inputs={"input-manifest.json": manifest},
            )
            materialized = (
                json.loads(read_regular(work / "materialization.json", 65536))["seconds"]
                if cost["exit_code"] == 0
                else None
            )
        else:
            work.mkdir()
            materialized = self.inputs(work, inputs)
            cost = invoke(
                binary,
                work,
                args,
                budget=self.budget,
                cpu_seconds=self.budget.cpu_seconds,
                max_file=2 * 1024**3,
                read_paths=read_paths,
            )
        self.costs.append(dict(work=str(work.relative_to(self.output)), **cost))
        self.boundary()
        if cost["exit_code"] != 0:
            raise ValueError("benchmark worker failed: " + work.name)
        references = {}
        for name, value in inputs.items():
            if isinstance(value, PinnedArtifact):
                if cost["files"][name] != dict(sha256=value.sha256, bytes=value.size):
                    raise ValueError("worker changed an admitted canonical input")
                references[name] = dict(
                    canonical_path=str(value.path), sha256=value.sha256, bytes=value.size
                )
        if references:
            json_new(work / "input-references.json", references)
            for name in references:
                (work / name).unlink()
        return cost, materialized

    def build_command(self, args, work, environment):
        # Successful compiler caches may contain hardlinks until their recorded cleanup.
        self.boundary(inventory=False)
        work.mkdir()
        json_new(work / "command.json", dict(argv=list(map(str, args)), environment=environment))
        started = time.monotonic()
        with (work / "stdout.txt").open("xb") as stdout, (work / "stderr.txt").open("xb") as stderr:
            process = subprocess.Popen(
                list(map(str, args)),
                cwd=work,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                preexec_fn=lambda: limits(2 * 1024**3, self.budget.cpu_seconds),
            )
            try:
                while process.poll() is None:
                    if time.monotonic() - started > min(7200, self.budget.deadline - started):
                        self.failure = "compiler command timeout"
                    if self.failure:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        raise RuntimeError(self.failure)
                    time.sleep(0.25)
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                raise
        result = dict(
            argv=list(map(str, args)),
            elapsed_seconds=time.monotonic() - started,
            exit_code=process.returncode,
            stdout_sha256=sha_file(work / "stdout.txt"),
            stderr_sha256=sha_file(work / "stderr.txt"),
        )
        json_new(work / "cost.json", result)
        if process.returncode:
            raise ValueError("compiler failed; retained " + str(work))
        return result

    def build(self, backend, folder):
        destination = folder / "binaries"
        destination.mkdir()
        env = dict(
            PATH=os.environ["PATH"],
            LANG="C",
            TZ="UTC",
            HOME=os.environ["HOME"],
            OMP_NUM_THREADS="4",
            OPENBLAS_NUM_THREADS="4",
            VECLIB_MAXIMUM_THREADS="4",
            RAYON_NUM_THREADS="4",
        )
        for key in ("CARGO_HOME", "RUSTUP_HOME"):
            if os.environ.get(key):
                env[key] = os.environ[key]
        if backend == "circle":
            target = folder / "object-cache"
            env["CARGO_TARGET_DIR"] = str(target)
            cargo = shutil.which("cargo")
            if not cargo:
                raise ValueError("pinned Rust toolchain unavailable")
            manifest = ROOT / "research/probes/circle/Cargo.toml"
            costs = []
            for name, features in (
                ("circle-prove", ["--features", "prover"]),
                ("circle-verify", ["--no-default-features"]),
            ):
                costs.append(
                    self.build_command(
                        [
                            cargo,
                            "+nightly-2025-07-14",
                            "build",
                            "--manifest-path",
                            manifest,
                            "--offline",
                            "--locked",
                            "--release",
                            *features,
                            "--bin",
                            name,
                            "-j",
                            "4",
                        ],
                        folder / ("build-" + name),
                        env,
                    )
                )
                shutil.copyfile(target / "release" / name, destination / name)
                (destination / name).chmod(0o700)
        else:
            source = folder / "gnark-source"
            source.mkdir()
            for path in (ROOT / "research/probes/gnark").iterdir():
                if path.suffix == ".go" or path.name in ("go.mod", "go.sum"):
                    shutil.copyfile(path, source / path.name)
            patch = ROOT / self.plan["gnark"]["timing_overlay"]
            if sha_file(patch) != self.plan["gnark"]["timing_overlay_sha256"]:
                raise ValueError("gnark observational overlay pin mismatch")
            prefix = str(source.relative_to(ROOT))
            subprocess.run(
                ["git", "apply", "--check", "--directory", prefix, str(patch)],
                cwd=ROOT,
                check=True,
                timeout=10,
            )
            subprocess.run(
                ["git", "apply", "--directory", prefix, str(patch)],
                cwd=ROOT,
                check=True,
                timeout=10,
            )
            go = self.prepared / "toolchain/go/bin/go"
            target = folder / "object-cache"
            env |= dict(
                GOROOT=str(go.parent.parent),
                GOPATH=str(self.prepared / "gopath"),
                GOMODCACHE=str(self.prepared / "gomodcache"),
                GOCACHE=str(target),
                GOPROXY="off",
                GOSUMDB="off",
                GOTOOLCHAIN="local",
                GOTELEMETRY="off",
                CGO_ENABLED="0",
                GOFLAGS="-p=1",
                GOMAXPROCS="4",
                GOMEMLIMIT="1GiB",
            )
            # Build from the copied module while retaining the compiler logs outside its source.
            costs = [
                self.build_command(
                    [
                        go,
                        "build",
                        "-C",
                        source,
                        "-trimpath",
                        "-buildvcs=false",
                        "-mod=readonly",
                        "-o",
                        destination / "gnark",
                        ".",
                    ],
                    folder / "build-gnark",
                    env,
                )
            ]
            (destination / "gnark").chmod(0o700)
            json_new(
                folder / "overlay-source-pins.json",
                {p.name: sha_file(p) for p in source.iterdir() if p.is_file()},
            )
        cache = storage(target)
        binaries = {
            p.name: dict(sha256=sha_file(p), bytes=p.stat().st_size) for p in destination.iterdir()
        }
        json_new(
            folder / "compiler-artifacts.json",
            dict(
                binaries=binaries,
                derived_object_cache_before_cleanup=cache,
                cleanup="Successful object cache only; source/binary/logs and failures retained",
            ),
        )
        shutil.rmtree(target)
        self.boundary()
        return destination, costs

    def prepare(self, backend, folder):
        binaries, compile_costs = self.build(backend, folder)
        native_open, native_expected = self.requests["allow"]
        rows = common.evaluate(self.originals, self.old_policy, native_open, native_expected)
        engines, keys, pins, models, artifacts, stages = {}, {}, {}, {}, {}, []
        for kind, row in zip(circle.KINDS, rows, strict=True):
            work = folder / ("setup-" + kind)
            if backend == "circle":
                started = time.perf_counter()
                circuit, trace = circle.compile_case(
                    kind, row, native_open.prompt.encode(), self.exported
                )
                trace_parity(kind, trace, row)
                program = encode(circuit.program())
                build_seconds = time.perf_counter() - started
                del circuit, trace
                cost, _ = self.worker(
                    work,
                    binaries / "circle-prove",
                    ["enroll", "program.json", "enrollment.json"],
                    {"program.json": program},
                )
                engines[kind] = read_regular(work / "enrollment.json", 65536)
                if self.linux:
                    reference = read_regular(
                        self.prepared / "circle-reference" / (kind + ".json"), 65536
                    )
                    if engines[kind] != reference:
                        raise ValueError("Linux enrollment differs from the caller's Mac root")
                artifacts[kind] = {
                    "program.json": PinnedArtifact(
                        work / "program.json", comparison.sha(program), len(program)
                    )
                }
                stage = json.loads(read_regular(work / "stderr.txt", 65536))
                stages.append(
                    dict(
                        kind=kind,
                        program_construction_seconds=build_seconds,
                        preprocessing=cost,
                        engine_timing=stage,
                        separate_weight_commitment_seconds=None,
                        separate_weight_commitment_reason=(
                            "Model constants and wiring share one preprocessing commitment"
                        ),
                    )
                )
            else:
                models[kind] = (
                    {}
                    if kind == "rule"
                    else {"model.json": comparison.encoded(self.exported[kind]["model"])}
                )
                cost, _ = self.worker(
                    work, binaries / "gnark", [PREFIX[kind] + "setup", "96"], models[kind]
                )
                pins[kind] = cost["files"]["circuit.r1cs"]["sha256"]
                if pins[kind] != self.frozen_circuits[kind]:
                    raise ValueError("timing overlay changed the frozen R1CS: " + kind)
                keys[kind] = read_regular(work / "vk.bin", 65536)
                artifacts[kind] = {
                    n: PinnedArtifact(
                        work / n, cost["files"][n]["sha256"], cost["files"][n]["bytes"]
                    )
                    for n in ("circuit.r1cs", "pk.bin")
                }
                stages.append(
                    dict(
                        kind=kind,
                        setup=cost,
                        engine_timing=json.loads(read_regular(work / "stderr.txt", 65536)),
                        separate_weight_commitment_seconds=None,
                        separate_weight_commitment_reason=(
                            "Fixed weights are embedded in R1CS compilation"
                        ),
                    )
                )
        enrollment = (
            circle.enroll(engines, self.originals)
            if backend == "circle"
            else comparison.encoded(common.enroll(self.exported, keys, pins))
        )
        pin = comparison.sha(enrollment)
        write_new(folder / "caller-enrollment.json", enrollment)
        json_new(folder / "caller-pin.json", dict(sha256=pin, before_proving=True))
        if backend == "circle":
            records, policy, _ = circle.resolve(enrollment, pin, self.originals, self.old_policy)
        else:
            records, policy = common.resolve(enrollment, pin, self.exported, pins)
        return dict(
            folder=folder,
            binaries=binaries,
            compile_costs=compile_costs,
            shared_stages=stages,
            engines=engines,
            artifacts=artifacts,
            models=models,
            records=records,
            policy=policy,
            enrollment=enrollment,
            pin=pin,
            circuits=pins,
        )

    def sample(self, backend, phase, repetition):
        name = f"{phase}-{repetition:02d}-{backend}"
        self.sample_id = name
        folder = self.output / name
        folder.mkdir()
        started = time.monotonic()
        prep = self.prepare(backend, folder) if phase == "fresh" else self.preparations[backend]
        if backend not in self.preparations:
            self.preparations[backend] = prep
        sample = dict(
            schema_id="hallmark.classifier-backend-sample/1",
            sample_id=name,
            backend=backend,
            phase=phase,
            repetition=repetition,
            status="running",
            preparation_reference=str(prep["folder"].relative_to(self.output)),
            source_sha256=self.source_sha,
            environment_sha256=self.environment_sha,
            shared_stages=dict(
                compile=prep["compile_costs"] if phase == "fresh" else [],
                setup=prep["shared_stages"] if phase == "fresh" else [],
                amortization_requests=3,
            ),
            cases=[],
            failures=[],
        )
        self.samples.append(sample)
        scorer = comparison.native_scorer(self.exported)
        verifier_python = self.prepared / "verifier-env/bin/python"
        python_prefix = Path(
            subprocess.check_output(
                [verifier_python, "-I", "-c", "import sys;print(sys.base_prefix)"],
                text=True,
                timeout=10,
            ).strip()
        )
        for case in self.corpus["requests"]:
            case_name = case["id"]
            opening, old_expected = self.requests[case_name]
            expected = circle.expected_request(old_expected, prep["policy"])
            start = time.perf_counter()
            scores = scorer(opening.prompt)
            native_seconds = time.perf_counter() - start
            start = time.perf_counter()
            rows = common.evaluate(prep["records"], prep["policy"], opening, expected)
            native_binding = time.perf_counter() - start
            if [r["public"][99] for r in rows] != case["verdicts"]:
                raise ValueError("frozen decision mismatch")
            request = dict(
                opening_cbor_hex=opening.encode().hex(), expected_cbor_hex=expected.encode().hex()
            )
            json_new(folder / (case_name + "-request.json"), request)
            result = dict(
                case_id=case_name,
                opening_sha256=comparison.sha(opening.encode()),
                expected_request_sha256=comparison.sha(expected.encode()),
                context=opening.context(expected).hex(),
                native_scores=scores,
                verdicts=case["verdicts"],
                native_inference_seconds=native_seconds,
                native_plus_binding_seconds=native_binding,
                caller_binding_seconds=None,
                proofs=[],
            )
            sample["cases"].append(result)
            proofs = []
            for kind, row in zip(circle.KINDS, rows, strict=True):
                start = time.perf_counter()
                if backend == "circle":
                    circuit, trace = circle.compile_case(
                        kind, row, opening.prompt.encode(), self.exported
                    )
                    trace_parity(kind, trace, row)
                    if (
                        comparison.sha(encode(circuit.program()))
                        != prep["artifacts"][kind]["program.json"].sha256
                    ):
                        raise ValueError("witness-dependent program")
                    witness = encode(circuit.witness())
                    public = encode([w.value for w in circuit.wires[: circuit.external]])
                    del circuit, trace
                    inputs = dict(
                        prep["artifacts"][kind],
                        **{
                            "enrollment.json": prep["engines"][kind],
                            "public.json": public,
                            "witness.json": witness,
                        },
                    )
                    args = [
                        "prove",
                        "program.json",
                        "enrollment.json",
                        "public.json",
                        "witness.json",
                        "proof.json",
                    ]
                    binary = prep["binaries"] / "circle-prove"
                    filename = "proof.json"
                else:
                    inputs = dict(
                        prep["models"][kind],
                        **prep["artifacts"][kind],
                        **{"assignment.txt": assignment(row, True)},
                    )
                    args = [PREFIX[kind] + "prove", "96"]
                    binary = prep["binaries"] / "gnark"
                    filename = "proof.bin"
                witness_seconds = time.perf_counter() - start
                work = folder / (case_name + "-prove-" + kind)
                cost, materialized = self.worker(work, binary, args, inputs)
                proof = read_regular(work / filename, 64 * 1024**2)
                proofs.append(proof)
                engine = json.loads(read_regular(work / "stderr.txt", 65536))
                cli = json.loads(read_regular(work / "stdout.txt", 65536))
                serialization = (
                    cli["serialize_write_seconds"]
                    if backend == "circle"
                    else engine["stages_seconds"]["proof_serialization"]
                )
                result["proofs"].append(
                    dict(
                        kind=kind,
                        program_identity=prep["records"][circle.KINDS.index(kind)]["program"]
                        .identity()
                        .hex(),
                        classifier_identity=bytes(row["public"][32:64]).hex(),
                        public=row["public"],
                        input_sha256=comparison.sha(comparison.encoded(row)),
                        witness_seconds=witness_seconds,
                        materialization_seconds=materialized,
                        prover_cost=cost,
                        worker_timing=dict(engine=engine, cli=cli),
                        serialization_seconds=serialization,
                        verifier_cost=None,
                        proof_bytes=len(proof),
                        proof_sha256=comparison.sha(proof),
                        encoding="canonical STWO JSON"
                        if backend == "circle"
                        else "gnark compressed binary",
                        compression="none",
                    )
                )
            if backend == "circle":
                bundle = dict(
                    schema_id="hallmark.circle-classifier-bundle/1",
                    proofs=[
                        dict(kind=k, public=r["public"], proof_hex=p.hex())
                        for k, r, p in zip(circle.KINDS, rows, proofs, strict=True)
                    ],
                )
                start = time.perf_counter()
                jobs = circle.check_bundle(
                    prep["enrollment"],
                    prep["pin"],
                    self.originals,
                    self.old_policy,
                    opening,
                    expected,
                    bundle,
                )
                result["caller_binding_seconds"] = time.perf_counter() - start
            else:
                bundle = common.bundle(
                    prep["records"], prep["policy"], opening, expected, rows, proofs
                )
                start = time.perf_counter()
                jobs = common.check_bundle(
                    prep["enrollment"],
                    prep["pin"],
                    self.exported,
                    prep["circuits"],
                    opening,
                    expected,
                    comparison.encoded(bundle),
                )
                result["caller_binding_seconds"] = time.perf_counter() - start
            json_new(folder / (case_name + "-bundle.json"), bundle)
            for kind, job, proof_result in zip(circle.KINDS, jobs, result["proofs"], strict=True):
                if backend == "circle":
                    binary = prep["binaries"] / "circle-verify"
                    args = ["enrollment.json", job["enrollment_pin"], "public.json", "proof.json"]
                    inputs = {
                        "enrollment.json": job["enrollment"],
                        "public.json": encode(job["public"]),
                        "proof.json": job["proof"],
                    }
                    reads = ()
                else:
                    binary = verifier_python
                    raw = comparison.encoded(job)
                    args = [
                        "-I",
                        "-B",
                        str(ROOT / "research/probes/circle/verify_gnark_one.py"),
                        "--job",
                        "job.json",
                        "--expected-job",
                        comparison.sha(raw),
                    ]
                    inputs = {"job.json": raw}
                    reads = (verifier_python.parent.parent, python_prefix, ROOT)
                work = folder / (case_name + "-verify-" + kind)
                cost, _ = self.worker(work, binary, args, inputs, reads)
                report = json.loads(read_regular(work / "stdout.txt", 65536))
                if (
                    report.get("status") != "passed"
                    or report.get("qualified_backend") is not False
                    or (
                        backend == "circle" and report.get("cryptographic_verification") is not True
                    )
                    or (backend == "gnark" and report.get("proofs_verified") != 1)
                ):
                    raise ValueError("fresh proof-only verifier rejected")
                proof_result["verifier_cost"] = cost
            print(name + ": verified " + case_name + " (three proofs)", flush=True)
        sample |= dict(
            status="passed",
            full_wall_seconds=time.monotonic() - started,
            sampled_process_tree_peak_rss_bytes=self.peaks.get(name, 0),
            storage=storage(folder),
        )
        json_new(folder / "sample.json", sample)
        with (self.output / "samples.jsonl").open("a") as stream:
            stream.write(json.dumps(sample, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        print(name + ": complete", flush=True)

    def fixture(self):
        """Compile both tools, check one frozen R1CS and freshly verify one proof per tool."""
        reports = []
        for backend in ("gnark", "circle"):
            self.sample_id = "fixture-" + backend
            folder = self.output / self.sample_id
            folder.mkdir()
            binaries, compile_costs = self.build(backend, folder)
            opening, expected = self.requests["allow"]
            row = common.evaluate(self.originals, self.old_policy, opening, expected)[0]
            if backend == "gnark":
                setup = folder / "setup-rule"
                setup_cost, _ = self.worker(
                    setup, binaries / "gnark", ["scaled-rule-setup", "96"], {}
                )
                if setup_cost["files"]["circuit.r1cs"]["sha256"] != self.frozen_circuits["rule"]:
                    raise ValueError("timing overlay changed frozen rule R1CS")
                keys = {k: r["key"] for k, r in zip(circle.KINDS, self.originals, strict=True)}
                keys["rule"] = read_regular(setup / "vk.bin", 65536)
                enrollment = comparison.encoded(
                    common.enroll(self.exported, keys, self.frozen_circuits)
                )
                records, policy = common.resolve(
                    enrollment, comparison.sha(enrollment), self.exported, self.frozen_circuits
                )
                expected = circle.expected_request(expected, policy)
                row = common.evaluate(records, policy, opening, expected)[0]
                inputs = {
                    n: PinnedArtifact(
                        setup / n, setup_cost["files"][n]["sha256"], setup_cost["files"][n]["bytes"]
                    )
                    for n in ("circuit.r1cs", "pk.bin")
                }
                inputs["assignment.txt"] = assignment(row, True)
                work = folder / "prove-rule"
                cost, _ = self.worker(work, binaries / "gnark", ["scaled-rule-prove", "96"], inputs)
                proof = read_regular(work / "proof.bin", 292)
                job = dict(
                    key_hex=keys["rule"].hex(),
                    expected_key_sha256=comparison.sha(keys["rule"]),
                    proof_hex=proof.hex(),
                    public=row["public"],
                )
                raw = comparison.encoded(job)
                python = self.prepared / "verifier-env/bin/python"
                prefix = Path(
                    subprocess.check_output(
                        [python, "-I", "-c", "import sys;print(sys.base_prefix)"],
                        text=True,
                        timeout=10,
                    ).strip()
                )
                checked, _ = self.worker(
                    folder / "verify-rule",
                    python,
                    [
                        "-I",
                        "-B",
                        str(ROOT / "research/probes/circle/verify_gnark_one.py"),
                        "--job",
                        "job.json",
                        "--expected-job",
                        comparison.sha(raw),
                    ],
                    {"job.json": raw},
                    (python.parent.parent, prefix, ROOT),
                )
            else:
                circuit, _ = circle.compile_case(
                    "rule", row, opening.prompt.encode(), self.exported
                )
                program, witness = encode(circuit.program()), encode(circuit.witness())
                public = encode([w.value for w in circuit.wires[: circuit.external]])
                del circuit
                setup = folder / "setup-rule"
                self.worker(
                    setup,
                    binaries / "circle-prove",
                    ["enroll", "program.json", "enrollment.json"],
                    {"program.json": program},
                )
                enrollment = read_regular(setup / "enrollment.json", 65536)
                work = folder / "prove-rule"
                cost, _ = self.worker(
                    work,
                    binaries / "circle-prove",
                    [
                        "prove",
                        "program.json",
                        "enrollment.json",
                        "public.json",
                        "witness.json",
                        "proof.json",
                    ],
                    {
                        "program.json": PinnedArtifact(
                            setup / "program.json", comparison.sha(program), len(program)
                        ),
                        "enrollment.json": enrollment,
                        "public.json": public,
                        "witness.json": witness,
                    },
                )
                proof = read_regular(work / "proof.json", 64 * 1024**2)
                checked, _ = self.worker(
                    folder / "verify-rule",
                    binaries / "circle-verify",
                    ["enrollment.json", comparison.sha(enrollment), "public.json", "proof.json"],
                    {"enrollment.json": enrollment, "public.json": public, "proof.json": proof},
                )
            report = json.loads(read_regular(folder / "verify-rule/stdout.txt", 65536))
            if report.get("status") != "passed" or report.get("qualified_backend") is not False:
                raise ValueError("fixture fresh verifier did not pass")
            reports.append(
                dict(
                    backend=backend,
                    compile=compile_costs,
                    prover=cost,
                    verifier=checked,
                    proof_sha256=comparison.sha(proof),
                )
            )
            print("Measurement fixture passed: " + backend, flush=True)
        result = dict(
            schema_id="hallmark.classifier-measurement-fixture/1",
            status="fixture-passed",
            backends=reports,
            benchmark_sample=False,
            scope="Single rule AIR only; no classifier-policy composition or repeated measurements",
            qualified_backend=False,
        )
        json_new(self.output / "result.json", result)
        return result

    def run(self):
        try:
            if self.fixture_mode:
                return self.fixture()
            for phase in ("fresh", "warm"):
                for repetition in range(self.plan["repetitions"][phase]):
                    for backend in (
                        ("gnark", "circle") if repetition % 2 == 0 else ("circle", "gnark")
                    ):
                        self.sample(backend, phase, repetition)
            if self.sources != {name: sha_file(ROOT / name) for name in self.sources}:
                raise ValueError("campaign source changed")
            self.boundary()
            report = summarize(self.samples, self.plan)
            result = dict(
                schema_id="hallmark.classifier-backend-campaign-result/1",
                status="passed",
                samples=len(self.samples),
                fresh_proofs=144,
                fresh_verifications=144,
                summary=report,
                elapsed_seconds=time.monotonic() - self.started,
                campaign_sampled_process_tree_peak_rss_bytes=max(self.peaks.values(), default=0),
                storage=storage(self.output),
                qualified_backend=False,
                hiding_claim=False,
                hardware_claim="not-accepted",
            )
            json_new(self.output / "result.json", result)
            return result
        except BaseException as error:
            json_new(
                self.output / "failure.json",
                dict(
                    error=str(error),
                    error_type=type(error).__name__,
                    samples=self.samples,
                    worker_costs=self.costs,
                    elapsed_seconds=time.monotonic() - self.started,
                    monitor_failure=self.failure,
                ),
            )
            raise
        finally:
            self.monitor_stop.set()
            self.monitor.join(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classifier-run", type=Path, required=True)
    parser.add_argument("--expected-enrollment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile", choices=("mac", "hf"), default="mac")
    parser.add_argument(
        "--fixture", action="store_true", help="single-rule measurement plumbing only"
    )
    args = parser.parse_args()
    result = Campaign(
        args.classifier_run.resolve(),
        args.expected_enrollment,
        args.output,
        fixture=args.fixture,
        profile=args.profile,
    ).run()
    print(json.dumps(result))
