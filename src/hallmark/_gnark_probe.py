"""Run the pinned cubic installation probe on macOS; never qualify a Hallmark backend."""

import argparse
import ctypes
import hashlib
import json
import os
import platform
import resource
import signal
import stat
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

MODULUS = 52435875175126190479447740508185965837690552500527637822603658699938581184513
MAX_FILE = 16 * 1024 * 1024
MAX_BINARY = 128 * 1024 * 1024
CASE_SECONDS = 45


@dataclass
class RunBudget:
    """One foreground run; sampled RSS and storage checks are not OS quotas."""

    root: Path
    deadline: float
    case_seconds: int
    verify_seconds: int
    cpu_seconds: int
    threads: int
    max_rss_bytes: int
    max_output_bytes: int

    def inspect(self, cost: dict[str, Any] | None = None) -> int:
        if time.monotonic() >= self.deadline:
            raise TimeoutError("qualification deadline")
        if cost is not None and (
            cost["timed_out"]
            or cost.get("memory_limit_exceeded", False)
            or cost.get("memory_monitor_failed", False)
            or cost["max_rss_bytes"] > self.max_rss_bytes
            or cost["user_seconds"] + cost["system_seconds"] > self.cpu_seconds
        ):
            raise MemoryError("qualification worker budget")
        total, count = 0, 0

        def failed_walk(error: OSError) -> NoReturn:
            raise error

        for directory, children, files in os.walk(
            self.root, followlinks=False, onerror=failed_walk
        ):
            for name in children + files:
                entry = (Path(directory) / name).lstat()
                count += 1
                if count > 20000 or not (
                    stat.S_ISDIR(entry.st_mode)
                    or (stat.S_ISREG(entry.st_mode) and entry.st_nlink == 1)
                ):
                    raise ValueError("unsafe output inventory")
                if stat.S_ISREG(entry.st_mode):
                    total += entry.st_size
                if total > self.max_output_bytes:
                    raise MemoryError("qualification storage budget")
        return total


def run_cli(check: Callable[..., dict[str, Any]], *, fixture: bool) -> int:
    class Parser(argparse.ArgumentParser):
        def error(self, message: str) -> NoReturn:
            raise ValueError("invalid arguments")

    parser = Parser(description="Pinned local proof probe; no backend qualification.")
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--output", required=True, type=Path)
    if fixture:
        parser.add_argument("--fixture", required=True, type=Path)
        parser.add_argument("--expected-fixture", required=True)
    try:
        args = parser.parse_args()
        result = check(**vars(args))
    except (Exception, KeyboardInterrupt):
        print(json.dumps({"status": "failed", "qualified_backend": False}))
        return 3
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}))
    return 0


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_regular(path: Path, limit: int) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("invalid file")
        raw = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
        if (
            len(raw) != before.st_size
            or len(raw) > limit
            or (
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        ):
            raise ValueError("changed file")
        return raw


def write_new(path: Path, raw: bytes, mode: int = 0o600) -> None:
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode), "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def json_new(path: Path, value: Any) -> None:
    write_new(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def sandbox_profile(binary: Path, work: Path) -> str:
    return f"""(version 1)
(deny default)
(import "dyld-support.sb")
(deny network*)
(allow process-exec signal)
(allow sysctl-read)
(allow file-read-metadata)
(allow file-read* file-map-executable
    (subpath "/System") (subpath "/usr/lib") (subpath "/private/var/db/dyld")
    (literal {json.dumps(str(binary))}))
(allow file-read* (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))
(allow file-read* file-write* (subpath {json.dumps(str(work))}))
"""


def limits(max_file: int = MAX_FILE, cpu_seconds: int = 40) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (max_file, max_file))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _rss_reader() -> Callable[[int], int]:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("this admitted monitor requires macOS arm64")
    proc_pidinfo = ctypes.CDLL("/usr/lib/libproc.dylib").proc_pidinfo
    proc_pidinfo.argtypes = [
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint64,
        ctypes.c_void_p,
        ctypes.c_int,
    ]
    proc_pidinfo.restype = ctypes.c_int
    # macOS proc_taskinfo: six uint64_t followed by twelve int32_t; resident_size is second.
    buffer = ctypes.create_string_buffer(96)

    def resident_bytes(pid: int) -> int:
        if proc_pidinfo(pid, 4, 0, buffer, len(buffer)) != len(buffer):
            raise OSError("worker memory sample unavailable")
        return ctypes.c_uint64.from_buffer(buffer, 8).value

    return resident_bytes


def _stop_worker(pid: int) -> tuple[int, int, resource.struct_rusage]:
    try:
        try:
            os.killpg(pid, signal.SIGKILL)
        except PermissionError:
            # macOS group signalling skips zombies; the unreaped child PID is still ours.
            os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    return os.wait4(pid, 0)


def invoke(
    binary: Path,
    work: Path,
    args: list[str],
    *,
    seconds: float = CASE_SECONDS,
    max_file: int = MAX_FILE,
    cpu_seconds: int = 40,
    budget: RunBudget | None = None,
) -> dict[str, Any]:
    """Fixed environment and OS network/file restrictions; process-group timeout."""
    if budget is not None:
        budget.inspect()
        seconds = min(seconds, budget.case_seconds, budget.deadline - time.monotonic())
        if args and args[0].endswith("verify"):
            seconds = min(seconds, budget.verify_seconds)
        cpu_seconds = min(cpu_seconds, budget.cpu_seconds)
    profile = sandbox_profile(binary, work)
    max_rss = budget.max_rss_bytes if budget else 16 * 1024**3
    cutoff = max_rss * 7 // 8
    resident_bytes = _rss_reader()
    write_new(work / "sandbox.sb", profile.encode())
    environment = {
        "PATH": "/usr/bin:/bin",
        "GOMAXPROCS": str(budget.threads if budget else 4),
        "GOMEMLIMIT": str(min(1024**3, budget.max_rss_bytes // 2)) if budget else "1GiB",
        "LANG": "C",
        "TZ": "UTC",
        "TMPDIR": str(work),
    }
    command = ["/usr/bin/sandbox-exec", "-f", str(work / "sandbox.sb"), str(binary), *args]
    json_new(
        work / "plan.json",
        {
            "schema_id": "hallmark.gnark-probe-attempt/1",
            "argv": command,
            "environment": environment,
            "wall_limit_seconds": seconds,
            "cpu_limit_seconds": cpu_seconds,
            "per_file_limit_bytes": max_file,
            "max_rss_bytes": max_rss,
            "memory_cutoff_bytes": cutoff,
            "rss_sample_interval_seconds": 0.01,
            "profile_sha256": digest(profile.encode()),
            "qualified_backend": False,
        },
    )
    start = time.monotonic()
    timed_out = False
    memory_limit_exceeded = memory_monitor_failed = False
    sampled_peak_rss = 0
    with (
        os.fdopen(
            os.open(work / "stdout.txt", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
        ) as stdout,
        os.fdopen(
            os.open(work / "stderr.txt", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb"
        ) as stderr,
    ):
        process = subprocess.Popen(
            command,
            cwd=work,
            env=environment,
            stdout=stdout,
            stderr=stderr,
            start_new_session=True,
            preexec_fn=lambda: limits(max_file, cpu_seconds),
        )
        try:
            while True:
                pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                if pid:
                    break
                if time.monotonic() - start > seconds:
                    timed_out = True
                else:
                    try:
                        sampled_peak_rss = max(sampled_peak_rss, resident_bytes(process.pid))
                        memory_limit_exceeded = sampled_peak_rss >= cutoff
                    except OSError:
                        # The worker may have exited between wait4 and proc_pidinfo.
                        time.sleep(0.01)
                        pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                        if pid:
                            break
                        memory_monitor_failed = True
                # shortcut: sampling permits growth between reads; retain the peak-RSS postcheck.
                if timed_out or memory_limit_exceeded or memory_monitor_failed:
                    _, status, usage = _stop_worker(process.pid)
                    break
                time.sleep(0.01)
            process.returncode = os.waitstatus_to_exitcode(status)
        except BaseException:
            _, status, _ = _stop_worker(process.pid)
            process.returncode = os.waitstatus_to_exitcode(status)
            raise
    result = {
        "schema_id": "hallmark.gnark-probe-cost/1",
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "memory_limit_exceeded": memory_limit_exceeded,
        "memory_monitor_failed": memory_monitor_failed,
        "sampled_peak_rss_bytes": sampled_peak_rss,
        "elapsed_seconds": time.monotonic() - start,
        "user_seconds": usage.ru_utime,
        "system_seconds": usage.ru_stime,
        "max_rss_bytes": usage.ru_maxrss,
        "files": {
            path.name: {
                "sha256": digest(read_regular(path, max_file)),
                "bytes": path.stat().st_size,
            }
            for path in sorted(work.iterdir())
        },
    }
    json_new(work / "cost.json", result)
    if budget is not None:
        budget.inspect(result)
    if memory_limit_exceeded or memory_monitor_failed or usage.ru_maxrss > max_rss:
        raise MemoryError("qualification worker memory budget")
    return result


def check(
    binary: Path, expected_binary: str, output: Path, *, budget: RunBudget | None = None
) -> dict[str, Any]:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("this admitted probe requires macOS arm64")
    raw_binary = read_regular(binary, MAX_BINARY)
    if len(expected_binary) != 64 or digest(raw_binary) != expected_binary:
        raise ValueError("binary identity mismatch")
    output.mkdir(mode=0o700)
    output = output.resolve()
    binary = output / "probe"
    write_new(binary, raw_binary, 0o500)
    dyld = read_regular(Path("/System/Library/Sandbox/Profiles/dyld-support.sb"), MAX_FILE)
    json_new(
        output / "protocol.json",
        {
            "schema_id": "hallmark.gnark-installation-protocol/1",
            "binary_sha256": expected_binary,
            "runner_sha256": digest(Path(__file__).read_bytes()),
            "dyld_support_sha256": digest(dyld),
            "platform": platform.platform(),
            "statement": "private uint8 x, public uint32 y; y=x^3+x+5",
            "proof_system": "Groth16",
            "curve": "BLS12-381",
            "setup": "fresh local research setup; no independent ceremony",
            "qualified_backend": False,
            "private_inputs": False,
            "limits": {
                "total_seconds": 900,
                "case_seconds": CASE_SECONDS,
                "go_threads": 4,
                "go_memory_soft_limit": "1GiB",
                "per_file_bytes": MAX_FILE,
            },
            "limitations": [
                "Live RSS sampling, post-exit checks and Go's soft limit are not OS memory quotas.",
                "No general hostile-worker memory or disk quota claim.",
                "No Hallmark statement, full encoder, independent verifier or trusted setup claim.",
            ],
        },
    )
    started = time.monotonic()
    cases: list[dict[str, Any]] = []

    def case(
        name: str,
        args: list[str],
        inputs: dict[str, bytes],
        outputs: Sequence[str],
        expected_exit: int = 0,
    ) -> dict[str, bytes]:
        if time.monotonic() - started > 900 - CASE_SECONDS:
            raise TimeoutError("probe budget exhausted")
        work = output / name
        work.mkdir(mode=0o700)
        for filename, raw in inputs.items():
            write_new(work / filename, raw)
        result = invoke(binary, work, args, budget=budget)
        cases.append({"name": name, **result})
        expected_names = {*inputs, *outputs, "sandbox.sb", "plan.json", "stdout.txt", "stderr.txt"}
        if (
            result["exit_code"] != expected_exit
            or result["timed_out"]
            or set(result["files"]) != expected_names
            or result["max_rss_bytes"] > 16 * 1024**3
            or result["user_seconds"] + result["system_seconds"] > 40
        ):
            raise ValueError("probe process or inventory failed")
        result_doc = json.loads(read_regular(work / "stdout.txt", 4096))
        if (
            set(result_doc) != {"schema_id", "status", "constraints", "elapsed_ns"}
            or result_doc["schema_id"] != "hallmark.gnark-installation-probe/1"
            or result_doc["status"] != ("passed" if expected_exit == 0 else "failed")
            or type(result_doc["constraints"]) is not int
            or result_doc["constraints"] < 0
            or type(result_doc["elapsed_ns"]) is not int
            or result_doc["elapsed_ns"] < 0
        ):
            raise ValueError("invalid probe result")
        return {name: read_regular(work / name, MAX_FILE) for name in outputs}

    try:
        setup = case("setup", ["setup"], {}, ["circuit.r1cs", "pk.bin", "vk.bin"])
        key_pin = digest(setup["vk.bin"])
        proving = {name: setup[name] for name in ("circuit.r1cs", "pk.bin")}
        proof = case("prove", ["prove", "3", "35"], proving, ["proof.bin"])
        verifier = {"vk.bin": setup["vk.bin"], "proof.bin": proof["proof.bin"]}
        case("verify", ["verify", "35"], verifier, [])
        case("changed-input", ["verify", "36"], verifier, [], 1)
        case("wrong-witness", ["prove", "3", "34"], proving, [], 1)
        case("out-of-range-witness", ["prove", "256", "35"], proving, [], 1)
        case("field-alias", ["verify", str(MODULUS + 35)], verifier, [], 1)
        case("noncanonical-integer", ["verify", "035"], verifier, [], 1)
        altered = bytes([proof["proof.bin"][0] ^ 1]) + proof["proof.bin"][1:]
        case("changed-proof", ["verify", "35"], verifier | {"proof.bin": altered}, [], 1)
        case(
            "trailing-proof",
            ["verify", "35"],
            verifier | {"proof.bin": proof["proof.bin"] + b"\0"},
            [],
            1,
        )
        other_setup = case("other-setup", ["setup"], {}, ["circuit.r1cs", "pk.bin", "vk.bin"])
        if digest(other_setup["vk.bin"]) == key_pin:
            raise ValueError("independent random setups unexpectedly agree")
        case("wrong-key", ["verify", "35"], verifier | {"vk.bin": other_setup["vk.bin"]}, [], 1)
        repeated = case("prove-again", ["prove", "3", "35"], proving, ["proof.bin"])
        if repeated == proof:
            raise ValueError("repeated randomized proof unexpectedly agrees")
        case("verify-again", ["verify", "35"], verifier | repeated, [])
        for x in (0, 255):
            y = x**3 + x + 5
            boundary = case(f"prove-{x}", ["prove", str(x), str(y)], proving, ["proof.bin"])
            case(f"verify-{x}", ["verify", str(y)], verifier | boundary, [])
        report = {
            "schema_id": "hallmark.gnark-installation-result/1",
            "status": "passed",
            "qualified_backend": False,
            "binary_sha256": expected_binary,
            "setup_vk_sha256": key_pin,
            "circuit_sha256": digest(setup["circuit.r1cs"]),
            "proof_sha256": digest(proof["proof.bin"]),
            "proof_bytes": len(proof["proof.bin"]),
            "cases": cases,
            "elapsed_seconds": time.monotonic() - started,
        }
        json_new(output / "result.json", report)
        return report
    except BaseException:
        json_new(
            output / "failure.json",
            {"schema_id": "hallmark.gnark-installation-failure/1", "cases": cases},
        )
        raise
