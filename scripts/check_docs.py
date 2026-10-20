"""Check repository Markdown paths and anchors without network dependencies."""

import html
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def markdown_files(root: Path) -> list[Path]:
    files = [*root.glob("*.md"), *root.glob("docs/**/*.md"), *root.glob("research/**/*.md")]
    files += list(root.glob(".agents/workflows/**/*.md"))
    return sorted(files)


def prose(text: str) -> str:
    """Remove comments and fenced examples, including tilde and longer fences."""
    lines = []
    fence = ""
    for line in re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if match and not fence:
            fence = match[1]
        elif fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence):
                if not match[2].strip():
                    fence = ""
        else:
            lines.append(line)
    return "\n".join(lines)


def slug(text: str) -> str:
    text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).lower()
    return "".join(c for c in text if c in " _-" or unicodedata.category(c)[0] in "LMN").replace(
        " ", "-"
    )


def headings(text: str) -> list[tuple[int, str, str]]:
    seen: set[str] = set()
    result = []
    for line in prose(text).splitlines():
        match = re.match(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if match:
            title = match[2]
            base = slug(title)
            anchor = base
            suffix = 0
            while anchor in seen:
                suffix += 1
                anchor = f"{base}-{suffix}"
            seen.add(anchor)
            result.append((len(match[1]), title, anchor))
    return result


def anchors(text: str) -> set[str]:
    return {h[2] for h in headings(text)} | set(
        re.findall(r'<a\s+(?:id|name)=["\']([^"\']+)["\']', prose(text))
    )


def links(text: str) -> list[str]:
    text = re.sub(r"(`+).*?\1", "", prose(text))
    # shortcut: only repository Markdown forms; extend fixtures before adopting others.
    target = r"(<[^>\n]+>|(?:[^\s()]|\([^()\n]*\))+)"
    result = re.findall(r"\]\(" + target + r'(?:\s+"[^"]*")?\)', text)
    references = {
        name.strip().casefold(): url
        for name, url in re.findall(r"(?m)^ {0,3}\[([^]]+)\]:\s*" + target, text)
    }
    result += list(references.values())
    for label, reference in re.findall(r"\[([^]\n]+)\]\[([^]\n]*)\]", text):
        key = (reference or label).strip().casefold()
        if key not in references:
            raise ValueError("undefined Markdown reference")
    return [link.removeprefix("<").removesuffix(">") for link in result]


def missing_links(root: Path) -> list[str]:
    root = root.resolve()
    errors = []
    for path in markdown_files(root):
        try:
            targets = links(path.read_text())
        except ValueError as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
            continue
        for link in targets:
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            if not target.is_relative_to(root) or not target.is_file():
                errors.append(f"{path.relative_to(root)}: missing or outside-root link {link}")
            elif parsed.fragment and (
                target.suffix != ".md"
                or unquote(parsed.fragment) not in anchors(target.read_text())
            ):
                errors.append(f"{path.relative_to(root)}: missing anchor {link}")
    return errors


if __name__ == "__main__":
    errors = missing_links(ROOT)
    if errors:
        raise SystemExit("\n".join(errors))
    print("Local Markdown paths and anchors valid; external URLs not checked.")
