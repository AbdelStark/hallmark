"""Compare SASH and FlashProve on recorded runs, and re-time the FlashProve verifier here.

`make compare-provers FLASHPROVE_RUN=runs/flashprove-gpu-...` times `cp_verify` on the stored
small and full-size proofs and the fresh H200 proof from that run, then gathers every other figure
from checked-in evidence files, each with its source pointer. Nothing is proved again and no paid
compute starts. The two backends prove different statements on different models, so no row is a
like-for-like speed claim; see docs/PROVER-COMPARISON.md.
"""

import argparse
import json
import platform
import re
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from flashprove import PIN
from run_e2e import sha, write_json
from run_llm_e2e import require

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/evidence"
SASH_GPU = "llm-gpu-generated-constraints-2026-10-26.json"
FLASHPROVE = "flashprove-2026-11-03.json"
SASH_CUDA = ("result", "measurements", 1)
# name: (evidence file, JSON path)
RECORDED = {
    "sash_prove_session_cuda_seconds": (SASH_GPU, (*SASH_CUDA, "prove_seconds")),
    "sash_prove_session_simd_seconds": (SASH_GPU, ("result", "measurements", 0, "prove_seconds")),
    "sash_segment_commands_cuda_seconds": (SASH_GPU, (*SASH_CUDA, "commands_seconds")),
    "sash_proof_bytes": (SASH_GPU, (*SASH_CUDA, "serialized_proof_bytes")),
    "sash_proof_archive_gzip_bytes": (SASH_GPU, ("proof_archive_bytes",)),
    "sash_prover_host_rss_bytes": (SASH_GPU, (*SASH_CUDA, "sampled_peak_rss_bytes")),
    "sash_prover_gpu_mib": (SASH_GPU, (*SASH_CUDA, "gpu_peak_memory_mib")),
    "sash_prove_job_bound_micro_usd": (
        SASH_GPU,
        ("phase_receipts", "prove", "compute_bound_micro_usd"),
    ),
    "sash_build_seconds": (
        SASH_GPU,
        ("failed_attempts", 0, "phase_receipts", "build", "running_seconds"),
    ),
    "sash_mac_verify_seconds": (SASH_GPU, ("native_verification", "cases", 0, "seconds")),
    "sash_mac_verify_rss_bytes": (
        SASH_GPU,
        ("native_verification", "verification_cost", "sampled_process_group_peak_rss_bytes"),
    ),
    "sash_linux_verify_seconds": (SASH_GPU, ("cpu_proof_only_verification", "cases", 0, "seconds")),
    "flashprove_example_wall_seconds": (FLASHPROVE, ("gpu_prove", "example_wall_seconds")),
    "flashprove_example_rss_kib": (FLASHPROVE, ("gpu_prove", "example_max_rss_kib")),
    "flashprove_proof_bytes": (FLASHPROVE, ("gpu_prove", "proof_bytes")),
    "flashprove_checked_tokens": (FLASHPROVE, ("gpu_prove", "checked_tokens")),
    "flashprove_prove_job_bound_micro_usd": (FLASHPROVE, ("gpu_prove", "compute_bound_micro_usd")),
    "flashprove_build_seconds": (FLASHPROVE, ("gpu_build", "running_seconds")),
}
# The TinyLlama case: 8 answer tokens through EOS in one 32-position block (docs/LLM-PROOF.md).
SASH_CHECKED_TOKENS = 8


def lookup(value, path):
    for key in path:
        value = value[key]
    return value


def recorded():
    files = {name: json.loads((EVIDENCE / name).read_text()) for name in (SASH_GPU, FLASHPROVE)}
    return {
        name: dict(
            value=lookup(files[file], path),
            source=f"research/evidence/{file}#{'.'.join(map(str, path))}",
        )
        for name, (file, path) in RECORDED.items()
    }


def max_rss_bytes(stderr):
    """Peak RSS from /usr/bin/time: -l on macOS prints bytes, -v on Linux prints KiB."""
    if found := re.search(r"(\d+)\s+maximum resident set size", stderr):
        return int(found[1])
    found = re.search(r"Maximum resident set size \(kbytes\): (\d+)", stderr)
    require(found, "no peak RSS in /usr/bin/time output")
    return int(found[1]) * 1024


def time_verifier(verifier, case, commitment_id, repeats):
    flag = "-l" if platform.system() == "Darwin" else "-v"
    args = ["/usr/bin/time", flag, verifier, case / "config", case / "ivk"]
    args += [case / "example.req", case / "example.y", case / "example.proof", "-id", commitment_id]
    rows = []
    for _ in range(repeats):
        started = time.monotonic()
        done = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=600)
        seconds = time.monotonic() - started
        last = (done.stdout.strip().splitlines() or [""])[-1]
        require(done.returncode == 0 and last == "YES", f"{case} was not accepted: {last}")
        rows.append(dict(seconds=seconds, max_rss_bytes=max_rss_bytes(done.stderr)))
    times = [r["seconds"] for r in rows]
    return dict(
        runs=rows,
        median_seconds=statistics.median(times),
        min_seconds=min(times),
        max_seconds=max(times),
        max_rss_bytes=max(r["max_rss_bytes"] for r in rows),
        proof_bytes=(case / "example.proof").stat().st_size,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flashprove-run", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=5)
    opts = parser.parse_args()
    run = opts.flashprove_run.resolve()
    fresh = json.loads((run / "result.json").read_text())
    require(fresh.get("passed") is True, f"{run} is not a passed FlashProve GPU run")
    verifier = run / "local/bin/cp_verify"
    examples = run / "local/src" / f"FlashProve-{PIN['revision']}" / "examples"
    cases = {
        "accepted-proof": (examples / "accepted-proof", PIN["examples"]["accepted-proof"]),
        "full-size": (examples / "full-size", PIN["examples"]["full-size"]),
        "fresh-h200": (run / "prove/retained/case", dict(commitment_id=fresh["commitment_id"])),
    }
    output = Path(tempfile.mkdtemp(prefix="prover-comparison-", dir=ROOT / "runs"))
    print("Outputs: " + str(output), flush=True)
    timings = {}
    for name, (case, pin) in cases.items():
        timings[name] = time_verifier(verifier, case, pin["commitment_id"], opts.repeats)
        print(name, f"{timings[name]['median_seconds']:.3f} s median", flush=True)
    numbers = recorded()
    value = {k: v["value"] for k, v in numbers.items()}
    fp_tokens = value["flashprove_checked_tokens"]
    result = dict(
        schema_id="hallmark.prover-comparison/1",
        flashprove_run=str(run.relative_to(ROOT)),
        host=dict(
            system=platform.system(),
            machine=platform.machine(),
            cpu=subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
            ).stdout.strip()
            or platform.processor(),
        ),
        flashprove_verifier=dict(
            sha256=sha(verifier),
            threads="cp_verify default (no -j)",
            repeats=opts.repeats,
            cases=timings,
        ),
        recorded=numbers,
        derived=dict(
            sash_proof_bytes_per_checked_token=value["sash_proof_bytes"] / SASH_CHECKED_TOKENS,
            flashprove_proof_bytes_per_checked_token=value["flashprove_proof_bytes"] / fp_tokens,
            sash_checked_tokens=SASH_CHECKED_TOKENS,
        ),
        like_for_like=False,
    )
    write_json(output / "result.json", result)


if __name__ == "__main__":
    main()
