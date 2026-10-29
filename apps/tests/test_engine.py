import fcntl
import json
import sys
import time
from pathlib import Path

import pytest
from conftest import wait

from hallmark_demo.engine import RunManager, alive


def test_real_subprocess_stages_results_artifacts_and_redaction(runner):
    manager, _ = runner
    run = manager.start("fixture", {})
    done = wait(manager, run["id"])
    assert done["status"] == "succeeded"
    assert done["result"]["proofs_verified"] == 0
    assert all(stage["status"] == "succeeded" for stage in done["stages"])
    assert len(done["result_sha256"]) == 64
    assert done["samples"] and done["local_peak_rss"] > 0
    assert "hf_testsecret" not in json.dumps(done)
    assert "[redacted]" in json.dumps(done["events"])
    data, name = manager.artifact(
        done["id"], next(a["id"] for a in done["artifacts"] if a["name"] == "result.json")
    )
    assert name == "result.json" and json.loads(data)["status"] == "passed"
    assert "events" not in manager.list()[0]
    (Path(done["output"]) / "result.json").write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        manager.artifact(
            done["id"], next(a["id"] for a in done["artifacts"] if a["name"] == "result.json")
        )


def test_no_report_is_failure_even_when_process_exits_zero(runner):
    manager, script = runner
    script.write_text("print('done',flush=True)\n")
    run = manager.start("fixture", {})
    done = wait(manager, run["id"])
    assert done["status"] == "failed"
    assert "no evidence" in done["error"]


def test_nonzero_exit_cannot_pass_with_a_result(runner):
    manager, script = runner
    script.write_text(script.read_text() + "raise SystemExit(7)\n")
    done = wait(manager, manager.start("fixture", {})["id"])
    assert done["status"] == "failed" and done["exit_code"] == 7
    assert done["result"] is None


def test_one_run_and_controller_at_a_time(runner, root):
    manager, script = runner
    script.write_text("import time\ntime.sleep(30)\n")
    run = manager.start("fixture", {})
    with pytest.raises(ValueError, match="already active"):
        manager.start("fixture", {})
    with pytest.raises(ValueError, match="already owns"):
        RunManager(root)
    assert alive(run["pid"], run["process_created"])
    manager.cancel(run["id"])
    done = wait(manager, run["id"])
    assert done["status"] == "cancelled"
    assert not alive(done["pid"], done["process_created"])


def test_restart_observes_same_live_process_without_relaunch(runner, root, workflow):
    manager, script = runner
    script.write_text(script.read_text().replace("time.sleep(.2)", "time.sleep(1)"))
    run = manager.start("fixture", {})
    manager.stop_monitoring.set()
    for thread in manager.threads.values():
        thread.join(2)
    fcntl.flock(manager.lockfile, fcntl.LOCK_UN)
    manager.lockfile.close()
    recovered = RunManager(root, workflows={"fixture": workflow})
    try:
        current = recovered.snapshot(run["id"])
        assert current["pid"] == run["pid"]
        assert current["status"] == "detached"
        done = wait(recovered, run["id"])
        assert done["status"] == "succeeded"
        assert len(recovered.list()) == 1
    finally:
        recovered.close()
        # The fixture finalizer should not close this already-released lock twice.
        manager.closed = True


def test_missing_process_is_not_restarted(runner, root, workflow):
    manager, _ = runner
    run = wait(manager, manager.start("fixture", {})["id"])
    manager.stop_monitoring.set()
    for thread in manager.threads.values():
        thread.join(2)
    saved = root / "runs/workbench" / run["id"] / "state.json"
    data = json.loads(saved.read_text())
    data.update(status="running", pid=99999999, process_created=0, output=None)
    saved.write_text(json.dumps(data))
    fcntl.flock(manager.lockfile, fcntl.LOCK_UN)
    manager.lockfile.close()
    recovered = RunManager(root, workflows={"fixture": workflow})
    try:
        done = recovered.snapshot(run["id"])
        assert done["status"] == "interrupted"
        assert done["pid"] == 99999999
    finally:
        recovered.close()
        manager.closed = True


def test_cancelled_cloud_run_requires_cleanup_evidence(runner):
    manager, script = runner
    script.write_text(
        script.read_text()
        .replace("time.sleep(.2)", "time.sleep(1)")
        .replace(
            "print('Running prepare',flush=True)",
            "(p/'build').mkdir(exist_ok=True)\n"
            "(p/'build/bucket.json').write_text('{}')\n"
            "print('Running prepare',flush=True)",
        )
    )
    run = manager.start("fixture", {})
    wait(manager, run["id"], lambda r: r["output"] is not None)
    manager.cancel(run["id"])
    done = wait(manager, run["id"])
    assert done["status"] == "needs_attention" and done["cleanup_required"]


def test_secret_split_across_writes_is_not_streamed_partially(runner):
    manager, script = runner
    script.write_text(
        "import sys,time\n"
        "sys.stdout.write('hf_test');sys.stdout.flush();time.sleep(1)\n"
        "sys.stdout.write('secret123456789\\n');sys.stdout.flush();time.sleep(1)\n"
    )
    run = manager.start("fixture", {})
    time.sleep(0.7)
    assert "hf_test" not in json.dumps(manager.snapshot(run["id"])["events"])
    done = wait(manager, run["id"])
    assert "hf_test" not in json.dumps(done["events"])


def test_local_stop_escalates_for_an_unresponsive_process(runner, monkeypatch):
    from hallmark_demo import engine

    manager, script = runner
    monkeypatch.setattr(engine, "LOCAL_CANCEL_GRACE", 0.1)
    script.write_text(
        "import signal,time\nsignal.signal(signal.SIGINT,signal.SIG_IGN)\n"
        "print('Ready',flush=True)\ntime.sleep(60)\n"
    )
    run = manager.start("fixture", {})
    wait(manager, run["id"], lambda r: any(e["message"] == "Ready" for e in r["events"]))
    manager.cancel(run["id"])
    done = wait(manager, run["id"])
    assert done["status"] == "cancelled" and not alive(done["pid"], done["process_created"])


def test_stop_through_uv_delivers_one_interrupt_and_cleanup_completes(runner, monkeypatch):
    from hallmark_demo import engine

    manager, script = runner
    if not manager.uv.is_file():
        pytest.skip("uv is not installed beside the app interpreter")
    script.write_text(
        "import signal,time\nfrom pathlib import Path\n"
        "def handler(*_):\n"
        "    with open('runs/signals.log','a') as f: f.write('SIGINT\\n')\n"
        "    raise KeyboardInterrupt\n"
        "signal.signal(signal.SIGINT,handler)\n"
        "try:\n    print('Ready',flush=True)\n    time.sleep(60)\n"
        "except KeyboardInterrupt:\n    time.sleep(1.5)\n    Path('runs/cleanup.done').touch()\n"
    )
    command = [str(manager.uv), "run", "--no-project", "--offline"]
    command += ["--python", sys.executable, "python", str(script)]
    monkeypatch.setattr(engine, "plan", lambda *a: dict(command=command, paid=True, ceiling="0"))
    run = manager.start("fixture", {})
    wait(manager, run["id"], lambda r: any(e["message"] == "Ready" for e in r["events"]))
    manager.cancel(run["id"])
    done = wait(manager, run["id"])
    assert done["status"] == "cancelled"
    assert (manager.root / "runs/cleanup.done").is_file()
    assert (manager.root / "runs/signals.log").read_text() == "SIGINT\n"


def test_stage_logs_are_streamed_and_redacted(runner):
    manager, script = runner
    script.write_text(
        "from pathlib import Path\nimport time\np=Path.cwd()/'runs/stage.log'\np.touch()\n"
        "print(f'Running prove; log: {p}',flush=True)\ntime.sleep(.7)\n"
        "p.write_text('worker hf_testsecret123456789\\n')\ntime.sleep(.7)\n"
    )
    run = manager.start("fixture", {})
    done = wait(manager, run["id"])
    events = [e for e in done["events"] if e["kind"] == "stage-log"]
    assert events and "[redacted]" in events[0]["message"]
    assert "hf_testsecret" not in json.dumps(events)


def test_closed_controller_cannot_launch_work(runner):
    manager, _ = runner
    manager.close(grace=0)
    with pytest.raises(ValueError, match="stopping"):
        manager.start("fixture", {})


def test_api_and_receipt_do_not_leak_report_secrets_or_credit_balance(runner):
    manager, script = runner
    script.write_text(
        script.read_text().replace(
            "'proofs_verified':0", "'proofs_verified':0,'secret':'hf_reportsecret123456789'"
        )
    )
    done = wait(manager, manager.start("fixture", {})["id"])
    assert done["status"] == "succeeded"
    assert done["result"]["secret"] == "[redacted]"
    manager.runs[done["id"]]["parameters"]["balance"] = "123.45"
    assert "balance" not in manager.receipt(done["id"])["run"]["parameters"]
    with pytest.raises(ValueError, match="sensitive"):
        manager.artifact(
            done["id"], next(a["id"] for a in done["artifacts"] if a["name"] == "result.json")
        )


@pytest.mark.parametrize("raw", ["[]", "null", '{"value":NaN}', '{"a":1,"a":2}'])
def test_report_reader_rejects_ambiguous_nonobject_or_nonfinite_json(root, raw):
    from hallmark_demo.engine import read_json

    path = root / "result.json"
    path.write_text(raw)
    with pytest.raises(ValueError):
        read_json(path)


def test_transient_observation_failure_does_not_cancel_or_restart(runner, monkeypatch):
    manager, script = runner
    script.write_text(script.read_text().replace("time.sleep(.2)", "time.sleep(.7)"))
    sample = manager._sample
    observed = []

    def flaky(run):
        if not observed:
            observed.append(run["pid"])
            raise OSError("temporary process observation failure")
        return sample(run)

    monkeypatch.setattr(manager, "_sample", flaky)
    run = manager.start("fixture", {})
    done = wait(manager, run["id"])
    assert observed == [run["pid"]]
    assert done["status"] == "succeeded" and not done["cancel_requested"]
    assert done["pid"] == run["pid"] and len(manager.list()) == 1


def test_partial_price_plan_is_retried_and_artifact_ids_stay_stable(runner):
    manager, script = runner
    script.write_text(script.read_text().replace("time.sleep(.2)", "time.sleep(.7)"))
    run = manager.start("fixture", {})
    current = wait(manager, run["id"], lambda r: bool(r["output"]))
    output = Path(current["output"])
    (output / "protocol.json").write_text("{}")
    price = manager.directory / run["id"] / "resource-plan.json"
    price.write_text("{")
    first = wait(manager, run["id"], lambda r: bool(r["artifacts"]))
    protocol_id = next(a["id"] for a in first["artifacts"] if a["name"] == "protocol.json")
    price.write_text('{"bound": 1}')
    done = wait(manager, run["id"])
    assert done["status"] == "succeeded" and not done["cancel_requested"]
    assert done["resource_plan"] == {"bound": 1}
    assert next(a["id"] for a in done["artifacts"] if a["name"] == "protocol.json") == protocol_id
    assert manager.artifact(run["id"], protocol_id) == (b"{}", "protocol.json")


def test_unowned_storage_is_preserved(root):
    store = root / "runs/workbench"
    store.mkdir()
    unrelated = store / "keep.txt"
    unrelated.write_text("unrelated")
    with pytest.raises(ValueError, match="not owned"):
        RunManager(root)
    assert unrelated.read_text() == "unrelated"
    assert not (store / "controller.lock").exists()


def test_access_denied_is_unknown_not_process_death(monkeypatch):
    from hallmark_demo import engine

    def denied(_pid):
        raise engine.psutil.AccessDenied(123)

    monkeypatch.setattr(engine.psutil, "Process", denied)
    assert engine.alive(123, 456) is None


def test_nested_driver_jobs_are_monitored_without_replacing_primary_output(runner):
    manager, script = runner
    script.write_text(
        script.read_text().replace(
            "print('Running prove',flush=True)",
            "nested=Path.cwd()/'runs/nested'\n(nested/'build').mkdir(parents=True)\n"
            "(nested/'build/job.json').write_text(json.dumps(dict(id='test-job',url='https://example.com/job')))\n"
            "(nested/'build/bucket.json').write_text('{}')\n"
            "print(f'Evidence: {nested}',flush=True)\n"
            "print('build: COMPLETED (test-job)',flush=True)\n"
            "print('Running prove',flush=True)",
        )
    )
    done = wait(manager, manager.start("fixture", {})["id"])
    assert done["status"] == "needs_attention"
    assert Path(done["output"]).name == "output"
    assert done["jobs"][0]["id"] == "test-job"
    assert done["jobs"][0]["status"] == "COMPLETED"
    assert done["cleanup_required"]


def test_initial_identity_read_failure_keeps_the_owned_child(runner, monkeypatch):
    from hallmark_demo import engine

    manager, script = runner
    script.write_text(script.read_text().replace("time.sleep(.2)", "time.sleep(.7)"))
    original = engine.psutil.Process.create_time
    calls = []

    def initially_denied(process):
        if not calls:
            calls.append(process.pid)
            raise engine.psutil.AccessDenied(process.pid)
        return original(process)

    monkeypatch.setattr(engine.psutil.Process, "create_time", initially_denied)
    run = manager.start("fixture", {})
    done = wait(manager, run["id"])
    assert done["status"] == "succeeded" and not done["cancel_requested"]
    assert done["process_created"] is not None
    assert calls == [done["pid"]] and len(manager.list()) == 1
