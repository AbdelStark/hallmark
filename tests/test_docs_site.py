"""Publication boundary and generated-link checks; browser QA is recorded separately."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_docs import destination, rewrite, stage
from check_site import check


def repository(tmp_path, files):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name, value in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    subprocess.run(["git", "add", *files], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture",
        ],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def test_staging_uses_tracked_allowlist_and_preserves_canonical_sources(tmp_path):
    root = repository(
        tmp_path,
        {
            "README.md": "# Project\n",
            "docs/guide.md": "[Overview](../README.md#project)\n[Runtime](../src/runtime.py)\n",
            "src/runtime.py": "secret = 'not a docs asset'\n",
            "website/assets/styles.css": "body {}\n",
            "website/assets/private.key": "not a public asset\n",
            "runs/notes.md": "never publish\n",
        },
    )
    (root / "docs/untracked.md").write_text("private note")
    out = stage(root)
    assert not (out / "docs/untracked.md").exists()
    assert not (out / "runs").exists() and not (out / "src").exists()
    assert not (out / "assets/private.key").exists()
    text = (out / "docs/guide.md").read_text()
    assert "../project.md#project" in text
    assert "https://github.com/AbdelStark/hallmark/blob/main/src/runtime.py" in text
    assert (out / "assets/styles.css").is_file()
    assert (root / "docs/guide.md").read_text().startswith("[Overview](../README.md")
    assert stage(root) == out


def test_unowned_staging_directory_is_preserved(tmp_path):
    root = repository(tmp_path, {"index.md": "# Home"})
    path = root / "runs/docs-source/keep.txt"
    path.parent.mkdir(parents=True)
    path.write_text("keep")
    with pytest.raises(ValueError, match="unowned"):
        stage(root)
    assert path.read_text() == "keep"


def test_tracked_symlink_is_rejected(tmp_path):
    root = repository(tmp_path, {"index.md": "# Home"})
    path = root / "docs/link.md"
    path.parent.mkdir()
    path.symlink_to(root / "index.md")
    subprocess.run(["git", "add", "docs/link.md"], cwd=root, check=True)
    with pytest.raises(ValueError, match="unsafe tracked"):
        stage(root)


def test_link_rewriting_preserves_code_and_external_urls():
    text = "[R](../src/a.py)\n```md\n[R](../src/a.py)\n```\n[E](https://example.com)\n"
    actual = rewrite(text, Path("docs/a.md"), Path("docs/a.md"), {})
    assert actual.count("https://github.com/AbdelStark/hallmark/blob/main/src/a.py") == 1
    assert "```md\n[R](../src/a.py)\n```" in actual
    assert "https://example.com" in actual
    with pytest.raises(ValueError, match="escapes"):
        rewrite("[bad](../../private.md)", Path("docs/a.md"), Path("docs/a.md"), {})


def test_github_heading_separator_maps_to_site_anchor():
    path = Path("docs/b.md")
    result = rewrite(
        "[R](b.md#result--controls)", Path("docs/a.md"), Path("docs/a.md"), {path: path}
    )
    assert result == "[R](b.md#result-controls)"


@pytest.mark.parametrize(
    "name", [".env", "checkpoints/model.json", "runs/private.md", "website/assets/token.pem"]
)
def test_nonpublic_inputs_have_no_site_destination(name):
    assert destination(Path(name)) is None


def test_generated_links_use_project_base_and_validate_anchors(tmp_path):
    (tmp_path / "docs/topic").mkdir(parents=True)
    (tmp_path / "index.html").write_text('<a href="docs/topic/#claim">Read</a>')
    page = tmp_path / "docs/topic/index.html"
    page.write_text('<h1 id="claim">Claim</h1><a href="/hallmark/">Home</a>')
    assert check(tmp_path)[2] == []
    page.write_text('<h1 id="other">Claim</h1>')
    assert "missing anchor" in check(tmp_path)[2][0]
