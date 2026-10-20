import importlib.util
from pathlib import Path


def test_doc_checker_rejects_missing_and_outside_links(root: Path, tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("check_docs", root / "scripts/check_docs.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "README.md").write_text(
        "[ok](README.md) [web](https://example.com) [anchor](#here) "
        "[bad](missing.md) [outside](../README.md)\n```\n[example](absent.md)\n```"
    )
    errors = module.missing_links(tmp_path)
    assert len(errors) == 2
    assert "missing.md" in errors[0]
    assert "../README.md" in errors[1]
