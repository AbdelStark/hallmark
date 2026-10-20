"""Local source bytes, lineage and split boundaries; all review documents are markers."""

import hashlib
import json
import random
import runpy
import stat
from pathlib import Path

import pytest
from pydantic import ValidationError

import hallmark.data_admission as data
from hallmark.data_admission import (
    DataImportPlan,
    DatasetManifest,
    LineageEntry,
    NearDuplicateReview,
    SourceManifest,
    SourceRow,
    SplitManifest,
    build_dataset,
    near_duplicate_candidates,
    verify_dataset,
    write_dataset,
)
from hallmark.errors import HallmarkError

ROOT = Path(__file__).resolve().parents[1]
BUILDER = runpy.run_path(str(ROOT / "scripts/build_data_fixture.py"))
export, row = BUILDER["export"], BUILDER["row"]
ref, json_bytes = BUILDER["file_ref"], BUILDER["json_bytes"]


@pytest.fixture
def artifacts():
    return export()


def build(artifacts, **changes):
    plan, policy, documents, raw_files = artifacts
    return build_dataset(
        plan,
        policy,
        **(dict(expected_plan=plan.identity(), documents=documents, raw_files=raw_files) | changes),
    )


def verify(artifacts, manifest, files, **changes):
    plan, policy, documents, raw_files = artifacts
    verify_dataset(
        manifest,
        files,
        plan,
        policy,
        **(
            dict(
                expected_dataset=manifest.identity(),
                expected_plan=plan.identity(),
                documents=documents,
                raw_files=raw_files,
            )
            | changes
        ),
    )


def records(files, name="records.jsonl"):
    return [json.loads(line) for line in files[name].splitlines()]


def rebind(artifacts, *, raw_files=None, source_changes=None, review_changes=None):
    """Invent new trusted fixture plans to exercise validation beyond byte-hash rejection."""
    plan, policy, docs, old_raw = artifacts
    docs = dict(docs)
    raw_files = old_raw if raw_files is None else raw_files
    approvals = []
    for approval in plan.sources:
        path = next(
            path for path, raw in docs.items() if hashlib.sha256(raw).digest() == approval.revision
        )
        source = SourceManifest.decode(docs[path])
        updates = dict(
            raw_files=tuple(ref(item.path, raw_files[item.path]) for item in source.raw_files)
        )
        updates.update(source_changes or {})
        source = SourceManifest.model_validate(source.model_dump() | updates)
        docs[path] = source.encode()
        approvals.append(
            approval.model_copy(update={"revision": hashlib.sha256(docs[path]).digest()})
        )
    near_path = plan.near_duplicate_review.path
    if review_changes:
        review = NearDuplicateReview.decode(docs[near_path])
        docs[near_path] = NearDuplicateReview.model_validate(
            review.model_dump() | review_changes
        ).encode()
    plan = plan.model_copy(
        update={
            "sources": tuple(approvals),
            "near_duplicate_review": ref(near_path, docs[near_path]),
            "evidence": tuple(ref(path, raw) for path, raw in sorted(docs.items())),
        }
    )
    return plan, policy, docs, raw_files


def test_complete_fixture_preserves_rows_text_and_review_provenance(artifacts):
    manifest, files = build(artifacts)
    verify(artifacts, manifest, files)
    normalized = {r["record_id"]: r for r in records(files)}
    lineage = {r["record_id"]: r for r in records(files, "lineage.jsonl")}
    assert manifest.record_count == len(normalized) == len(lineage) == 26
    assert manifest.group_count == 21
    for source_id, originals in BUILDER["source_rows"]().items():
        source_path = f"raw/{source_id}.jsonl"
        raw_lines = artifacts[3][source_path].splitlines(keepends=True)
        for index, original in enumerate(originals):
            result, entry = normalized[original.record_id], lineage[original.record_id]
            assert (result["prompt"], result["response"]) == (original.prompt, original.response)
            assert entry["raw_row"] == hashlib.sha256(raw_lines[index]).hexdigest()
            assert entry["source_row"] == index + 1
            assert entry["parents"] == list(original.parents)
            assert entry["source_manifest"] == result["source_revision"]
            assert entry["label_mapping_review"] and entry["annotation_review"]
            assert result["license_id"] == "LicenseRef-Proprietary"
    assert normalized["fixture-a-1"]["label"] == 0
    assert normalized["fixture-b-1"]["label"] == 1
    assert lineage["fixture-a-1"]["difficult_negative"] is True
    splits = json.loads(files["splits.json"])
    assert splits["near_duplicate_candidates"] == [["fixture-a-1", "fixture-b-1"]]
    for component in BUILDER["build"]()["required_components"]:
        assert len({normalized[name]["group_id"] for name in component}) == 1
        assert len({normalized[name]["split"] for name in component}) == 1


def test_groups_and_representatives_ignore_labels_and_input_order(artifacts):
    _, files = build(artifacts)
    changed = {
        source: [
            item.model_copy(
                update={
                    "source_label": "present" if item.source_label == "absent" else "absent",
                    "difficult_negative": False,
                }
            )
            for item in reversed(rows)
        ]
        for source, rows in reversed(list(BUILDER["source_rows"]().items()))
    }
    _, altered = build(export(changed))
    assert (
        json.loads(files["splits.json"])["groups"] == json.loads(altered["splits.json"])["groups"]
    )


def test_split_recipe_matches_independent_integer_boundaries(artifacts):
    _, files = build(artifacts)
    groups = json.loads(files["splits.json"])["groups"]
    strata = {}
    for group in groups:
        key = (tuple(group["sources"]), tuple(group["families"]))
        key = key if len(key[0]) == len(key[1]) == 1 else None
        strata.setdefault(key, []).append(group)
        members = group["members"]
        assert group["group_id"] == "g-" + hashlib.sha256(json_bytes(members)).hexdigest()
        expected = min(
            members,
            key=lambda name: (
                hashlib.sha256(b"inj-direct-design/1|representative|" + name.encode()).digest(),
                name,
            ),
        )
        assert group["representative"] == expected
    for stratum in strata.values():
        ordered = sorted(
            stratum,
            key=lambda group: (
                hashlib.sha256(b"inj-direct-design/1|split|" + group["group_id"].encode()).digest(),
                group["group_id"],
            ),
        )
        n = len(ordered)
        assert [group["split"] for group in ordered] == (
            ["train"] * (3 * n // 5)
            + ["calibration"] * (4 * n // 5 - 3 * n // 5)
            + ["test"] * (n - 4 * n // 5)
        )


def test_random_parent_forests_match_an_independent_reachability_oracle():
    rng = random.Random(29)
    for _ in range(25):
        rows = []
        edges = {f"r{i}": set() for i in range(30)}
        for i in range(30):
            parents = tuple(sorted(f"r{j}" for j in range(i) if rng.random() < 0.03))
            rows.append(row(f"r{i}", f"Distinct marker {i}.", parents=parents))
            for parent in parents:
                edges[f"r{i}"].add(parent)
                edges[parent].add(f"r{i}")
        # Ensure enough untouched groups for all three partitions.
        rows += [row(f"extra{i}", f"Separate example {i}.") for i in range(10)]
        for i in range(10):
            edges[f"extra{i}"] = set()
        _, files = build(export({"fixture-a": rows}))
        groups = json.loads(files["splits.json"])["groups"]
        for group in groups:
            pending, reachable = [group["members"][0]], set()
            while pending:
                name = pending.pop()
                if name not in reachable:
                    reachable.add(name)
                    pending.extend(edges[name] - reachable)
            assert reachable == set(group["members"])


@pytest.mark.parametrize("kind", ["source", "family"])
def test_held_out_members_move_the_entire_connected_group(kind):
    sources = BUILDER["source_rows"]()
    kwargs = {"held_sources": ("fixture-a",)}
    if kind == "family":
        sources["fixture-a"][0] = sources["fixture-a"][0].model_copy(
            update={"family_id": "held-family"}
        )
        kwargs = {"held_families": ("held-family",)}
    _, files = build(export(sources, **kwargs))
    groups = json.loads(files["splits.json"])["groups"]
    target = next(group for group in groups if "fixture-a-0" in group["members"])
    assert target["cohort"] == "held-out" and target["split"] == "test"
    assert "fixture-grandchild" in target["members"]
    assert any(group["cohort"] == "primary" and group["split"] == "train" for group in groups)


@pytest.mark.parametrize("pin", [None, b"", b"x" * 32, "x" * 32, bytearray(b"x" * 32)])
def test_missing_or_wrong_plan_pin_rejects(artifacts, pin):
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        build(artifacts, expected_plan=pin)


@pytest.mark.parametrize(
    "change",
    [
        {"source_id": "unapproved"},
        {"license_id": "Unapproved-Licence"},
        {"upstream_revision": "changed"},
        {"purpose": "other"},
    ],
)
def test_changed_source_or_licence_cannot_authorize_itself(artifacts, change):
    try:
        changed = rebind(artifacts, source_changes=change)
    except ValidationError:
        return
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        build(changed, expected_plan=artifacts[0].identity())


@pytest.mark.parametrize("inventory", ["documents", "raw_files"])
@pytest.mark.parametrize("mutation", ["missing", "extra", "changed", "wrong-type", "not-a-dict"])
def test_exact_source_and_document_inventories(artifacts, inventory, mutation):
    value = dict(artifacts[2 if inventory == "documents" else 3])
    path = next(iter(value))
    if mutation == "missing":
        value.pop(path)
    elif mutation == "extra":
        value["extra"] = b"extra"
    elif mutation == "changed":
        value[path] += b"changed"
    elif mutation == "wrong-type":
        value[path] = bytearray(value[path])
    else:
        value = None
    with pytest.raises(HallmarkError):
        build(artifacts, **{inventory: value})


@pytest.mark.parametrize("field", ["annotation_review", "data_card", "transformation_recipe"])
def test_missing_review_or_recipe_document_rejects_even_with_new_plan_pin(artifacts, field):
    changed = rebind(artifacts, source_changes={field: b"x" * 32})
    with pytest.raises(HallmarkError):
        build(changed)


def test_fixture_review_cannot_enter_a_non_fixture_import(artifacts):
    changed = (artifacts[0].model_copy(update={"fixture_only": False}), *artifacts[1:])
    with pytest.raises(HallmarkError):
        build(changed)


def test_mock_public_mode_binds_declarations_without_authenticating_human_review(artifacts):
    # These remain invented test documents; the caller must authenticate real reviewer evidence.
    changed = rebind(
        artifacts,
        source_changes={"privacy": "public", "review_kind": "human"},
        review_changes={"review_kind": "human"},
    )
    changed = (changed[0].model_copy(update={"fixture_only": False}), *changed[1:])
    manifest, files = build(changed)
    assert manifest.fixture_only is False
    verify(changed, manifest, files)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-parent",
        "cycle",
        "duplicate-id",
        "unknown-label",
        "positive-hard-negative",
        "small-split",
    ],
)
def test_lineage_and_labels_reject(mutation):
    sources = BUILDER["source_rows"]()
    if mutation == "missing-parent":
        sources["fixture-a"][0] = sources["fixture-a"][0].model_copy(
            update={"parents": ("absent",)}
        )
    elif mutation == "cycle":
        sources["fixture-a"][0] = sources["fixture-a"][0].model_copy(
            update={"parents": ("fixture-child",)}
        )
    elif mutation == "duplicate-id":
        sources["fixture-a"].append(sources["fixture-a"][0])
    elif mutation == "unknown-label":
        sources["fixture-a"][0] = sources["fixture-a"][0].model_copy(
            update={"source_label": "unknown"}
        )
    elif mutation == "positive-hard-negative":
        sources["fixture-a"][0] = sources["fixture-a"][0].model_copy(
            update={"source_label": "present", "difficult_negative": True}
        )
    else:
        sources = {"fixture-a": [row("only", "Only one group.")]}
    with pytest.raises(HallmarkError):
        build(export(sources))


@pytest.mark.parametrize(
    "raw",
    [
        b"\n",
        b"{}\n",
        b"[]\n",
        b"\xff\n",
        b'{"schema_id":"x","schema_id":"y"}\n',
        b'{"label":NaN}\n',
    ],
)
def test_reviewed_but_malformed_raw_bytes_reject_without_leaking(artifacts, raw):
    files = dict(artifacts[3])
    files["raw/fixture-a.jsonl"] = raw
    with pytest.raises(HallmarkError) as error:
        build(rebind(artifacts, raw_files=files))
    assert error.value.__context__ is None


def test_stale_near_duplicate_review_and_changed_review_mode_reject(artifacts):
    for changes in ({"candidate_inventory": b"x" * 32}, {"review_kind": "human"}):
        with pytest.raises(HallmarkError):
            build(rebind(artifacts, review_changes=changes))


def test_ascii_review_normalization_preserves_non_ascii_and_never_drops_contrastive_rows():
    rows = (
        row("a", "  MiXeD\t  SPACES ", "absent"),
        row("b", "mixed spaces", "present"),
        row("c", "café"),
        row("d", "cafe\u0301"),
        row("e", "CAFÉ"),
    )
    assert near_duplicate_candidates(rows) == (("a", "b"),)
    assert rows[0].prompt == "  MiXeD\t  SPACES "


@pytest.mark.parametrize("field", ["prompt", "response"])
def test_utf8_byte_boundary_rejects_without_truncation(field):
    original = row("utf8", "")
    valid = SourceRow.model_validate(original.model_dump() | {field: "🧪" * 8192})
    assert len(getattr(valid, field).encode()) == 32768
    with pytest.raises(ValidationError):
        SourceRow.model_validate(original.model_dump() | {field: "🧪" * 8193})
    with pytest.raises(ValidationError):
        SourceRow.model_validate(original.model_dump() | {field: "\ud800"})


@pytest.mark.parametrize("location", ["plan", "source"])
def test_mismatched_policy_rejects_even_under_new_plan_pin(artifacts, location):
    if location == "plan":
        changed = (artifacts[0].model_copy(update={"policy": b"x" * 32}), *artifacts[1:])
    else:
        changed = rebind(artifacts, source_changes={"policy": b"x" * 32})
    with pytest.raises(HallmarkError):
        build(changed)


@pytest.mark.parametrize("artifact", ["records.jsonl", "lineage.jsonl", "splits.json"])
def test_rehashed_cross_split_or_lineage_mutation_still_fails_reproduction(artifacts, artifact):
    manifest, files = build(artifacts)
    files = dict(files)
    if artifact == "records.jsonl":
        rows = records(files)
        child = next(row for row in rows if row["record_id"] == "fixture-child")
        child["split"] = "test" if child["split"] != "test" else "train"
        files[artifact] = b"".join(json_bytes(row) for row in rows)
        field = "records"
    elif artifact == "lineage.jsonl":
        rows = records(files, artifact)
        next(row for row in rows if row["record_id"] == "fixture-child")["parents"] = []
        files[artifact] = b"".join(json_bytes(row) for row in rows)
        field = "lineage"
    else:
        splits = json.loads(files[artifact])
        splits["groups"][0]["representative"] = "invented"
        files[artifact] = json_bytes(splits)
        field = "splits"
    changed = manifest.model_copy(update={field: ref(artifact, files[artifact])})
    with pytest.raises(HallmarkError):
        verify(artifacts, changed, files)


def test_dataset_pin_inventory_and_untrusted_constructed_records_reject(artifacts):
    manifest, files = build(artifacts)
    with pytest.raises(HallmarkError, match="TRUST_MISSING"):
        verify(artifacts, manifest, files, expected_dataset=b"x" * 32)
    with pytest.raises(HallmarkError):
        verify(artifacts, manifest, files | {"extra": b""})
    with pytest.raises(HallmarkError):
        build((artifacts[0].model_copy(update={"held_out_sources": ("unknown",)}), *artifacts[1:]))
    with pytest.raises(HallmarkError):
        build_dataset(
            None,
            artifacts[1],
            expected_plan=artifacts[0].identity(),
            documents=artifacts[2],
            raw_files=artifacts[3],
        )
    with pytest.raises(HallmarkError):
        build_dataset(
            artifacts[0],
            None,
            expected_plan=artifacts[0].identity(),
            documents=artifacts[2],
            raw_files=artifacts[3],
        )


def test_resource_caps_are_enforced_before_import_or_output(artifacts, monkeypatch):
    for name, value in (("MAX_ROWS", 1), ("MAX_RAW_BYTES", 1), ("MAX_OUTPUT_BYTES", 1)):
        with monkeypatch.context() as patch:
            patch.setattr(data, name, value)
            with pytest.raises(HallmarkError):
                build(artifacts)
    with monkeypatch.context() as patch:
        patch.setattr(data, "MAX_RAW_BYTES", 3)
        with pytest.raises(HallmarkError, match="LIMIT_EXCEEDED"):
            near_duplicate_candidates((row("large", "larger"),))


def test_new_private_directories_and_existing_or_symlink_targets(artifacts, tmp_path):
    manifest, files = build(artifacts)
    target = tmp_path / "new"
    write_dataset(target, manifest, files)
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert {path.name for path in target.iterdir()} == {*files, "manifest.json"}
    for path in target.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert DatasetManifest.model_validate_json((target / "manifest.json").read_bytes()) == manifest
    with pytest.raises(FileExistsError):
        write_dataset(target, manifest, files)
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(FileExistsError):
        write_dataset(link, manifest, files)
    assert all((target / name).read_bytes() == raw for name, raw in files.items())


@pytest.mark.parametrize("failure", [1, 2, 3, 4])
def test_sync_failures_preserve_partial_files_without_publishing_manifest(
    artifacts, tmp_path, monkeypatch, failure
):
    manifest, files = build(artifacts)
    target = tmp_path / "failed"
    calls = 0

    def fail_at(fd):
        nonlocal calls
        calls += 1
        if calls == failure:
            raise OSError("injected sync failure")

    monkeypatch.setattr(data.os, "fsync", fail_at)
    with pytest.raises(OSError):
        write_dataset(target, manifest, files)
    assert target.is_dir() and list(target.iterdir())
    assert not (target / "manifest.json").exists()
    with pytest.raises(FileExistsError):
        write_dataset(target, manifest, files)


def test_fixed_fixture_and_schemas_reproduce_without_network(monkeypatch):
    fixture = ROOT / "fixtures/wire/data-import-v1.json"
    assert BUILDER["build"]() == json.loads(fixture.read_text())
    for cls, name in (
        (SourceRow, "source-row"),
        (SourceManifest, "source-manifest"),
        (NearDuplicateReview, "near-duplicate-review"),
        (DataImportPlan, "data-import-plan"),
        (LineageEntry, "lineage"),
        (SplitManifest, "split-manifest"),
        (DatasetManifest, "dataset-manifest"),
    ):
        assert cls.model_json_schema() == json.loads(
            (ROOT / f"docs/schemas/{name}-v1.json").read_text()
        )
    monkeypatch.setattr("socket.socket", lambda *args, **kwargs: pytest.fail("network access"))
    runpy.run_path(str(ROOT / "scripts/check_data_import.py"))["check"](fixture)
