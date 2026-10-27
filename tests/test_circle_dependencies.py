import json
import tomllib
from pathlib import Path


def test_every_locked_registry_dependency_has_a_matching_license_review():
    root = Path(__file__).resolve().parents[1] / "research/probes/circle"
    lock = tomllib.loads((root / "Cargo.lock").read_text())
    review = json.loads((root / "dependencies.json").read_text())
    locked = {(p["name"], p["version"], p["checksum"]) for p in lock["package"] if "source" in p}
    reviewed = {(p["name"], p["version"], p["checksum"]) for p in review["packages"]}
    assert locked == reviewed and len(reviewed) == len(review["packages"])
    assert all(
        p["selected_license_alternative"] and p["source"].startswith("registry+")
        for p in review["packages"]
    )
