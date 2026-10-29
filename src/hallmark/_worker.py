"""Bounded, sandboxed Mac proof workers with retained cost records."""

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
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

MAX_FILE = 16 * 1024 * 1024
MAX_OPEN_FILES = 4096
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


def stream_regular(path: Path, limit: int, *, destination: Path | None = None) -> dict[str, Any]:
    """Hash or copy bounded regular bytes; failed exclusive copies remain as evidence."""
    if type(limit) is not int or limit < 0:
        raise ValueError("invalid file limit")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise ValueError("invalid file")
        output = (
            os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb")
            if destination is not None
            else nullcontext(None)
        )
        hashed, size = hashlib.sha256(), 0
        with output as target:
            while chunk := source.read(min(1024**2, limit + 1 - size)):
                size += len(chunk)
                if size > limit:
                    raise ValueError("invalid file")
                hashed.update(chunk)
                if target is not None:
                    target.write(chunk)
            after = os.fstat(source.fileno())
            current = path.lstat()
            if (
                size != before.st_size
                or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or after.st_nlink != 1
                or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
            ):
                raise ValueError("changed file")
            if target is not None:
                target.flush()
                os.fsync(target.fileno())
        return {"sha256": hashed.hexdigest(), "bytes": size}


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


def limit_open_files() -> None:
    # Native download clients can raise this to an impractical close-fds scan range.
    cap = min(
        value
        for value in (MAX_OPEN_FILES, *resource.getrlimit(resource.RLIMIT_NOFILE))
        if value != resource.RLIM_INFINITY
    )
    resource.setrlimit(resource.RLIMIT_NOFILE, (cap, cap))


def limits(max_file: int = MAX_FILE, cpu_seconds: int = 40) -> None:
    limit_open_files()
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (max_file, max_file))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _rss_reader() -> Callable[[int], int]:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("this admitted monitor requires macOS arm64")
    proc_pidinfo = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True).proc_pidinfo
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
        ctypes.set_errno(0)
        if proc_pidinfo(pid, 4, 0, buffer, len(buffer)) != len(buffer):
            raise OSError(ctypes.get_errno(), "worker memory sample unavailable")
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
    read_paths: Sequence[Path] = (),
) -> dict[str, Any]:
    """Fixed environment and OS network/file restrictions; process-group timeout."""
    if budget is not None:
        budget.inspect()
        seconds = min(seconds, budget.case_seconds, budget.deadline - time.monotonic())
        if args and args[0].endswith("verify"):
            seconds = min(seconds, budget.verify_seconds)
        cpu_seconds = min(cpu_seconds, budget.cpu_seconds)
    profile = sandbox_profile(binary, work)
    if read_paths:
        profile += (
            "\n(allow file-read* file-map-executable "
            + " ".join("(subpath " + json.dumps(str(path)) + ")" for path in read_paths)
            + ")\n"
        )
    max_rss = budget.max_rss_bytes if budget else 16 * 1024**3
    cutoff = max_rss * 7 // 8
    resident_bytes = _rss_reader()
    write_new(work / "sandbox.sb", profile.encode())
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "TZ": "UTC",
        "TMPDIR": str(work),
    }
    command = ["/usr/bin/sandbox-exec", "-f", str(work / "sandbox.sb"), str(binary), *args]
    json_new(
        work / "plan.json",
        {
            "schema_id": "hallmark.worker-attempt/1",
            "argv": command,
            "environment": environment,
            "wall_limit_seconds": seconds,
            "cpu_limit_seconds": cpu_seconds,
            "per_file_limit_bytes": max_file,
            "max_open_files": MAX_OPEN_FILES,
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
    process_missing_sample = False
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
                    except OSError as error:
                        process_missing_sample = isinstance(error, ProcessLookupError)
                        # The worker may have exited between wait4 and proc_pidinfo.
                        time.sleep(0.01)
                        pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                        if pid:
                            break
                        memory_monitor_failed = True
                # shortcut: sampling permits growth between reads; retain the peak-RSS postcheck.
                if timed_out or memory_limit_exceeded or memory_monitor_failed:
                    _, status, usage = _stop_worker(process.pid)
                    # ESRCH can precede waitability during exit; only a normal exit resolves it.
                    if process_missing_sample and os.waitstatus_to_exitcode(status) >= 0:
                        memory_monitor_failed = False
                    break
                time.sleep(0.01)
            process.returncode = os.waitstatus_to_exitcode(status)
        except BaseException:
            _, status, _ = _stop_worker(process.pid)
            process.returncode = os.waitstatus_to_exitcode(status)
            raise
    result = {
        "schema_id": "hallmark.worker-cost/1",
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "memory_limit_exceeded": memory_limit_exceeded,
        "memory_monitor_failed": memory_monitor_failed,
        "memory_sample_process_missing": process_missing_sample,
        "sampled_peak_rss_bytes": sampled_peak_rss,
        "elapsed_seconds": time.monotonic() - start,
        "user_seconds": usage.ru_utime,
        "system_seconds": usage.ru_stime,
        "max_rss_bytes": usage.ru_maxrss,
        "files": {path.name: stream_regular(path, max_file) for path in sorted(work.iterdir())},
    }
    json_new(work / "cost.json", result)
    if budget is not None:
        budget.inspect(result)
    if memory_limit_exceeded or memory_monitor_failed or usage.ru_maxrss > max_rss:
        raise MemoryError("qualification worker memory budget")
    return result
