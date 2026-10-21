"""Bounded Linux x86-64 compilation diagnosis; never run setup or claim a proof."""

import argparse
import ctypes
import errno
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ._gnark_probe import (
    PinnedArtifact,
    RunBudget,
    _stop_worker,
    digest,
    json_new,
    limits,
    read_regular,
    stream_regular,
    write_new,
)

MAX_RSS = 28_000_000_000
RSS_CUTOFF = 26_000_000_000
MAX_FILE = 65536


def network_filter() -> list[tuple[int, int, int, int]]:
    """Reject other ABIs and socket creation, including io_uring's socket path."""
    instructions = [
        (0x20, 0, 0, 4),  # seccomp_data.arch
        (0x15, 1, 0, 0xC000003E),  # AUDIT_ARCH_X86_64
        (0x06, 0, 0, 0x80000000),  # KILL_PROCESS
        (0x20, 0, 0, 0),  # seccomp_data.nr
        (0x45, 0, 1, 0x40000000),  # reject x32 syscall numbers
        (0x06, 0, 0, 0x80000000),
    ]
    # ptrace/pidfd_getfd could acquire another process's existing socket.
    for number in (41, 53, 101, 425, 438):
        instructions.extend([(0x15, 0, 1, number), (0x06, 0, 0, 0x50000 | errno.EPERM)])
    return [*instructions, (0x06, 0, 0, 0x7FFF0000)]


def restrict_worker(cpu_seconds: int, max_file: int = MAX_FILE) -> None:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("Linux x86-64 required")
    limits(max_file, cpu_seconds)

    class Instruction(ctypes.Structure):
        _fields_ = [
            ("code", ctypes.c_ushort),
            ("jt", ctypes.c_ubyte),
            ("jf", ctypes.c_ubyte),
            ("k", ctypes.c_uint32),
        ]

    class Program(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Instruction))]

    rules = network_filter()
    instructions = (Instruction * len(rules))(*(Instruction(*rule) for rule in rules))
    program = Program(len(rules), instructions)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) or libc.prctl(22, 2, ctypes.byref(program), 0, 0):
        raise OSError(ctypes.get_errno(), "network restriction unavailable")


def resident_bytes(pid: int) -> int:
    fields = Path(f"/proc/{pid}/statm").read_text().split()
    if len(fields) != 7 or any(not field.isascii() or not field.isdecimal() for field in fields):
        raise ValueError("invalid process memory sample")
    return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")


def container_memory_limit(required: int = MAX_RSS) -> int:
    for name in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            raw = Path(name).read_text().strip()
        except FileNotFoundError:
            continue
        if not raw.isascii() or not raw.isdecimal() or int(raw) < required + 512 * 1024**2:
            raise ValueError("container memory unavailable or insufficient")
        return int(raw)
    raise ValueError("container memory limit unavailable")


def invoke(
    command: list[str],
    work: Path,
    *,
    seconds: float,
    max_rss: int = MAX_RSS,
    cutoff: int = RSS_CUTOFF,
    budget: RunBudget | None = None,
    max_file: int = MAX_FILE,
    inputs: dict[str, bytes | PinnedArtifact] | None = None,
) -> dict[str, Any]:
    max_seconds, allowed_rss, cpu_seconds, threads, soft_memory = 300, MAX_RSS, 1200, 4, 1024**3
    if budget is not None:
        if (
            not 0 < budget.case_seconds <= 7200
            or not 0 < budget.cpu_seconds <= 48 * 7200
            or not 1 <= budget.threads <= 48
            or not 0 < budget.max_rss_bytes <= 230_000_000_000
            or not 0 < budget.max_output_bytes <= 128 * 1024**3
        ):
            raise ValueError("invalid proof budget")
        budget.inspect()
        max_seconds, allowed_rss = budget.case_seconds, budget.max_rss_bytes
        seconds = min(seconds, budget.deadline - time.monotonic())
        cpu_seconds, threads = budget.cpu_seconds, budget.threads
        soft_memory = allowed_rss * 3 // 4
    if (
        not 0 < seconds <= max_seconds
        or not 0 < cutoff < max_rss <= allowed_rss
        or not 0 < max_file <= (48 * 1024**3 if budget else MAX_FILE)
    ):
        raise ValueError("invalid compile limits")
    for name, value in (inputs or {}).items():
        if not name or name in (".", "..") or Path(name).name != name or "/" in name:
            raise ValueError("invalid input filename")
        if isinstance(value, bytes) and len(value) > max_file:
            raise ValueError("input exceeds file bound")
    work.mkdir(mode=0o700)
    for name, value in (inputs or {}).items():
        if isinstance(value, PinnedArtifact):
            value.copy_to(work / name, max_file)
        else:
            write_new(work / name, value)
    if budget is not None:
        budget.inspect()
        seconds = min(seconds, budget.deadline - time.monotonic())
    environment = {
        "PATH": "/usr/bin:/bin",
        "GOMAXPROCS": str(threads),
        "GOMEMLIMIT": str(soft_memory) if budget else "1GiB",
        "LANG": "C",
        "TZ": "UTC",
        "TMPDIR": str(work),
    }
    json_new(
        work / "plan.json",
        {
            "argv": command,
            "environment": environment,
            "seconds": seconds,
            "max_rss_bytes": max_rss,
            "cutoff_bytes": cutoff,
            "per_file_limit_bytes": max_file,
            "cpu_limit_seconds": cpu_seconds,
            "seccomp_filter": network_filter(),
        },
    )
    start = time.monotonic()
    timed_out = memory_exceeded = monitor_failed = False
    peak = 0
    with (work / "stdout.txt").open("xb") as stdout, (work / "stderr.txt").open("xb") as stderr:
        child = subprocess.Popen(
            command,
            cwd=work,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            close_fds=True,
            start_new_session=True,
            preexec_fn=lambda: restrict_worker(cpu_seconds, max_file),
        )
        try:
            while True:
                pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    break
                timed_out = time.monotonic() - start > seconds
                try:
                    peak = max(peak, resident_bytes(child.pid))
                    memory_exceeded = peak >= cutoff
                except (OSError, ValueError) as error:
                    pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                    if pid:
                        monitor_failed = not isinstance(error, FileNotFoundError)
                        break
                    monitor_failed = True
                # shortcut: sampled RSS can overshoot; keep the kernel peak postcheck.
                if timed_out or memory_exceeded or monitor_failed:
                    _, status, usage = _stop_worker(child.pid)
                    break
                time.sleep(0.01)
            child.returncode = os.waitstatus_to_exitcode(status)
        except BaseException:
            _, status, _ = _stop_worker(child.pid)
            child.returncode = os.waitstatus_to_exitcode(status)
            raise
    result: dict[str, Any] = {
        "schema_id": "hallmark.linux-compile-cost/1",
        "exit_code": child.returncode,
        "elapsed_seconds": time.monotonic() - start,
        "user_seconds": usage.ru_utime,
        "system_seconds": usage.ru_stime,
        "max_rss_bytes": usage.ru_maxrss * 1024,
        "sampled_peak_rss_bytes": peak,
        "timed_out": timed_out,
        "memory_limit_exceeded": memory_exceeded,
        "memory_monitor_failed": monitor_failed,
        "files": {p.name: stream_regular(p, max_file) for p in sorted(work.iterdir())},
    }
    result["within_limits"] = not (
        timed_out
        or memory_exceeded
        or monitor_failed
        or result["max_rss_bytes"] > max_rss
        or usage.ru_utime + usage.ru_stime > cpu_seconds
    )
    json_new(work / "cost.json", result)
    if budget is not None:
        budget.inspect(result)
    print(json.dumps({"case": work.name, "cost": result}), flush=True)
    return result


def check(binary: Path, expected_binary: str, output: Path) -> dict[str, Any]:
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("Linux x86-64 required")
    raw = read_regular(binary, 128 * 1024**2)
    if digest(raw) != expected_binary:
        raise ValueError("binary pin mismatch")
    output = output.resolve()
    output.mkdir(mode=0o700)
    binary = output / "probe"
    write_new(binary, raw, 0o500)
    result: dict[str, Any] = {
        "schema_id": "hallmark.linux-compile-result/1",
        "status": "incomplete",
        "qualified_backend": False,
        "full_input_proof": False,
        "maximum_compile_reproduced": False,
        "binary_sha256": expected_binary,
        "cases": [],
    }
    start = time.monotonic()
    try:
        result["container_memory_limit_bytes"] = container_memory_limit()
        # Exercise the actual child filter before spending the maximum compile budget.
        code = (
            "import socket,errno\ntry: socket.socket()\n"
            "except OSError as e: assert e.errno==errno.EPERM\n"
            "else: raise AssertionError('network available')\n"
        )
        smoke = invoke([sys.executable, "-c", code], output / "network-smoke", seconds=5)
        if smoke["exit_code"] != 0 or not smoke["within_limits"]:
            raise ValueError("network restriction smoke failed")
        counts = []
        for name, capacity in [("small", 8), ("maximum", 32768), ("confirmation", 32768)]:
            seconds = min(30 if capacity == 8 else 300, 640 - (time.monotonic() - start))
            cost = invoke(
                [str(binary), "input-compile", str(capacity)], output / name, seconds=seconds
            )
            result["cases"].append({"name": name, "cost": cost})
            if cost["exit_code"] != 0 or not cost["within_limits"]:
                break
            report = json.loads(read_regular(output / name / "stdout.txt", MAX_FILE))
            count = report["constraints"]
            if (
                set(report) != {"schema_id", "status", "constraints", "elapsed_ns"}
                or report["schema_id"] != "hallmark.gnark-installation-probe/1"
                or report["status"] != "passed"
                or type(count) is not int
                or count <= 0
                or type(report["elapsed_ns"]) is not int
                or report["elapsed_ns"] < 0
            ):
                raise ValueError("invalid compile report")
            if capacity == 8 and count != 205547:
                raise ValueError("small circuit changed")
            counts.append(count)
        if len(counts) == 3:
            if counts[1] != counts[2]:
                raise ValueError("maximum compile count mismatch")
            result["maximum_compile_reproduced"] = True
            result["constraints"] = counts[1]
        if digest(read_regular(binary, 128 * 1024**2)) != expected_binary:
            raise ValueError("binary changed")
    except Exception as error:
        result["failure_type"] = type(error).__name__
    result["elapsed_seconds"] = time.monotonic() - start
    json_new(output / "result.json", result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--expected-binary", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = check(args.binary, args.expected_binary, args.output)
    raise SystemExit(0 if result["maximum_compile_reproduced"] else 3)
