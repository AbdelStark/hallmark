"""Check the installed protocol and CLI rejection; never execute marker bytes."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from hallmark.qualification import QualificationProtocol


def check(path):
    fixture = json.loads(path.read_text())
    protocol = QualificationProtocol.decode(bytes.fromhex(fixture["cbor_hex"]))
    assert protocol.identity().hex() == fixture["identity_hex"]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config = root / "private-protocol.json"
        config.write_text(protocol.model_dump_json())
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "hallmark.cli",
                "qualify",
                str(config),
                "--expected-protocol",
                "0" * 64,
                "--output",
                str(root / "output"),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 2 and not result.stdout
        assert json.loads(result.stderr)["code"] == "INPUT_INVALID"
        assert directory not in result.stderr and not (root / "output").exists()
    print(
        json.dumps(
            {
                "schema_id": "hallmark.qualification-contract-check/1",
                "status": "matched",
                "qualified_backend": False,
            }
        )
    )


if __name__ == "__main__":
    check(Path(sys.argv[1]))
