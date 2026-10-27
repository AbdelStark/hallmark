import sys
import time

import pytest

from hallmark_demo import engine
from hallmark_demo.catalog import Stage, Workflow


@pytest.fixture
def workflow():
    return Workflow(
        "fixture",
        "Process fixture",
        "Controller test",
        "Test only",
        "No proof claim",
        "seconds",
        0,
        None,
        (),
        (Stage("prepare", "Prepare", ("prepare",)), Stage("prove", "Prove", ("prove",))),
        "fixture.result/1",
        "docs/DEMO.md",
        False,
    )


@pytest.fixture
def root(tmp_path):
    (tmp_path / "runs").mkdir()
    return tmp_path


@pytest.fixture
def runner(root, workflow, monkeypatch):
    script = root / "fixture.py"
    script.write_text(
        """import json,sys,time
from pathlib import Path
p=Path.cwd()/'runs/output'
p.mkdir(exist_ok=True)
print(f'Evidence: {p}',flush=True)
print('Running prepare',flush=True)
print('hf_testsecret123456789',flush=True)
time.sleep(.2)
print('Running prove',flush=True)
time.sleep(.2)
report={'schema_id':'fixture.result/1','status':'passed','proofs_verified':0}
(p/'result.json').write_text(json.dumps(report))
"""
    )
    monkeypatch.setattr(
        engine,
        "plan",
        lambda *a: dict(command=[sys.executable, str(script)], paid=False, ceiling="0"),
    )
    monkeypatch.setattr(
        engine, "preflight", lambda *a: [dict(label="fixture", ok=True, detail="local")]
    )
    manager = engine.RunManager(root, workflows={"fixture": workflow})
    yield manager, script
    manager.close(grace=2)


def wait(manager, key, predicate=lambda run: run["status"] not in engine.ACTIVE, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = manager.snapshot(key)
        if predicate(run):
            return run
        time.sleep(0.05)
    raise AssertionError(manager.snapshot(key))
