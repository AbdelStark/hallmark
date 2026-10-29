"""Persistent run lifecycle shared by the terminal and browser clients."""

import ast
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import psutil

from .catalog import CATALOG, plan, preflight
from .results import summarize

LOCAL_CANCEL_GRACE = 15

ACTIVE = {"starting", "running", "cancelling", "detached"}
OUTPUT = re.compile(r"^(?:Evidence|Outputs|Composed evidence): (.+)$")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|[\x00-\x08\x0b-\x1f\x7f]")
STORE_MARKER = "hallmark.demo-store/1\n"


class MonitoringLimitError(ValueError):
    """A hard output limit requires stopping the driver rather than retrying a read."""


def source_revision():
    package = Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted(package.rglob("*")):
        if path.is_file() and (path.suffix == ".py" or path.parent.name == "web"):
            digest.update(str(path.relative_to(package)).encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def now():
    return datetime.now(UTC).isoformat()


def parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    def constant(_value):
        raise ValueError("Nonfinite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def read_json(path, limit=2 * 1024**2):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Missing, unsafe or oversized result file")
    value = parse_json(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    return value


def alive(pid, created):
    try:
        process = psutil.Process(pid)
        return process.create_time() == created and process.status() != psutil.STATUS_ZOMBIE
    except psutil.AccessDenied:
        return None
    except (psutil.NoSuchProcess, TypeError):
        return False


class Redactor:
    def __init__(self, root):
        self.values = []
        candidates = dict(os.environ)
        path = root / ".env"
        if path.is_file() and not path.is_symlink() and path.stat().st_size < 65536:
            for line in path.read_text().splitlines():
                match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$", line)
                if match:
                    value = match[2]
                    try:
                        if value.startswith(('"', "'")):
                            value = ast.literal_eval(value)
                    except (ValueError, SyntaxError):
                        continue
                    if isinstance(value, str):
                        candidates[match[1]] = value
        for key, value in candidates.items():
            if re.search(r"TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY", key) and len(value) >= 8:
                self.values.append(value)

    def __call__(self, text):
        text = ANSI.sub("", str(text))
        for value in self.values:
            text = text.replace(value, "[redacted]")
        text = re.sub(r"\bhf_[A-Za-z0-9]{8,}\b", "[redacted]", text)
        return re.sub(r"(?i)(Bearer\s+)[A-Za-z0-9._-]+", r"\1[redacted]", text)


class RunManager:
    def __init__(self, root, *, workflows=None):
        self.root = Path(root).resolve()
        self.app_revision = source_revision()
        self.workflows = CATALOG if workflows is None else workflows
        self.directory = self.root / "runs/workbench"
        if (self.root / "runs").is_symlink() or self.directory.is_symlink():
            raise ValueError("Unsafe run storage")
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        marker = self.directory / ".hallmark-demo-store"
        if marker.is_symlink():
            raise ValueError("Unsafe run storage marker")
        if not marker.exists():
            if any(self.directory.iterdir()):
                raise ValueError("Run storage is not owned by Hallmark; choose another checkout")
            with marker.open("x") as stream:
                stream.write(STORE_MARKER)
            marker.chmod(0o600)
        if marker.read_text() != STORE_MARKER:
            raise ValueError("Unknown run storage format")
        if (self.directory / "controller.lock").is_symlink():
            raise ValueError("Unsafe controller lock")
        self.lockfile = (self.directory / "controller.lock").open("a+")
        try:
            fcntl.flock(self.lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lockfile.close()
            raise ValueError("A demo controller already owns this checkout") from None
        self.uv = Path(sys.executable).parent / "uv"
        self.redact = Redactor(self.root)
        self.lock = threading.RLock()
        self.runs = {}
        self.processes = {}
        self.threads = {}
        self.closed = False
        self.stop_monitoring = threading.Event()
        self.cpu_observations = {}
        for path in sorted(self.directory.glob("*/state.json")):
            try:
                run = read_json(path, 8 * 1024**2)
                if (
                    path.is_symlink()
                    or path.parent.is_symlink()
                    or path.parent.name != run["id"]
                    or not re.fullmatch(r"[0-9a-f]{12}", run["id"])
                    or run["workflow"] not in self.workflows
                ):
                    continue
                run.setdefault("schema_id", "hallmark.demo-run/1")
                self.runs[run["id"]] = run
                if run["status"] in ACTIVE:
                    if alive(run.get("pid"), run.get("process_created")) is not False:
                        run["status"] = "detached"
                        self._monitor_thread(run["id"])
                    else:
                        try:
                            self._finish(run, None)
                        except (ValueError, KeyError, TypeError, OSError):
                            # A missing log or old state must not leave a run active forever.
                            run.update(status="failed", ended_at=now(), ended_unix=time.time())
                        if run["status"] == "failed":
                            run["status"] = "interrupted"
                            run["error"] = (
                                "Process exited without a successful completion report. "
                                "Inspect retained evidence."
                            )
                            self._save(run)
            except (ValueError, KeyError, TypeError, OSError):
                continue

    def _save(self, run):
        directory = self.directory / run["id"]
        directory.mkdir(exist_ok=True, mode=0o700)
        temporary = directory / "state.tmp"
        temporary.write_text(json.dumps(run, allow_nan=False))
        temporary.chmod(0o600)
        temporary.replace(directory / "state.json")

    def _event(self, run, kind, message):
        event = dict(
            seq=run["next_seq"], time=now(), kind=kind, message=self.redact(message)[:8192]
        )
        run["next_seq"] += 1
        run["events"] = (run["events"] + [event])[-500:]
        path = self.directory / run["id"] / "events.jsonl"
        with path.open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        path.chmod(0o600)

    def _redact_view(self, value):
        if isinstance(value, str):
            return self.redact(value)
        if isinstance(value, list):
            return [self._redact_view(item) for item in value]
        if isinstance(value, dict):
            return {key: self._redact_view(item) for key, item in value.items()}
        return value

    def list(self):
        with self.lock:
            return [
                {
                    k: v
                    for k, v in self.snapshot(key).items()
                    if k not in {"events", "samples", "result", "checks", "artifacts", "command"}
                }
                for key in sorted(
                    self.runs, key=lambda k: self.runs[k]["started_unix"], reverse=True
                )
            ]

    def snapshot(self, key):
        with self.lock:
            if key not in self.runs:
                raise KeyError("Unknown run")
            run = json.loads(json.dumps(self.runs[key]))
            run["summary"] = (
                summarize(self.workflows[run["workflow"]], run["result"])
                if run.get("result") is not None
                else None
            )
            run["elapsed_seconds"] = max(
                0, (run.get("ended_unix") or time.time()) - run["started_unix"]
            )
            return self._redact_view(run)

    def checks(self, workflow, parameters=None):
        if workflow not in self.workflows:
            raise ValueError("Unknown workflow")
        return preflight(self.root, self.workflows[workflow], self.uv, parameters)

    def start(self, workflow_id, parameters):
        with self.lock:
            if self.closed:
                raise ValueError("The controller is stopping")
            if source_revision() != self.app_revision:
                raise ValueError(
                    "App source changed; restart the controller before launching a run"
                )
            if workflow_id not in self.workflows:
                raise ValueError("Unknown workflow")
            if any(run["status"] in ACTIVE for run in self.runs.values()):
                raise ValueError(
                    "A run is already active. Inspect or stop it before starting another."
                )
            workflow = self.workflows[workflow_id]
            self.redact = Redactor(self.root)
            prepared = plan(self.root, workflow, parameters, self.uv)
            checks = self.checks(workflow_id, prepared.get("parameters"))
            if any(not check["ok"] for check in checks):
                raise ValueError(
                    "Preflight failed: "
                    + "; ".join(
                        check["label"] + ": " + check["detail"]
                        for check in checks
                        if not check["ok"]
                    )
                )
            key = uuid.uuid4().hex[:12]
            command = list(prepared["command"])
            if prepared.get("monitor_adapter"):
                command += ["--monitor-dir", str(self.directory / key)]
            run = dict(
                schema_id="hallmark.demo-run/1",
                id=key,
                workflow=workflow_id,
                title=workflow.title,
                scheme=workflow.scheme,
                claim=workflow.claim,
                status="starting",
                started_at=now(),
                started_unix=time.time(),
                ended_at=None,
                ended_unix=None,
                pid=None,
                process_created=None,
                command=command,
                parameters=parameters,
                paid=prepared["paid"],
                cost_ceiling=prepared["ceiling"],
                checks=checks,
                output=None,
                result=None,
                result_sha256=None,
                error=None,
                cleanup_required=False,
                stages=[
                    dict(id=s.id, title=s.title, status="pending", started_at=None, ended_at=None)
                    for s in workflow.stages
                ],
                events=[],
                next_seq=1,
                log_offset=0,
                samples=[],
                artifacts=[],
                jobs=[],
                local_peak_rss=0,
                cancel_requested=False,
                source_commit=self._commit(),
                app_revision=self.app_revision,
            )
            self.runs[key] = run
            self._save(run)
            self._event(run, "lifecycle", "Starting " + workflow.title)
            directory = self.directory / key
            environment = dict(os.environ)
            environment.pop("VIRTUAL_ENV", None)
            environment.pop("UV_PROJECT_ENVIRONMENT", None)
            environment.update(
                PATH=str(self.uv.parent) + os.pathsep + environment.get("PATH", ""),
                PYTHONUNBUFFERED="1",
            )
            try:
                with (directory / "driver.log").open("xb") as log:
                    (directory / "driver.log").chmod(0o600)
                    process = subprocess.Popen(
                        command,
                        cwd=self.root,
                        env=environment,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                run.update(
                    pid=process.pid,
                    status="running",
                )
                self.processes[key] = process
                try:
                    run["process_created"] = psutil.Process(process.pid).create_time()
                except psutil.Error:
                    pass  # Keep the owned child handle; sampling retries identity capture.
                self._stage(run, workflow.stages[0].id)
                self._save(run)
                self._monitor_thread(key)
            except (OSError, psutil.Error) as error:
                run.update(
                    status="failed",
                    error=self.redact(error),
                    ended_at=now(),
                    ended_unix=time.time(),
                )
                self._event(run, "error", run["error"])
                self._save(run)
            return self.snapshot(key)

    def _commit(self):
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            return "unavailable"

    def _stage(self, run, stage_id):
        index = next(i for i, stage in enumerate(run["stages"]) if stage["id"] == stage_id)
        # Nested drivers can repeat preparation; never rewind the visible pipeline.
        current = next(
            (i for i, stage in enumerate(run["stages"]) if stage["status"] == "running"), -1
        )
        if index < current:
            return
        for i, stage in enumerate(run["stages"]):
            if i < index and stage["status"] != "succeeded":
                stage.update(status="succeeded", ended_at=now())
            elif i == index and stage["status"] == "pending":
                stage.update(status="running", started_at=now())
                self._event(run, "stage", stage["title"])

    def _line(self, run, line):
        clean = self.redact(line.strip())
        if not clean:
            return
        match = OUTPUT.fullmatch(clean)
        if match:
            path = Path(match[1])
            if (
                path.is_absolute()
                and path.is_dir()
                and not path.is_symlink()
                and path.resolve().is_relative_to((self.root / "runs").resolve())
            ):
                output = str(path.resolve())
                if run["output"] is None:
                    run["output"] = output
                elif output != run["output"]:
                    children = run.setdefault("child_outputs", [])
                    if output not in children and len(children) < 8:
                        children.append(output)
        stage_log = re.fullmatch(r"Running ([\w-]+); log: (.+)", clean)
        if stage_log:
            path = Path(stage_log[2])
            if (
                path.suffix == ".log"
                and path.is_file()
                and not path.is_symlink()
                and path.resolve().is_relative_to((self.root / "runs").resolve())
            ):
                logs = run.setdefault("stage_logs", {})
                if len(logs) < 32:
                    logs.setdefault(str(path), dict(stage=stage_log[1], offset=0, disabled=False))
        if run["status"] != "cancelling":
            workflow = self.workflows[run["workflow"]]
            for stage in workflow.stages:
                if any(marker in clean for marker in stage.markers):
                    self._stage(run, stage.id)
                    break
        if clean.startswith("{") and '"schema_id"' in clean:
            self._event(run, "log", "Structured report written by the workflow")
        else:
            self._event(run, "log", clean)

    def _tail(self, run, final=False):
        path = self.directory / run["id"] / "driver.log"
        if path.stat().st_size > 32 * 1024**2:
            raise MonitoringLimitError("Driver log exceeded the 32 MiB monitoring limit")
        with path.open("rb") as stream:
            stream.seek(run["log_offset"])
            for _ in range(200):
                line = stream.readline(2 * 1024**2)
                if not line:
                    break
                # Wait for a complete line so tokens split across writes cannot leak.
                if not line.endswith(b"\n"):
                    if len(line) >= 2 * 1024**2:
                        raise MonitoringLimitError("Driver produced a line exceeding 2 MiB")
                    if not final:
                        break
                run["log_offset"] = stream.tell()
                self._line(run, line.decode(errors="replace"))

    def _tail_stage_logs(self, run):
        for name, observed in run.get("stage_logs", {}).items():
            if observed["disabled"]:
                continue
            path = Path(name)
            if path.is_symlink() or path.stat().st_size > 32 * 1024**2:
                observed["disabled"] = True
                self._event(run, "log", "Large stage log retained locally: " + path.name)
                continue
            with path.open("rb") as stream:
                stream.seek(observed["offset"])
                for _ in range(100):
                    line = stream.readline(65536)
                    if not line:
                        break
                    if not line.endswith(b"\n"):
                        if len(line) == 65536:
                            observed["disabled"] = True
                            self._event(
                                run, "log", "Long stage output retained locally: " + path.name
                            )
                        break
                    observed["offset"] = stream.tell()
                    message = self.redact(line.decode(errors="replace").strip())
                    if message:
                        self._event(run, "stage-log", "[" + observed["stage"] + "] " + message)

    def _force_local_stop(self, run):
        if (
            run["paid"]
            or not run["cancel_requested"]
            or time.time() - run.get("cancel_started_unix", time.time()) < LOCAL_CANCEL_GRACE
        ):
            return
        targets = list(run.get("cancel_targets", []))
        if alive(run["pid"], run["process_created"]) is True:
            try:
                parent = psutil.Process(run["pid"])
                targets += [(p.pid, p.create_time()) for p in parent.children(recursive=True)]
                targets.append((parent.pid, parent.create_time()))
            except psutil.Error:
                pass
        for pid, created in targets:
            if alive(pid, created) is True:
                try:
                    psutil.Process(pid).kill()
                except psutil.Error:
                    pass

    def _sample(self, run):
        processes = [psutil.Process(run["pid"])]
        if run["process_created"] is None and run["id"] in self.processes:
            run["process_created"] = processes[0].create_time()
        processes += processes[0].children(recursive=True)
        rss, cpu_delta = 0, 0.0
        observations = self.cpu_observations.setdefault(run["id"], {})
        for process in processes:
            try:
                with process.oneshot():
                    rss += process.memory_info().rss
                    identity = (process.pid, process.create_time())
                    cpu = sum(process.cpu_times()[:2])
                    cpu_delta += max(0, cpu - observations.get(identity, cpu))
                    observations[identity] = cpu
            except psutil.Error:
                continue
        elapsed = time.time() - run["started_unix"]
        previous = run["samples"][-1] if run["samples"] else None
        interval = elapsed - previous["seconds"] if previous else 0
        sample = dict(
            seconds=round(elapsed, 2),
            rss_bytes=rss,
            cpu_percent=round(cpu_delta / interval * 100, 1) if interval > 0 else None,
            processes=len(processes),
        )
        run["samples"] = (run["samples"] + [sample])[-600:]
        run["local_peak_rss"] = max(run["local_peak_rss"], rss)

    def _inspect_output(self, run):
        price_plan = self.directory / run["id"] / "resource-plan.json"
        if price_plan.is_file():
            try:
                run["resource_plan"] = read_json(price_plan)
            except (ValueError, OSError):
                pass  # The adapter may still be writing; retain the last complete observation.
        if not run["output"]:
            return
        root = Path(run["output"])
        artifacts = []
        for relative in (
            "result.json",
            "failure.json",
            "protocol.json",
            "source-pins.json",
            "environment.json",
            "proofs/result.json",
            "mlp-training/results.json",
            "cnn-training/results.json",
        ):
            path = root / relative
            if (
                path.is_file()
                and not path.is_symlink()
                and path.resolve().is_relative_to(root)
                and path.stat().st_size <= 2 * 1024**2
            ):
                artifacts.append(
                    dict(
                        id=hashlib.sha256(relative.encode()).hexdigest()[:16],
                        name=relative,
                        bytes=path.stat().st_size,
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                )
        run["artifacts"] = artifacts
        jobs = []
        cleanup_required = False
        folders = [root, *(Path(p) for p in run.get("child_outputs", []))]
        for parent, phase in (
            (parent, phase)
            for parent in folders
            for phase in ("build", "prove", "benchmark", "verify")
        ):
            folder = parent / phase
            try:
                job = read_json(folder / "job.json")
            except (ValueError, OSError, json.JSONDecodeError):
                job = None
            try:
                receipt = read_json(folder / "retention.json")
            except (ValueError, OSError, json.JSONDecodeError):
                receipt = None
            if (folder / "bucket.json").is_file() and (
                not receipt or receipt.get("bucket_deleted") is not True
            ):
                cleanup_required = True
            if job:
                prior = next(
                    (row["status"] for row in run["jobs"] if row["id"] == job["id"]),
                    "Status not yet reported",
                )
                stage = receipt.get("stage", prior) if receipt else prior
                for event in reversed(run["events"]):
                    pattern = re.escape(phase) + r": ([A-Z_]+) \(" + re.escape(job["id"]) + r"\)"
                    matched = re.fullmatch(pattern, event["message"])
                    if matched and receipt is None:
                        stage = matched[1]
                        break
                jobs.append(
                    dict(
                        phase=phase,
                        id=job["id"],
                        url=job["url"],
                        status=stage,
                        cleanup_complete=bool(receipt and receipt.get("bucket_deleted")),
                    )
                )
        run.update(jobs=jobs, cleanup_required=cleanup_required)

    def _finish(self, run, code):
        self._tail(run, final=True)
        self._inspect_output(run)
        run.update(ended_at=now(), ended_unix=time.time(), exit_code=code)
        if run["cancel_requested"]:
            run["status"] = "needs_attention" if run["cleanup_required"] else "cancelled"
        elif code not in (0, None):
            run.update(status="failed", error=f"Workflow exited {code}. Inspect the retained logs.")
        else:
            try:
                workflow = self.workflows[run["workflow"]]
                if workflow.schema:
                    if not run["output"]:
                        raise ValueError("Driver produced no evidence directory")
                    path = Path(run["output"]) / "result.json"
                    result = read_json(path)
                    if result.get("schema_id") != workflow.schema or not (
                        result.get("status") == "passed" or result.get("passed") is True
                    ):
                        raise ValueError("Workflow result does not satisfy its completion contract")
                    run["result_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                else:
                    text = (self.directory / run["id"] / "driver.log").read_text()
                    result = json.loads(
                        next(line for line in reversed(text.splitlines()) if line.startswith("{"))
                    )
                    if result.get("software_passed") is not True or result.get("mismatched") != 0:
                        raise ValueError("Software conformance failed")
                    result = {
                        k: result[k]
                        for k in (
                            "schema_id",
                            "scope",
                            "matched",
                            "mismatched",
                            "software_passed",
                            "all_required_executed",
                        )
                    }
                summarize(workflow, result)
                run.update(result=result, status="succeeded")
            except (ValueError, OSError, StopIteration) as error:
                run.update(status="failed", error=self.redact(error))
        if run["cleanup_required"]:
            run["status"] = "needs_attention"
            run["error"] = (
                "Cloud cleanup is not confirmed. "
                "Inspect job links and retained bucket/retention records."
            )
        for stage in run["stages"]:
            if run["status"] == "succeeded":
                stage.update(status="succeeded", ended_at=stage["ended_at"] or now())
            elif stage["status"] == "running":
                stage.update(status=run["status"], ended_at=now())
        self._event(run, "lifecycle", run["error"] or run["status"].replace("_", " ").capitalize())
        self._save(run)

    def _monitor_thread(self, key):
        thread = threading.Thread(target=self._monitor, args=(key,), daemon=True)
        self.threads[key] = thread
        thread.start()

    def _monitor(self, key):
        while not self.stop_monitoring.is_set():
            with self.lock:
                run = self.runs[key]
                process = self.processes.get(key)
                code = process.poll() if process is not None else None
                live = code is None and (
                    process is not None or alive(run["pid"], run["process_created"]) is not False
                )
                try:
                    self._tail(run)
                    self._tail_stage_logs(run)
                    self._inspect_output(run)
                    if run["cancel_requested"]:
                        self._signal_stop(run)
                    self._force_local_stop(run)
                    if live:
                        self._sample(run)
                    else:
                        self._finish(run, code)
                        return
                except Exception as error:  # Any escape would end monitoring with the run active.
                    self._event(run, "error", str(error))
                    if isinstance(error, MonitoringLimitError) and live:
                        self.cancel(key)
                    if not live:
                        run.update(
                            status="failed",
                            error=self.redact(error),
                            ended_at=now(),
                            ended_unix=time.time(),
                        )
                        self._save(run)
                        return
                self._save(run)
            time.sleep(0.5)

    def _signal_stop(self, run):
        process = self.processes.get(run["id"])
        owned_child = process is not None and process.poll() is None
        if run.get("cancel_signalled") or (
            not owned_child and alive(run["pid"], run["process_created"]) is not True
        ):
            return
        try:
            # uv forwards SIGINT itself; a group signal would interrupt the driver's cleanup.
            os.kill(run["pid"], signal.SIGINT)
            run["cancel_signalled"] = True
        except ProcessLookupError:
            pass

    def cancel(self, key):
        with self.lock:
            run = self.runs[key]
            if run["status"] not in ACTIVE:
                return self.snapshot(key)
            if not run["cancel_requested"]:
                run.update(
                    cancel_requested=True, status="cancelling", cancel_started_unix=time.time()
                )
                run["cancel_targets"] = []
                if alive(run["pid"], run["process_created"]) is True:
                    try:
                        run["cancel_targets"] = [
                            (p.pid, p.create_time())
                            for p in psutil.Process(run["pid"]).children(recursive=True)
                        ]
                    except psutil.Error:
                        pass
                self._event(
                    run,
                    "lifecycle",
                    "Stop requested; waiting for driver cleanup and retained outputs.",
                )
                self._signal_stop(run)
                self._save(run)
            return self.snapshot(key)

    def receipt(self, key):
        run = self.snapshot(key)
        run["parameters"] = {k: v for k, v in run["parameters"].items() if k != "balance"}
        return dict(
            schema_id="hallmark.demo-receipt/1",
            exported_at=now(),
            run=run,
            note="Monitoring receipt. Recheck driver evidence and independently enrolled "
            "inputs before relying on a proof. Prepaid balance is omitted.",
        )

    def artifact(self, key, artifact_id):
        with self.lock:
            run = self.runs[key]
            item = next((a for a in run["artifacts"] if a["id"] == artifact_id), None)
            if item is None:
                raise KeyError("Unknown artifact")
            root = Path(run["output"])
            path = root / item["name"]
            if (
                path.is_symlink()
                or not path.resolve().is_relative_to(root)
                or path.stat().st_size > 2 * 1024**2
            ):
                raise ValueError("Unsafe artifact")
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("Artifact changed; refresh the run")
            if self.redact(data.decode()) != data.decode():
                raise ValueError("Report contains sensitive values; inspect the private local copy")
            return data, path.name

    def retained(self):
        items = []
        for prefix, kind in (
            ("e2e-", "classifier_run"),
            ("llm-e2e-", "llm_run"),
            ("llm-gpu-", "build_run"),
        ):
            paths = set((self.root / "runs").glob(prefix + "*"))
            paths.update((self.root / "runs").glob("*/runs/" + prefix + "*"))
            for path in sorted(paths):
                if path.is_symlink() or not path.is_dir():
                    continue
                try:
                    report = read_json(path / "result.json")
                except (ValueError, OSError):
                    continue
                if report.get("status") == "passed" or report.get("passed") is True:
                    items.append(
                        dict(path=str(path.relative_to(self.root)), kind=kind, name=path.name)
                    )
        return items

    def close(self, grace=20):
        with self.lock:
            if self.closed:
                return
            self.closed = True
        for key, run in list(self.runs.items()):
            if run["status"] in ACTIVE:
                self.cancel(key)
        deadline = time.monotonic() + grace
        for thread in self.threads.values():
            thread.join(max(0, deadline - time.monotonic()))
        # Live drivers keep their disk log and recorded PID; a new controller observes
        # the same process rather than launching a duplicate paid job.
        self.stop_monitoring.set()
        for thread in self.threads.values():
            thread.join(2)
        fcntl.flock(self.lockfile, fcntl.LOCK_UN)
        self.lockfile.close()
