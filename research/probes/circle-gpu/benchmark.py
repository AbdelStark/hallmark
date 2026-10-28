"""Frozen classifier cases, stock CPU / CUDA proving, fresh stock verification."""

import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import time
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def run(args, folder, deadline):
    folder.mkdir()
    started = time.monotonic()
    peak = 0
    failure = None

    with (folder / "stdout.txt").open("xb") as out, (folder / "stderr.txt").open("xb") as err:
        child = subprocess.Popen(
            list(map(str, args)), stdout=out, stderr=err, start_new_session=True
        )
        try:
            next_sample = started
            while child.poll() is None:
                status = Path(f"/proc/{child.pid}/status")
                try:
                    if time.monotonic() >= next_sample:
                        next_sample += 0.05
                        for line in status.read_text().splitlines():
                            if line.startswith(("VmHWM:", "VmRSS:")):
                                peak = max(peak, int(line.split()[1]) * 1024)
                except FileNotFoundError:
                    pass
                if time.monotonic() > min(deadline, started + 300) or peak > 180 * 1024**3:
                    raise TimeoutError("classifier command resource limit")
                time.sleep(0.002)
        except BaseException as exc:
            failure = exc
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    result = dict(
        seconds=time.monotonic() - started,
        exit_code=child.returncode,
        sampled_peak_rss_bytes=peak,
        sample_period_seconds=0.05,
        failure_type=type(failure).__name__ if failure else None,
    )
    write(folder / "cost.json", result)
    if failure:
        raise failure
    return result


def verify(binary, case, proof, folder, deadline, public=None):
    cost = run(
        [
            binary,
            case / "enrollment.json",
            sha(case / "enrollment.json"),
            public or case / "public.json",
            proof,
        ],
        folder,
        deadline,
    )
    return cost


def timings(folder):
    rows = []
    for name in ("stdout.txt", "stderr.txt"):
        for line in (folder / name).read_text().splitlines():
            if line.startswith("{"):
                rows.append(json.loads(line))
    return rows


def campaign(root):
    # CUDA reserves a large virtual address range; sampled RSS controls host memory.
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024**3,) * 2)
    out = root / "output"
    out.mkdir()
    work = Path("/work/classifier-measurement")
    work.mkdir(parents=True)
    protocol = json.loads((root / "protocol.json").read_text())
    for name, pin in protocol["inputs"].items():
        if sha(root / name) != pin:
            raise ValueError("worker input hash changed")
    # Inputs use an exact, caller-enrolled regular-member roster.
    from reference_files import check_archive

    inventory = json.loads((root / "inputs-inventory.json").read_text())
    check_archive(root / "inputs.tar.gz", inventory, work / "cases")
    cases = work / "cases"
    roster = json.loads((root / "cases.json").read_text())
    expected_roster = {
        f"{case}-{kind}"
        for case in ("allow", "rule-block", "cnn-block")
        for kind in ("rule", "mlp", "encoder")
    }
    if len(roster) != 9 or set(roster) != expected_roster:
        raise ValueError("incomplete classifier roster")
    os.environ.update(RAYON_NUM_THREADS="4", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    binaries = {name: root / ("circle-prove-" + name) for name in ("cpu", "cuda")}
    verifier = root / "circle-verify"
    device = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total,compute_cap",
            "--format=csv,noheader",
        ],
        text=True,
    ).strip()
    if len(device.splitlines()) != 1 or "H200" not in device:
        raise ValueError("expected one H200")
    cpu = next(
        line.split(":", 1)[1].strip()
        for line in Path("/proc/cpuinfo").read_text().splitlines()
        if line.startswith("model name")
    )
    write(
        out / "machine.json",
        dict(
            device=device,
            cpu_model=cpu,
            visible_logical_cpus=os.cpu_count(),
            guest_meminfo=Path("/proc/meminfo").read_text(),
            cgroup_cpu_max=Path("/sys/fs/cgroup/cpu.max").read_text()
            if Path("/sys/fs/cgroup/cpu.max").is_file()
            else None,
            cgroup_memory_max=Path("/sys/fs/cgroup/memory.max").read_text()
            if Path("/sys/fs/cgroup/memory.max").is_file()
            else None,
            platform=platform.platform(),
            python=platform.python_version(),
            threads=4,
            declared_memory_envelope_bytes=protocol["max_address_space_bytes"],
            memory_control="50-ms sampled RSS stop; no RLIMIT_AS",
            binaries={p.name: sha(p) for p in [*binaries.values(), verifier]},
        ),
    )
    deadline = time.monotonic() + 1600
    rows = []
    # Warm the driver and validate arithmetic before full classifier work.
    fixture = cases / "fixture"
    for backend, binary in binaries.items():
        proof = (out / (backend + "-fixture.json")).resolve()
        cost = run(
            [
                binary,
                "prove",
                fixture / "program.json",
                fixture / "enrollment.json",
                fixture / "public.json",
                fixture / "witness.json",
                proof,
            ],
            out / (backend + "-fixture-prove"),
            deadline,
        )
        if (
            cost["exit_code"]
            or verify(verifier, fixture, proof, out / (backend + "-fixture-verify"), deadline)[
                "exit_code"
            ]
        ):
            raise ValueError("real arithmetic fixture failed")
        bad = fixture / "bad-witness.json"
        badproof = out / (backend + "-bad-fixture.json")
        badcost = run(
            [
                binary,
                "prove",
                fixture / "program.json",
                fixture / "enrollment.json",
                fixture / "public.json",
                bad,
                badproof,
            ],
            out / (backend + "-bad-fixture-prove"),
            deadline,
        )
        if (
            badcost["exit_code"] == 0
            and verify(
                verifier, fixture, badproof, out / (backend + "-bad-fixture-verify"), deadline
            )["exit_code"]
            == 0
        ):
            raise ValueError("invalid witness accepted")
    with (out / "gpu.csv").open("xb") as telemetry:
        monitor = subprocess.Popen(
            [
                "nvidia-smi",
                "--query-gpu=timestamp,memory.used,utilization.gpu,power.draw",
                "--format=csv,noheader,nounits",
                "--loop-ms=100",
            ],
            stdout=telemetry,
            stderr=subprocess.DEVNULL,
        )
        try:
            for iteration in range(3):
                for backend in ("cpu", "cuda") if iteration % 2 == 0 else ("cuda", "cpu"):
                    for name in roster:
                        case = cases / name
                        folder = out / f"{iteration}-{backend}-{name}"
                        proof = out / (folder.name + ".json")
                        cost = run(
                            [
                                binaries[backend],
                                "prove",
                                case / "program.json",
                                case / "enrollment.json",
                                case / "public.json",
                                case / "witness.json",
                                proof,
                            ],
                            folder,
                            deadline,
                        )
                        if cost["exit_code"]:
                            raise ValueError("classifier prover failed")
                        v = verify(verifier, case, proof, out / (folder.name + "-verify"), deadline)
                        if v["exit_code"]:
                            raise ValueError("stock verifier rejected candidate")
                        times = timings(folder)
                        if backend == "cuda":
                            air = [
                                r
                                for r in times
                                if r.get("schema_id") == "hallmark.circle-cuda-air/1"
                            ]
                            if (
                                len(air) != 1
                                or air[0]["gpu_constraint_calls"] != 1
                                or air[0]["cpu_constraint_fallbacks"] != 0
                            ):
                                raise ValueError("device AIR execution not established")
                        negatives = []
                        for public in sorted(case.glob("reject-*.json")):
                            n = verify(
                                verifier,
                                case,
                                proof,
                                out / (folder.name + "-" + public.stem),
                                deadline,
                                public,
                            )
                            if n["exit_code"] == 0:
                                raise ValueError("mutated public input accepted")
                            negatives.append(n)
                        if len(negatives) != 7:
                            raise ValueError("public mutation roster changed")
                        row = dict(
                            iteration=iteration,
                            backend=backend,
                            case=name,
                            prove=cost,
                            verify=v,
                            timings=times,
                            negative_checks=negatives,
                            proof_bytes=proof.stat().st_size,
                            proof_sha256=sha(proof),
                            enrollment_sha256=sha(case / "enrollment.json"),
                            public_sha256=sha(case / "public.json"),
                        )
                        rows.append(row)
                        write(folder / "result.json", row)
                        print(
                            json.dumps(
                                {k: row[k] for k in ("iteration", "backend", "case", "proof_bytes")}
                            ),
                            flush=True,
                        )
        finally:
            monitor.terminate()
            monitor.wait(timeout=10)
    write(
        out / "result.json",
        dict(
            schema_id="hallmark.classifier-cuda-measurement/1",
            passed=True,
            measurements=rows,
            repetitions=3,
            proofs=54,
            public_mutation_rejections=378,
            preparation_reused=True,
            fixture_warmed=True,
            qualified_backend=False,
        ),
    )


if __name__ == "__main__":
    campaign(Path("/persist"))
