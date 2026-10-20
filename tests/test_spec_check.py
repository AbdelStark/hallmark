"""Mutations of the documented specification gate, with no network in tests."""

import copy
import importlib
import json
import shutil

import pytest


@pytest.fixture
def checker(root, monkeypatch):
    monkeypatch.syspath_prepend(str(root / "scripts"))
    return importlib.import_module("check_spec")


@pytest.fixture
def work(root):
    return json.loads((root / "docs/roadmap/work-items.json").read_text())


@pytest.fixture
def docs_copy(root, tmp_path):
    for directory in ("docs/spec", "docs/rfcs", "docs/roadmap", "research/source"):
        shutil.copytree(root / directory, tmp_path / directory)
    return tmp_path


def test_current_spec(checker, root):
    _, counts = checker.check_local(root)
    assert counts == {
        "work_items": 40,
        "dependency_edges": 106,
        "rfcs": 10,
        "sections": 51,
        "invariants": 18,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "cycle",
        "unknown-dependency",
        "self",
        "orphan-issue",
        "foreign",
        "missing-acceptance",
        "duplicate-issue",
        "unknown-rfc",
        "missing-tracker",
    ],
)
def test_work_map_rejects_drift(checker, root, work, mutation):
    if mutation == "missing":
        work["items"].pop()
    elif mutation == "duplicate":
        work["items"].append(copy.deepcopy(work["items"][0]))
    elif mutation == "cycle":
        work["items"][0]["depends_on"] = ["W02"]
    elif mutation == "unknown-dependency":
        work["items"][0]["depends_on"] = ["W99"]
    elif mutation == "self":
        work["items"][0]["depends_on"] = ["W01"]
    elif mutation == "orphan-issue":
        work["items"][0]["issue"] = {"number": 999, "url": checker.ISSUES + "999"}
    elif mutation == "foreign":
        work["items"][0]["issue"]["url"] = "https://github.com/other/repo/issues/2"
    elif mutation == "missing-acceptance":
        work["items"][0]["acceptance"] = []
    elif mutation == "duplicate-issue":
        work["items"][1]["issue"] = work["items"][0]["issue"]
    elif mutation == "unknown-rfc":
        work["items"][0]["rfcs"] = ["9999"]
    else:
        del work["tracking"]["0001"]
    with pytest.raises(ValueError):
        checker.check_work(root, work)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-requirement",
        "duplicate-requirement",
        "tracker-dependency",
        "tracker-title",
        "tracker-milestone",
        "merged-evidence",
        "orphan-tracker",
    ],
)
def test_requirement_and_tracker_rows(checker, docs_copy, work, mutation):
    target = docs_copy / "docs/roadmap/IMPLEMENTATION.md"
    if "requirement" in mutation:
        target = docs_copy / "docs/spec/11-requirements.md"
    text = target.read_text()
    if mutation == "missing-requirement":
        text = "\n".join(line for line in text.splitlines() if 'id="w01"' not in line)
    elif mutation == "duplicate-requirement":
        text += next(line for line in text.splitlines() if 'id="w01"' in line)
    elif mutation == "tracker-dependency":
        text = text.replace("| Open; blocked |", "| Open; blocked | changed ", 1)
    elif mutation == "tracker-title":
        text = text.replace("| wire: implement strict", "| changed: implement strict", 1)
    elif mutation == "tracker-milestone":
        text = text.replace("## Milestone: v0.2", "## Milestone: v1.0", 1)
    elif mutation == "merged-evidence":
        text = text.replace("https://github.com/AbdelStark/hallmark/pull/52", "absent", 1)
    else:
        text = text.replace("| W01 |", "| W99 |", 1)
    target.write_text(text)
    with pytest.raises(ValueError):
        checker.check_work(docs_copy, work)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-section",
        "orphan-section",
        "unknown-owner",
        "missing-invariant",
        "missing-source",
        "changed-source",
        "new-heading",
        "missing-rfc-section",
        "empty-rfc-section",
        "missing-question-owner",
        "invalid-question-date",
    ],
)
def test_coverage_and_rfc_contract(checker, docs_copy, work, mutation):
    target = docs_copy / "docs/roadmap/coverage.json"
    coverage = json.loads(target.read_text())
    if mutation == "missing-section":
        coverage["sections"].pop(next(iter(coverage["sections"])))
    elif mutation == "orphan-section":
        coverage["sections"]["docs/spec/00-overview.md#absent"] = ["W01"]
    elif mutation == "unknown-owner":
        coverage["sections"][next(iter(coverage["sections"]))] = ["W99"]
    elif mutation == "missing-invariant":
        del coverage["invariants"]["INV-COMPLETE-V1"]
    elif mutation == "missing-source":
        coverage["historical_sources"] = {}
    elif mutation == "changed-source":
        (docs_copy / "research/source/product-requirements.txt").write_text("changed")
    else:
        path = docs_copy / "docs/rfcs/RFC-0001-wire.md"
        text = path.read_text()
        if mutation == "new-heading":
            path = docs_copy / "docs/spec/00-overview.md"
            text = path.read_text() + "\n## Unowned requirement\nImplement another thing.\n"
        elif mutation == "missing-rfc-section":
            text = text.replace("## Goals", "## Replaced")
        elif mutation == "empty-rfc-section":
            start, rest = text.split("## Motivation\n", 1)
            text = start + "## Motivation\n\n## Goals\n" + rest.split("## Goals\n", 1)[1]
        elif mutation == "missing-question-owner":
            text = text.replace("— @AbdelStark, resolution", "— nobody, resolution")
        else:
            text = text.replace("checkpoint 2026-11-02:", "checkpoint 2026-02-31:")
        path.write_text(text)
    target.write_text(json.dumps(coverage))
    with pytest.raises(ValueError):
        checker.check_coverage(docs_copy, {i["id"]: i for i in work["items"]})


@pytest.fixture
def live_records(checker, work):
    records = []
    by_id = {i["id"]: i for i in work["items"]}
    for item in work["items"]:
        deps = ", ".join(f"#{by_id[k]['issue']['number']} ({k})" for k in item["depends_on"])
        body = f"[{item['id']}](https://example.com/spec#{item['id'].lower()})\n"
        for key, heading in (("scope", "Scope"), ("acceptance", "Acceptance Criteria")):
            body += f"\n## {heading}\n\n" + "\n".join("- " + v for v in item[key]) + "\n"
        body += "\n## Dependencies\n\n- Depends on: " + (deps or "None") + "\n"
        labels = [f"{k}:{item[k]}" for k in ("area", "type", "priority", "effort")]
        labels += [f"spec:rfc-{r}" for r in item["rfcs"]]
        records.append(
            {
                "number": item["issue"]["number"],
                "html_url": item["issue"]["url"],
                "title": item["title"],
                "body": body,
                "labels": [{"name": label} for label in labels],
                "milestone": {"title": item["milestone"]},
                "state": "open",
                "updated_at": "2026-10-20T00:00:00Z",
            }
        )
    for rfc, issue in work["tracking"].items():
        children = [i for i in work["items"] if rfc in i["rfcs"]]
        records.append(
            {
                "number": issue["number"],
                "html_url": issue["url"],
                "title": "Tracker",
                "body": "\n".join(
                    f"- [ ] #{i['issue']['number']} — {i['title']}" for i in children
                ),
                "labels": [{"name": "type:tracking"}, {"name": f"spec:rfc-{rfc}"}],
                "milestone": {"title": max(i["milestone"] for i in children)},
                "state": "open",
                "updated_at": "2026-10-20T00:00:00Z",
            }
        )
    return records


def test_live_issue_projection(checker, work, live_records):
    checked = checker.check_live(work, live_records)
    assert len(checked) == 50
    assert checked[0]["number"] == 2 and checked[-1]["number"] == 51
    assert all("body" not in i and len(i["body_sha256"]) == 64 for i in checked)
    # PRs in the paginated issues endpoint are not work issues.
    assert checker.check_live(work, live_records + [{"pull_request": {}, "number": 99}]) == checked


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "title",
        "label",
        "conflicting-label",
        "milestone",
        "scope",
        "acceptance",
        "dependencies",
        "requirement",
        "tracker-child",
        "tracker-milestone",
    ],
)
def test_live_drift_fails(checker, work, live_records, mutation):
    record = live_records[0]
    if mutation == "missing":
        live_records.pop(0)
    elif mutation == "duplicate":
        live_records.append(copy.deepcopy(record))
    elif mutation == "title":
        record["title"] += " changed"
    elif mutation == "label":
        record["labels"].pop()
    elif mutation == "conflicting-label":
        record["labels"].append({"name": "priority:p9"})
    elif mutation == "milestone":
        record["milestone"] = None
    elif mutation in {"scope", "acceptance"}:
        record["body"] = record["body"].replace(work["items"][0][mutation][0], "changed")
    elif mutation == "dependencies":
        record["body"] = record["body"].replace("Depends on: None", "Depends on: #99")
    elif mutation == "requirement":
        record["body"] = record["body"].replace("#w01", "#wrong")
    elif mutation == "tracker-child":
        live_records[-1]["body"] += "\n- [ ] #99 — orphan"
    else:
        live_records[-1]["milestone"] = {"title": "v0.2"}
    with pytest.raises(ValueError):
        checker.check_live(work, live_records)


def test_duplicate_json_key_rejected(checker, tmp_path):
    path = tmp_path / "map.json"
    path.write_text('{"items": [], "items": []}')
    with pytest.raises(ValueError, match="duplicate JSON"):
        checker.read_json(path)


@pytest.mark.parametrize("failure", ["timeout", "denied"])
def test_live_api_failure_retains_failed_audit_without_raw_output(
    checker, tmp_path, monkeypatch, capsys, failure
):
    output = tmp_path / "failed.json"
    monkeypatch.setattr("sys.argv", ["check_spec.py", "--live", "--output", str(output)])

    def fail(*args, **kwargs):
        assert kwargs["timeout"] == 45 and kwargs["capture_output"]
        if failure == "timeout":
            raise checker.subprocess.TimeoutExpired("gh", 45, output="PRIVATE_SENTINEL")
        raise checker.subprocess.CalledProcessError(
            1, "gh", output="PRIVATE_SENTINEL", stderr="PRIVATE_SENTINEL"
        )

    monkeypatch.setattr(checker.subprocess, "run", fail)
    assert checker.main() == 1
    result = json.loads(output.read_text())
    assert result["status"] == "failed" and result["live"] == "not-checked"
    assert result["source_sha256"]
    assert "PRIVATE_SENTINEL" not in output.read_text() + capsys.readouterr().out


def test_live_audit_refuses_overwrite_before_api(checker, tmp_path, monkeypatch):
    output = tmp_path / "existing.json"
    output.write_text("preserved failure")
    monkeypatch.setattr("sys.argv", ["check_spec.py", "--live", "--output", str(output)])
    monkeypatch.setattr(checker.subprocess, "run", lambda *a, **k: pytest.fail("network called"))
    with pytest.raises(FileExistsError):
        checker.main()
    assert output.read_text() == "preserved failure"


def test_offline_gate_never_queries_github(checker, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["check_spec.py"])
    monkeypatch.setattr(checker.subprocess, "run", lambda *a, **k: pytest.fail("network called"))
    assert checker.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "passed" and result["live"] == "not-checked"
