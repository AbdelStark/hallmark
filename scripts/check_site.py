"""Check generated site links and key content without network access."""

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://abdelstark.github.io/hallmark/"


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag in {"a", "link"} and values.get("href"):
            self.links.append(values["href"])
        if tag in {"img", "script", "source"} and values.get("src"):
            self.links.append(values["src"])


def check(root):
    pages = {}
    for path in root.rglob("*.html"):
        doc = Document()
        doc.feed(path.read_text())
        pages[path.resolve()] = doc
    errors, checked = [], 0
    for path, document in pages.items():
        relative = path.relative_to(root.resolve()).as_posix()
        url = urljoin(BASE, relative.removesuffix("index.html"))
        for value in document.links:
            target = urlsplit(urljoin(url, value))
            if target.netloc != urlsplit(BASE).netloc or not target.path.startswith("/hallmark/"):
                continue
            local = unquote(target.path.removeprefix("/hallmark/"))
            dest = (root / local).resolve()
            if not dest.is_relative_to(root.resolve()):
                errors.append(f"{relative}: outside site {value}")
                continue
            if dest.is_dir():
                dest /= "index.html"
            checked += 1
            if not dest.is_file():
                errors.append(f"{relative}: missing {value}")
            elif (
                target.fragment
                and dest in pages
                and unquote(target.fragment) not in pages[dest].ids
            ):
                errors.append(f"{relative}: missing anchor {value}")
    return pages, checked, errors


def main():
    root = ROOT / "site"
    pages, links, errors = check(root)
    if errors:
        raise SystemExit("\n".join(errors[:80]))
    home = (root / "index.html").read_text()
    assert "Inference," in home and "53.94" in home
    assert "huggingface.co/abdelstark/hallmark-byte-mlp" in home
    assert "huggingface.co/abdelstark/hallmark-contextual-byte-cnn" in home
    assert (root / "assets/build.json").is_file()
    assert (root / "search.json").is_file()
    lesson = (root / "docs/learn/computation-and-claims/index.html").read_text()
    assert "arithmatex" in lesson
    architecture = (root / "docs/ARCHITECTURE/index.html").read_text()
    assert "mermaid" in architecture
    explorer = (root / "docs/learn/read-a-proof/index.html").read_text()
    assert 'id="a-complete-short-llm-response"' in explorer
    assert 'id="an-exact-classifier-verdict"' in explorer
    assert "### A complete short LLM response" not in explorer
    print(json.dumps(dict(status="passed", pages=len(pages), local_links_and_assets=links)))


if __name__ == "__main__":
    main()
