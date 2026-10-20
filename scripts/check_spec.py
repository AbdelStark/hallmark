"""Check v1 specification coverage; opt in to a read-only GitHub metadata audit."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, date, datetime
from pathlib import Path

from check_docs import ROOT, headings, missing_links, prose

REPO = "AbdelStark/hallmark"
ISSUES = f"https://github.com/{REPO}/issues/"
SECTIONS = [
    "Summary",
    "Motivation",
    "Goals",
    "Non-Goals",
    "Proposed Design",
    "Alternatives Considered",
    "Drawbacks",
    "Migration / Rollout",
    "Testing Strategy",
    "Open Questions",
    "References",
]
WORK = {f"W{i:02}" for i in range(1, 41)}
RFCS = {f"{i:04}" for i in range(1, 11)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(text):
    return [line.strip("| ").split(" | ") for line in text.splitlines() if line.startswith("| ")]


def check_work(root, work):
    require(work["schema_id"] == "hallmark/spec-work-map/1", "unknown work map")
    items = {item["id"]: item for item in work["items"]}
    require(set(items) == WORK and len(work["items"]) == len(WORK), "missing/duplicate work item")
    require(set(work["tracking"]) == RFCS, "missing/orphan RFC tracker")
    issue_ids = []
    for item in [*items.values(), *({"issue": v} for v in work["tracking"].values())]:
        issue = item["issue"]
        require(type(issue["number"]) is int and issue["number"] > 0, "invalid issue number")
        require(issue["url"] == ISSUES + str(issue["number"]), "foreign or invalid issue URL")
        issue_ids.append(issue["number"])
    require(len(set(issue_ids)) == len(issue_ids), "duplicate issue mapping")
    for key, item in items.items():
        for name in ("title", "area", "type", "priority", "effort", "out_of_scope"):
            require(isinstance(item[name], str) and item[name].strip(), f"{key}: missing {name}")
        for name in ("scope", "acceptance", "rfcs", "depends_on"):
            values = item[name]
            require(
                isinstance(values, list) and all(isinstance(v, str) and v.strip() for v in values),
                f"{key}: invalid {name}",
            )
            require(len(values) == len(set(values)), f"{key}: duplicate {name}")
            require(values or name == "depends_on", f"{key}: empty {name}")
        require(set(item["rfcs"]) <= RFCS, f"{key}: unknown RFC")
        require(set(item["depends_on"]) <= WORK - {key}, f"{key}: unknown/self dependency")
        require(item["milestone"] in {"v0.2", "v0.3", "v1.0"}, f"{key}: invalid milestone")
    pending = set(items)
    while pending:
        ready = {key for key in pending if not set(items[key]["depends_on"]) & pending}
        require(ready, "cyclic work dependencies")
        pending -= ready

    requirement_rows = [
        r
        for r in rows((root / "docs/spec/11-requirements.md").read_text())
        if re.match(r'<a id="w\d+">', r[0])
    ]
    require(len(requirement_rows) == len(WORK), "missing/extra requirement row")
    seen = set()
    for row in requirement_rows:
        match = re.fullmatch(r'<a id="(w\d+)"></a>(W\d+)', row[0])
        require(match and match[1].upper() == match[2], "invalid requirement anchor")
        key = match[2]
        require(key in items and key not in seen, "duplicate/orphan requirement")
        seen.add(key)
        item = items[key]
        require(
            len(row) == 5 and row[1] == item["title"] and row[3] == item["milestone"],
            f"{key}: requirement metadata differs",
        )
        require(re.findall(r"\[(\d{4})\]", row[2]) == item["rfcs"], f"{key}: RFC differs")
        require(row[4] == (", ".join(item["depends_on"]) or "None"), f"{key}: dependencies differ")

    tracker = (root / "docs/roadmap/IMPLEMENTATION.md").read_text()
    tracker_rows = []
    milestone = None
    for line in tracker.splitlines():
        if line.startswith("## Milestone: "):
            milestone = line.removeprefix("## Milestone: ")
        row = rows(line)
        if row and len(row[0]) > 1 and re.fullmatch(r"W\d+", row[0][1]):
            tracker_rows.append((row[0], milestone))
    require(len(tracker_rows) == len(WORK), "missing/extra tracker work row")
    seen = set()
    for row, milestone in tracker_rows:
        key = row[1]
        require(key in items and key not in seen, "duplicate/orphan tracker work")
        seen.add(key)
        item = items[key]
        issue = item["issue"]
        expected = [
            f" [#{issue['number']}]({issue['url']})".strip(),
            key,
            *(item[k] for k in ("title", "area", "priority", "effort")),
            ", ".join(item["rfcs"]),
        ]
        require(
            len(row) == 9 and row[:7] == expected and milestone == item["milestone"],
            f"{key}: tracker metadata differs",
        )
        deps = [items[k]["issue"] for k in item["depends_on"]]
        expected_deps = ", ".join(f"[#{d['number']}]({d['url']})" for d in deps) or "None"
        require(row[8] == expected_deps, f"{key}: tracker dependencies differ")
        if row[7].startswith("Merged"):
            require(
                re.search(rf"https://github.com/{REPO}/pull/\d+", row[7]),
                f"{key}: merged tracker lacks PR evidence",
            )
    for rfc, issue in work["tracking"].items():
        require(
            any(issue["url"] in line and f"RFC-{rfc}." in line for line in tracker.splitlines()),
            f"{rfc}: missing tracker link",
        )
    return items


def check_coverage(root, items):
    coverage = read_json(root / "docs/roadmap/coverage.json")
    require(coverage["schema_id"] == "hallmark/spec-coverage/1", "unknown coverage schema")
    targets = set()
    invariants = set()
    for path in sorted((root / "docs/spec").glob("*.md")):
        text = path.read_text()
        sections = headings(text)
        selected = [h for h in sections if h[0] == 2] or [h for h in sections if h[0] == 1]
        targets.update(f"{path.relative_to(root)}#{h[2]}" for h in selected)
        definitions = re.findall(r"\*\*(INV-[A-Z0-9-]+):\*\*", prose(text))
        require(
            not invariants.intersection(definitions) and len(set(definitions)) == len(definitions),
            "duplicate invariant definition",
        )
        invariants.update(definitions)
    rfcs = sorted((root / "docs/rfcs").glob("RFC-*.md"))
    require(len(rfcs) == 10 and {p.name[4:8] for p in rfcs} == RFCS, "missing/duplicate RFC")
    for path in rfcs:
        text = prose(path.read_text())
        require(
            [h[1] for h in headings(text) if h[0] == 2] == SECTIONS,
            f"{path.name}: RFC section template differs",
        )
        chunks = re.split(r"(?m)^## .+\n", text)
        require(all(chunk.strip() for chunk in chunks), f"{path.name}: empty RFC section")
        for field in ("Status", "Authors", "Created", "Target milestone"):
            require(
                len(re.findall(rf"(?m)^- {field}: .+", text)) == 1,
                f"{path.name}: missing/duplicate RFC {field}",
            )
        date.fromisoformat(re.search(r"(?m)^- Created: (.+)$", text)[1])
        questions = re.findall(r"(?m)^- OPEN QUESTION (.+)$", text)
        require(questions, f"{path.name}: missing owned open question")
        for question in questions:
            require(
                re.match(
                    r"[A-Z][A-Z-]+ — @[\w-]+.*resolution checkpoint \d{4}-\d{2}-\d{2}: .+", question
                ),
                f"{path.name}: unowned/undated question",
            )
            date.fromisoformat(re.search(r"checkpoint (\S+):", question)[1])
        targets.add(f"{path.relative_to(root)}#proposed-design")
    for name, expected in (("sections", targets), ("invariants", invariants)):
        require(set(coverage[name]) == expected, f"missing/orphan {name} coverage")
        for key, owners in coverage[name].items():
            require(
                isinstance(owners, list)
                and owners
                and len(set(owners)) == len(owners)
                and set(owners) <= items.keys(),
                f"{key}: invalid work coverage",
            )
    covered = {owner for owners in coverage["sections"].values() for owner in owners}
    require(covered == items.keys(), "work item has no source requirement")
    require(
        set(coverage["historical_sources"])
        == {str(p.relative_to(root)) for p in (root / "research/source").glob("*.txt")}
        and len(coverage["historical_sources"]) == 3,
        "missing historical source pin",
    )
    for name, expected in coverage["historical_sources"].items():
        require(
            name.startswith("research/source/") and ".." not in Path(name).parts,
            "invalid historical path",
        )
        require(digest(root / name) == expected, "historical source changed")
    return {"sections": len(targets), "invariants": len(invariants), "rfcs": len(rfcs)}


def check_local(root):
    errors = missing_links(root)
    require(not errors, "\n".join(errors))
    work = read_json(root / "docs/roadmap/work-items.json")
    items = check_work(root, work)
    counts = check_coverage(root, items)
    return work, {
        **counts,
        "work_items": len(items),
        "dependency_edges": sum(len(i["depends_on"]) for i in items.values()),
    }


def check_live(work, records):
    issues = {i["number"]: i for i in records if "pull_request" not in i}
    require(
        len(issues) == len([i for i in records if "pull_request" not in i]), "duplicate live issue"
    )
    items = {i["id"]: i for i in work["items"]}
    checked = []
    for item in items.values():
        number = item["issue"]["number"]
        require(number in issues, f"missing live issue #{number}")
        issue = issues[number]
        require(
            issue["html_url"] == item["issue"]["url"] and issue["title"] == item["title"],
            f"#{number}: live identity/title mismatch",
        )
        labels = {v["name"] for v in issue["labels"]}
        expected_labels = {f"{k}:{item[k]}" for k in ("area", "type", "priority", "effort")}
        expected_labels |= {f"spec:rfc-{rfc}" for rfc in item["rfcs"]}
        require(
            expected_labels
            == {
                label
                for label in labels
                if label.startswith(("area:", "type:", "priority:", "effort:", "spec:"))
            },
            f"#{number}: missing/conflicting live label",
        )
        require(
            issue["milestone"] and issue["milestone"]["title"] == item["milestone"],
            f"#{number}: live milestone mismatch",
        )
        body = issue["body"] or ""
        for field, heading in (("scope", "Scope"), ("acceptance", "Acceptance Criteria")):
            section = body.split(f"## {heading}\n", 1)[-1].split("\n## ", 1)[0]
            bullets = re.findall(r"(?m)^- (?:\[[ xX]\] )?(.+)$", section)
            require(bullets == item[field], f"#{number}: live {field} mismatch")
        deps = re.search(r"(?m)^- Depends on: (.+)$", body)
        expected_deps = {items[k]["issue"]["number"] for k in item["depends_on"]}
        require(
            deps
            and set(map(int, re.findall(r"#(\d+)", deps[1]))) == expected_deps
            and (expected_deps or deps[1] == "None"),
            f"#{number}: live dependencies differ",
        )
        require(
            f"#{item['id'].lower()})" in body and f"[{item['id']}]" in body,
            f"#{number}: missing live requirement reference",
        )
        checked.append(issue)
    for rfc, ref in work["tracking"].items():
        number = ref["number"]
        require(number in issues, f"missing live tracker #{number}")
        issue = issues[number]
        children = [i for i in items.values() if rfc in i["rfcs"]]
        expected = {i["issue"]["number"] for i in children}
        found = re.findall(r"(?m)^- \[[ xX]\] #(\d+) —", issue["body"] or "")
        require(
            len(found) == len(expected) and set(map(int, found)) == expected,
            f"#{number}: orphan/missing tracker child",
        )
        require(
            issue["html_url"] == ref["url"]
            and {"type:tracking", f"spec:rfc-{rfc}"} <= {v["name"] for v in issue["labels"]},
            f"#{number}: tracker metadata differs",
        )
        require(
            issue["milestone"]
            and issue["milestone"]["title"] == max(i["milestone"] for i in children),
            f"#{number}: tracker milestone differs",
        )
        checked.append(issue)
    return [
        {
            "number": i["number"],
            "url": i["html_url"],
            "title": i["title"],
            "state": i["state"],
            "updated_at": i["updated_at"],
            "labels": sorted(v["name"] for v in i["labels"]),
            "milestone": i["milestone"]["title"],
            "body_sha256": hashlib.sha256((i["body"] or "").encode()).hexdigest(),
        }
        for i in sorted(checked, key=lambda i: i["number"])
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="read GitHub issue metadata via gh")
    parser.add_argument("--output", type=Path, help="new audit JSON file, required for --live")
    args = parser.parse_args()
    if args.live != bool(args.output):
        parser.error("--live and --output must be supplied together")
    # Reserve a new result before network work; never replace a previous audit.
    output = args.output.open("x") if args.output else None
    result = {
        "schema_id": "hallmark/spec-check/1",
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "failed",
        "live": "not-checked",
    }
    try:
        work, counts = check_local(ROOT)
        result.update(counts)
        result["source_sha256"] = {
            str(p.relative_to(ROOT)): digest(p)
            for p in sorted(
                [
                    *ROOT.glob("docs/spec/*.md"),
                    *ROOT.glob("docs/rfcs/*.md"),
                    *ROOT.glob("docs/roadmap/*"),
                    ROOT / "scripts/check_spec.py",
                    ROOT / "scripts/check_docs.py",
                ]
            )
            if p.is_file()
        }
        if args.live:
            raw = subprocess.run(
                [
                    "gh",
                    "api",
                    "--paginate",
                    "--slurp",
                    f"repos/{REPO}/issues?state=all&per_page=100",
                ],
                capture_output=True,
                check=True,
                timeout=45,
            ).stdout
            records = [issue for page in json.loads(raw) for issue in page]
            result["response_sha256"] = hashlib.sha256(raw).hexdigest()
            result["issues"] = check_live(work, records)
            result["live"] = "matched"
        result["status"] = "passed"
    except (
        OSError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        subprocess.SubprocessError,
    ) as exc:
        result["error"] = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
    finally:
        if output:
            with output:
                json.dump(result, output, indent=2)
                output.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in {"source_sha256", "issues"}}))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
