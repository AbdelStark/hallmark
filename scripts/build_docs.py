"""Build the public site from tracked documentation; ignored research runs never enter it."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/AbdelStark/hallmark/blob/main/"
ROOT_PAGES = {"index.md", "README.md", "SPEC.md", "CONTRIBUTING.md", "SECURITY.md", "LICENSE.md"}
TARGET = re.compile(r"""(?P<prefix>\]\(|^ {0,3}\[[^\]]+\]:\s*)(?P<url><[^>\n]+>|[^\s)"']+)""")


def destination(path):
    if path.as_posix() == "README.md":
        return Path("project.md")
    if path.as_posix() in ROOT_PAGES:
        return path
    if path.parts[0] in {"docs", "research"} and path.suffix == ".md":
        return path
    if path.parts[:2] == ("docs", "assets") and path.suffix in {".svg", ".png", ".jpg"}:
        return path
    if path.parts[:2] == ("research", "evidence") and path.suffix == ".json":
        return path
    if path.parts[:2] == ("website", "assets") and path.suffix in {
        ".css",
        ".js",
        ".mjs",
        ".svg",
        ".woff2",
        ".woff",
        ".ttf",
        ".txt",
        ".json",
    }:
        return Path(*path.parts[1:])
    return None


def rewrite(text, source, output, files):
    def link(match):
        original = match["url"]
        value = original.removeprefix("<").removesuffix(">")
        url = urlsplit(value)
        if url.scheme or url.netloc or not url.path or url.path.startswith("/"):
            return match[0]
        target = Path(os.path.normpath(source.parent / unquote(url.path)))
        if ".." in target.parts:
            raise ValueError("documentation link escapes the repository")
        if target in files:
            path = quote(os.path.relpath(files[target], output.parent), safe="/.-_")
        else:
            path = REPOSITORY + quote(target.as_posix(), safe="/.-_")
        if url.query:
            path += "?" + url.query
        if url.fragment:
            fragment = url.fragment
            if target in files and target.suffix == ".md":
                fragment = re.sub(r"-{2,}", "-", fragment)
            path += "#" + fragment
        return match["prefix"] + ("<" + path + ">" if original.startswith("<") else path)

    lines, fence = [], ""
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker and not fence:
            fence = marker[1]
        elif fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                if not marker[2].strip():
                    fence = ""
        else:
            line = TARGET.sub(link, line)
        lines.append(line)
    return "".join(lines)


def stage(root):
    root = root.resolve()
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    files = {Path(p): destination(Path(p)) for p in tracked if p and destination(Path(p))}
    output = root / "runs/docs-source"
    marker = output / ".hallmark-docs-stage"
    if (root / "runs").is_symlink() or output.is_symlink():
        raise ValueError("unsafe documentation staging path")
    if output.exists():
        if not marker.is_file():
            raise ValueError("refusing to replace an unowned staging directory")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    marker.touch()
    inventory = {}
    for source, target in sorted(files.items()):
        path = root / source
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError("unsafe tracked documentation input")
        data = path.read_bytes()
        inventory[source.as_posix()] = hashlib.sha256(data).hexdigest()
        if source.suffix == ".md":
            data = rewrite(data.decode(), source, target, files).encode()
        dest = output / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    manifest = dict(
        source_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root)
        .decode()
        .strip(),
        source_files=inventory,
        scope="tracked documentation, evidence and site assets only",
    )
    (output / "assets").mkdir(exist_ok=True)
    (output / "assets/build.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--serve", action="store_true", help="build, then preview at localhost:8000"
    )
    args = parser.parse_args()
    stage(ROOT)
    subprocess.run([sys.executable, "-m", "zensical", "build", "--strict"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, str(ROOT / "scripts/check_site.py")], cwd=ROOT, check=True)
    if args.serve:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "http.server",
                "8000",
                "--bind",
                "127.0.0.1",
                "--directory",
                "site",
            ],
            cwd=ROOT,
            check=True,
        )


if __name__ == "__main__":
    main()
