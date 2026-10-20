"""Check local Markdown file links without network or optional dependencies."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def missing_links(root: Path) -> list[str]:
    errors = []
    files = [*root.glob("*.md"), *root.glob("docs/**/*.md"), *root.glob("research/**/*.md")]
    files += list(root.glob(".agents/**/*.md"))
    for path in files:
        text = re.sub(r"```.*?```", "", path.read_text(), flags=re.DOTALL)
        for link in re.findall(r"\]\(([^\s)]+)\)", text):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_file():
                errors.append(f"{path.relative_to(root)}: missing or outside-root link {link}")
    return errors


if __name__ == "__main__":
    errors = missing_links(ROOT)
    if errors:
        raise SystemExit("\n".join(errors))
    print("Local Markdown file links valid (anchors and external URLs not checked).")
