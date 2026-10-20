"""Pinned local proof qualification stages; incomplete until the whole gate exists."""

import hashlib
import json
import os
import platform
import re
import time
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from hallmark import _gnark_block_probe as block
from hallmark import _gnark_graph_probe as graph
from hallmark import _gnark_probe as worker
from hallmark.errors import HallmarkError, sanitize_exception
from hallmark.integrity import parse_json
from hallmark.manifests import FileHash32, FileRef, _Artifact, _Record, _verify_file

INPUTS = (
    "binary",
    "rule_fixture",
    "mlp_fixture",
    "block_fixture",
    "source_review",
    "dependency_review",
    "build_record",
    "authorization",
)
STAGES = (("installation", 18), ("rule", 134), ("mlp", 156), ("block", 233))
MISSING = (
    "complete-admitted-encoder-empty-near-boundary-maximum",
    "independently-enrolled-programs-and-keys",
    "independent-verifier-implementation",
    "independent-security-and-hiding-review",
    "accepted-setup-lineage",
)


def controller_sha256() -> bytes:
    """Pin the installed controller and its local trust-boundary helpers."""
    directory = Path(__file__).parent
    names = (
        "qualification",
        "_gnark_probe",
        "_gnark_graph_probe",
        "_gnark_block_probe",
        "manifests",
        "contracts",
        "wire",
        "errors",
        "integrity",
        "cli",
    )
    inventory = {
        name: worker.digest(worker.read_regular(directory / f"{name}.py", 1024**2))
        for name in names
    }
    return hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).digest()


class QualificationLimits(_Record):
    total_seconds: Annotated[int, Field(ge=1, le=7200)]
    case_seconds: Annotated[int, Field(ge=1, le=120)]
    verify_seconds: Annotated[int, Field(ge=1, le=60)]
    case_cpu_seconds: Annotated[int, Field(ge=1, le=120)]
    threads: Annotated[int, Field(ge=1, le=4)]
    max_worker_rss_bytes: Annotated[int, Field(ge=1024**2, le=16 * 1024**3)]
    max_output_bytes: Annotated[int, Field(ge=1, le=20 * 1024**3)]

    @model_validator(mode="after")
    def nested_limits(self) -> Self:
        if not self.verify_seconds <= self.case_seconds <= self.total_seconds:
            raise ValueError("inconsistent deadlines")
        return self


class QualificationProtocol(_Artifact):
    """An externally approved run plan, not proof of approval or qualification."""

    _domain = "protocol"
    schema_id: Literal["hallmark/qualification-protocol/1"]
    host: Literal["macos-arm64"]
    controller_sha256: FileHash32
    binary: FileRef
    rule_fixture: FileRef
    mlp_fixture: FileRef
    block_fixture: FileRef
    source_review: FileRef
    dependency_review: FileRef
    build_record: FileRef
    authorization: FileRef
    limits: QualificationLimits

    def refs(self) -> dict[str, FileRef]:
        return {name: getattr(self, name) for name in INPUTS}

    @model_validator(mode="after")
    def bounded_inventory(self) -> Self:
        refs = self.refs()
        if len({ref.path for ref in refs.values()}) != len(INPUTS):
            raise ValueError("duplicate input paths")
        for name, ref in refs.items():
            maximum = worker.MAX_BINARY if name == "binary" else 2 * 1024**2
            if not 1 <= ref.size <= maximum:
                raise ValueError("input outside read budget")
        if sum(ref.size for ref in refs.values()) > self.limits.max_output_bytes:
            raise ValueError("inputs exceed output budget")
        return self


def qualify(protocol_path: Path, expected_protocol: str, output: Path) -> dict[str, Any]:
    """Run the fixed roster with fresh setup; return incomplete even if every stage passes."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected_protocol):
        raise HallmarkError("INPUT_INVALID", "parse")
    raw = worker.read_regular(protocol_path, 1024**2)
    parse_json(raw.decode("utf-8"))
    protocol = QualificationProtocol.model_validate_json(raw)
    if protocol.identity().hex() != expected_protocol:
        raise HallmarkError("INPUT_INVALID", "verify")
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise HallmarkError("INPUT_INVALID", "execute")
    if protocol.controller_sha256 != controller_sha256():
        raise HallmarkError("INPUT_INVALID", "verify")
    root_fd = os.open(protocol_path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        seen: set[tuple[int, int]] = set()
        snapshots = {
            name: _verify_file(root_fd, ref, seen, retain=True)
            for name, ref in protocol.refs().items()
        }
    finally:
        os.close(root_fd)
    for kind in ("rule", "mlp"):
        value = graph.validate_fixture(snapshots[f"{kind}_fixture"])
        if value["schema_id"] != f"hallmark.gnark-{kind}-fixture/1":
            raise HallmarkError("INPUT_INVALID", "verify")
    block.validate_fixture(snapshots["block_fixture"])
    output.mkdir(mode=0o700)
    output = output.resolve()
    started = time.monotonic()
    limits = protocol.limits
    budget = worker.RunBudget(
        output,
        started + limits.total_seconds,
        limits.case_seconds,
        limits.verify_seconds,
        limits.case_cpu_seconds,
        limits.threads,
        limits.max_worker_rss_bytes,
        limits.max_output_bytes,
    )
    completed: list[dict[str, Any]] = []
    stage = "preparation"
    try:
        worker.write_new(output / "protocol.json", raw)
        inputs = output / "inputs"
        inputs.mkdir(mode=0o700)
        for name, data in snapshots.items():
            worker.write_new(inputs / name, data, 0o500 if name == "binary" else 0o600)
        worker.json_new(
            output / "environment.json",
            {
                "schema_id": "hallmark.qualification-environment/1",
                "python": platform.python_version(),
                "platform": platform.platform(),
                "protocol": expected_protocol,
                "controller_sha256": controller_sha256().hex(),
                "qualified_backend": False,
                "limits": limits.model_dump(mode="json"),
                "limitations": [
                    "RSS and storage are measured postconditions, not hard OS quotas.",
                    "The external protocol pin does not authenticate its approval.",
                    "Pinned review files are retained; their claims are not adjudicated.",
                ],
            },
        )
        del snapshots
        for stage, count in STAGES:
            budget.inspect()
            if stage == "installation":
                report = worker.check(
                    inputs / "binary", protocol.binary.sha256.hex(), output / stage, budget=budget
                )
            else:
                fixture = f"{stage}_fixture"
                check = block.check if stage == "block" else graph.check
                report = check(
                    inputs / "binary",
                    protocol.binary.sha256.hex(),
                    inputs / fixture,
                    protocol.refs()[fixture].sha256.hex(),
                    output / stage,
                    budget=budget,
                )
            if (
                report["status"] != "passed"
                or report["qualified_backend"] is not False
                or len(report["cases"]) != count
            ):
                raise HallmarkError("INPUT_INVALID", "verify")
            result_bytes = worker.read_regular(output / stage / "result.json", 4 * 1024**2)
            completed.append(
                {"stage": stage, "cases": count, "result_sha256": worker.digest(result_bytes)}
            )
            budget.inspect()
        total = budget.inspect()
        result = {
            "schema_id": "hallmark.qualification-result/1",
            "status": "incomplete",
            "qualified_backend": False,
            "protocol": expected_protocol,
            "completed": completed,
            "missing": list(MISSING),
            "elapsed_seconds": time.monotonic() - started,
            "measured_bytes_before_result": total,
        }
        encoded = (json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
        if total + len(encoded) > limits.max_output_bytes:
            raise MemoryError("qualification result exceeds budget")
        worker.write_new(output / "result.json", encoded)
        return result
    except (Exception, KeyboardInterrupt) as exc:
        failure = (
            HallmarkError("RESOURCE_EXHAUSTED", "execute")
            if isinstance(exc, KeyboardInterrupt)
            else sanitize_exception(exc, stage="execute")
        )
        worker.json_new(
            output / "failure.json",
            {
                "schema_id": "hallmark.qualification-failure/1",
                "status": "failed",
                "qualified_backend": False,
                "protocol": expected_protocol,
                "completed": completed,
                "failed_stage": stage,
                "error": failure.as_dict(),
            },
        )
        raise failure from None
