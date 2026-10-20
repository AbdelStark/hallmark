"""Required installed-wheel synthetic training/replay; no pytest skip path."""

import json
import os
import sys
from pathlib import Path

import hallmark
from hallmark.experiment import audit_run, run_experiment


def main():
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    root, output = map(Path, sys.argv[1:])
    assert Path(hallmark.__file__).is_relative_to(Path(sys.prefix))
    pin = run_experiment(root / "configs/fixture.json", output)
    result = audit_run(output, root / "fixtures/smoke.jsonl", pin)
    assert result["status"] == "research-replay-matched"
    report = json.loads((output / "results.json").read_text())
    assert report["evidence_class"] == "synthetic-fixture"
    assert report["fpr_evidence_status"] == "insufficient-evidence"
    assert report["zk_proof"] == "not-implemented"
    try:
        audit_run(output, root / "fixtures/smoke.jsonl", "0" * 64)
    except ValueError:
        pass
    else:
        raise AssertionError("caller pin was ignored")
    # Keep the complete fixture intact; mutate a copy for the installed negative check.
    import shutil

    altered = output.with_name(output.name + "-altered")
    shutil.copytree(output, altered)
    report["metrics"]["test"]["tp"] = 999
    (altered / "results.json").write_text(json.dumps(report))
    try:
        audit_run(altered, root / "fixtures/smoke.jsonl", pin)
    except ValueError:
        pass
    else:
        raise AssertionError("changed result was accepted")
    print("Installed train contract: synthetic fit/replay and pin/tamper rejection passed.")


if __name__ == "__main__":
    main()
