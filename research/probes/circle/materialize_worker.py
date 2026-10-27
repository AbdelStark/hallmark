"""Install pinned inputs, record their copy time, then exec the proof-only tool.

Used inside the existing bounded Linux worker. No credentials, model downloads,
native replay or proof acceptance flags are supplied by this adapter.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from hallmark._gnark_probe import PinnedArtifact, digest, json_new, read_regular  # noqa: E402
from hallmark.integrity import parse_json  # noqa: E402


def main():
    if len(sys.argv) != 3:
        raise ValueError("expected manifest path and external manifest hash")
    raw = read_regular(Path(sys.argv[1]), 65536)
    if digest(raw) != sys.argv[2]:
        raise ValueError("caller input manifest mismatch")
    value = parse_json(raw.decode())
    if (
        set(value) != {"schema_id", "binary", "binary_sha256", "arguments", "files"}
        or value["schema_id"] != "hallmark.classifier-worker-inputs/1"
    ):
        raise ValueError("invalid input manifest")
    binary = Path(value["binary"])
    if digest(read_regular(binary.resolve(), 128 * 1024**2)) != value["binary_sha256"]:
        raise ValueError("caller executable pin mismatch")
    if type(value["arguments"]) is not list or not all(type(v) is str for v in value["arguments"]):
        raise ValueError("invalid executable arguments")
    started = time.perf_counter()
    for name, ref in value["files"].items():
        if (
            type(name) is not str
            or Path(name).name != name
            or name in (".", "..")
            or set(ref) != {"path", "sha256", "bytes"}
        ):
            raise ValueError("invalid input reference")
        PinnedArtifact(Path(ref["path"]), ref["sha256"], ref["bytes"]).copy_to(
            Path(name), 2 * 1024**3
        )
    json_new(
        Path("materialization.json"),
        dict(
            schema_id="hallmark.input-materialization/1",
            seconds=time.perf_counter() - started,
            files=len(value["files"]),
        ),
    )
    os.execve(binary, [str(binary), *value["arguments"]], os.environ)


if __name__ == "__main__":
    main()
