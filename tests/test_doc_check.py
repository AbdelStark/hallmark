import importlib.util
from pathlib import Path


def test_doc_checker_rejects_missing_and_outside_links(root: Path, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("check_docs", root / "scripts/check_docs.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "README.md").write_text(
        "[ok](README.md) [web](https://example.com) [anchor](#here) "
        "[bad](missing.md) [outside](../README.md)\n## Here\n```\n[example](absent.md)\n```"
    )
    errors = module.missing_links(tmp_path)
    assert len(errors) == 2
    assert "missing.md" in errors[0]
    assert "../README.md" in errors[1]


def doc_module(root):
    spec = importlib.util.spec_from_file_location("check_docs", root / "scripts/check_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_anchors_include_unicode_explicit_ids_and_duplicates(root):
    module = doc_module(root)
    text = "# Hello, **world**!\n## Café `x_y`\n## Hello, world!\n## Hello-world-1\n"
    text += '## Hello, world!\n<a id="manual"></a>\n'
    assert module.anchors(text) == {
        "hello-world",
        "café-x_y",
        "hello-world-1",
        "hello-world-1-1",
        "hello-world-2",
        "manual",
    }


def test_missing_anchor_and_reference_are_rejected(root, tmp_path):
    module = doc_module(root)
    target = tmp_path / "README.md"
    target.write_text("# Exists\n[missing](#absent)\n[valid](#exists)\n")
    assert module.missing_links(tmp_path) == ["README.md: missing anchor #absent"]
    target.write_text("[missing][undefined]\n")
    assert module.missing_links(tmp_path) == ["README.md: undefined Markdown reference"]


def test_cross_file_reference_and_encoded_paths(root, tmp_path):
    module = doc_module(root)
    (tmp_path / "other page.md").write_text("# Target!\n")
    target = tmp_path / "README.md"
    target.write_text(
        '[inline](<other page.md#target>) [ref][r] [r][]\n[r]: other%20page.md#target "title"\n'
    )
    assert module.missing_links(tmp_path) == []
    (tmp_path / "other page.md").write_text("# Changed\n")
    assert len(module.missing_links(tmp_path)) == 2


def test_code_and_comments_do_not_supply_links_or_anchors(root, tmp_path):
    module = doc_module(root)
    text = "~~~~text\n# Hidden\n[bad](absent.md)\n~~~~\n"
    text += "````\n```\n[bad](absent.md)\n````\n"
    text += "<!-- # Hidden2\n[bad](absent.md) -->\n`[bad](absent.md)`\n"
    (tmp_path / "README.md").write_text(text)
    assert module.missing_links(tmp_path) == []
    assert not module.anchors(text)


def test_symlink_target_outside_repository_fails(root, tmp_path):
    module = doc_module(root)
    (tmp_path / "README.md").write_text("[outside](link.md)\n")
    (tmp_path / "link.md").symlink_to(root / "README.md")
    assert any("outside-root link" in e for e in module.missing_links(tmp_path))


def test_long_unfinished_link_is_plain_text_without_exponential_backtracking(root):
    module = doc_module(root)
    assert module.links("[unfinished](" + "a" * 10000 + "\n") == []
