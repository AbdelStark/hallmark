"""Check public registry fixtures through the installed library and offline CLI."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hallmark.enrollment import RegistryState, SignedRegistry, TrustPolicy
from hallmark.errors import HallmarkError
from hallmark.registry import SignedTransition
from hallmark.registry_history import (
    append_history,
    create_history,
    read_snapshot,
    read_transition,
)
from hallmark.registry_store import provision_state, read_state


def main() -> None:
    vector = json.loads(Path(sys.argv[1]).read_text())
    old = TrustPolicy.decode(bytes.fromhex(vector["old_trust"]["cbor_hex"]))
    new = TrustPolicy.decode(bytes.fromhex(vector["new_trust"]["cbor_hex"]))
    previous = SignedRegistry.decode(bytes.fromhex(vector["previous"]["cbor_hex"]))
    snapshot = SignedRegistry.decode(bytes.fromhex(vector["snapshot"]["cbor_hex"]))
    transition = SignedTransition.decode(bytes.fromhex(vector["transition"]["cbor_hex"]))
    state = RegistryState(
        schema_id="hallmark/registry-state/1",
        sequence=previous.body.sequence,
        digest=previous.body.identity(),
    )
    transition.verify(old, new, state)
    with tempfile.TemporaryDirectory(prefix="hallmark-registry-fixture-") as directory:
        root = Path(directory)
        archive, checkpoint = root / "history.sqlite", root / "checkpoint.sqlite"
        create_history(archive, previous, old, state, vector["now"])
        result = append_history(
            archive, snapshot, new, state, vector["now"], transition=transition, old_trust=old
        )
        assert read_snapshot(archive, state) == previous
        assert read_snapshot(archive, result.state) == snapshot
        assert read_transition(archive, result.state) == transition
        try:
            append_history(
                archive, snapshot, new, state, vector["now"], transition=transition, old_trust=old
            )
        except HallmarkError as error:
            assert error.code == "REGISTRY_INVALID"
        else:
            raise AssertionError("stale authoring state was accepted")
        for name, record in (
            ("old", old),
            ("new", new),
            ("previous", previous),
            ("snapshot", snapshot),
            ("transition", transition),
        ):
            (root / name).write_bytes(record.encode())
        provision_state(checkpoint, state)
        arguments = [
            sys.executable,
            "-m",
            "hallmark.cli",
            "registry-check",
            str(root / "snapshot"),
            "--trust",
            str(root / "new"),
            "--state",
            str(checkpoint),
            "--now",
            str(vector["now"]),
            "--old-trust",
            str(root / "old"),
            "--transition",
            str(root / "transition"),
            "--previous",
            str(root / "previous"),
        ]
        checked = subprocess.run(arguments, capture_output=True, text=True, timeout=10, check=True)
        report = json.loads(checked.stdout)
        assert checked.stderr == "" and report["schema_id"] == "hallmark/registry-check/1"
        assert report["registry"] == snapshot.body.identity().hex()
        assert report["trust"] == new.identity().hex()
        assert read_state(checkpoint) == result.state
        rejected = subprocess.run(
            arguments, capture_output=True, text=True, timeout=10, check=False
        )
        assert rejected.returncode == 1 and rejected.stdout == ""
        assert json.loads(rejected.stderr)["code"] == "REGISTRY_INVALID"
        assert read_state(checkpoint) == result.state
    print("Public fixture rotation, retained history, checkpoint, CLI and replay rejection passed.")


if __name__ == "__main__":
    main()
