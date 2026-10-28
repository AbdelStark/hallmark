"""Time the unchanged default classifier controller; do not change its proof relation."""

import platform
import subprocess
import tempfile
import time
from functools import wraps
from pathlib import Path
from unittest.mock import patch

import run_circle_classifiers
import run_circle_e2e
import run_e2e

ROOT = Path(__file__).resolve().parents[1]


def measured(name, function, events):
    @wraps(function)
    def call(*args, **kwargs):
        started = time.perf_counter()
        event = dict(stage=name(*args, **kwargs) if callable(name) else name, status="failed")
        try:
            result = function(*args, **kwargs)
            event["status"] = "passed"
            return result
        finally:
            event["seconds"] = time.perf_counter() - started
            events.append(event)

    return call


def run():
    (ROOT / "runs").mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix="reference-timing-", dir=ROOT / "runs"))
    events = []
    protocol = dict(
        schema_id="hallmark.reference-timing-plan/1",
        timing="perf_counter around unchanged synchronous controller calls; nested timers overlap",
        controller_source=run_e2e.source_pins(),
        host=platform.platform(),
        machine=subprocess.check_output(
            ["sysctl", "machdep.cpu.brand_string", "hw.memsize", "hw.ncpu"], text=True
        ).splitlines(),
        frozen_models=run_e2e.EXPORTS,
        cloud_jobs=0,
    )
    run_e2e.write_json(output / "protocol.json", protocol)
    print(f"Timing evidence: {output}", flush=True)
    started = time.perf_counter()
    try:
        with (
            patch.object(
                run_e2e,
                "command",
                measured(lambda args, path, *a: path.stem, run_e2e.command, events),
            ),
            patch.object(
                run_circle_classifiers,
                "run",
                measured("classifier-proof-campaign", run_circle_classifiers.run, events),
            ),
        ):
            result = run_circle_e2e.run()
        run_e2e.write_json(
            output / "result.json",
            dict(
                schema_id="hallmark.reference-timing-result/1",
                status="passed",
                classifier_run=str(result.relative_to(ROOT)),
                events=events,
                seconds=time.perf_counter() - started,
            ),
        )
    finally:
        run_e2e.write_json(output / "events.json", events)
    print(f"Timing result: {output / 'result.json'}", flush=True)


if __name__ == "__main__":
    run()
