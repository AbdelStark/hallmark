"""Bounded archive and installed-distribution inventories; no release authorization."""

import argparse
import csv
import hashlib
import importlib.metadata as metadata
import io
import itertools
import json
import platform
import re
import stat
import sys
import sysconfig
import tarfile
import tomllib
import zipfile
import zlib
from email.parser import Parser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

MAX_FILE = 8 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_FILES = 2048
FORBIDDEN = {
    "runs",
    "data",
    "checkpoints",
    "private",
    "secrets",
    "credentials",
    ".git",
    ".venv",
    "__pycache__",
    "harness",
}
SECRET = re.compile(
    rb"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{36,}"
    rb"|AKIA[0-9A-Z]{16}|hf_[A-Za-z0-9]{30,}"
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def safe_name(name):
    path = PurePosixPath(name)
    if (
        not name
        or not path.parts
        or len(name) > 4096
        or path.is_absolute()
        or path.as_posix() != name
        or ".." in path.parts
        or "\\" in name
        or ":" in name
        or any(ord(c) < 32 for c in name)
    ):
        raise ValueError("unsafe package path")
    if (
        any(part.lower() in FORBIDDEN or part.startswith(".env") for part in path.parts)
        or path.stem.lower() in {"private", "secrets", "credentials"}
        or path.suffix.lower()
        in {
            ".pem",
            ".key",
            ".pt",
            ".pth",
            ".safetensors",
            ".pkl",
            ".pickle",
            ".npy",
            ".npz",
            ".sqlite",
            ".log",
            ".pyc",
        }
    ):
        raise ValueError("private or generated package path")
    return name


def inspect_content(name, raw):
    safe_name(name)
    if len(raw) > MAX_FILE or SECRET.search(raw):
        raise ValueError("oversized file or recognizable credential material")


def file_inventory(files):
    if len(files) > MAX_FILES or sum(len(raw) for raw in files.values()) > MAX_TOTAL:
        raise ValueError("package inventory exceeds bounds")
    if len({name.casefold() for name in files}) != len(files):
        raise ValueError("case-aliasing package names")
    result = []
    for name, raw in sorted(files.items()):
        inspect_content(name, raw)
        result.append({"path": name, "size": len(raw), "sha256": digest(raw)})
    return result


def archive_files(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_TOTAL:
        raise ValueError("unsafe distribution file")
    files = {}
    total = 0

    def add(name, size, read):
        nonlocal total
        safe_name(name)
        total += size
        if name in files or len(files) >= MAX_FILES or size > MAX_FILE or total > MAX_TOTAL:
            raise ValueError("duplicate or oversized archive member")
        raw = read(MAX_FILE + 1)
        if len(raw) != size:
            raise ValueError("archive size mismatch")
        files[name] = raw

    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG) or info.is_dir():
                    raise ValueError("nonregular wheel member")
                with archive.open(info) as handle:
                    add(info.filename, info.file_size, handle.read)
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path) as archive:
            for info in archive:
                if not info.isfile():
                    raise ValueError("nonregular source member")
                with archive.extractfile(info) as handle:
                    add(info.name, info.size, handle.read)
    else:
        raise ValueError("unsupported distribution")
    file_inventory(files)
    return files


def check_archives(wheel, sdist, source, distribution):
    wheel_files, source_files = archive_files(wheel), archive_files(sdist)
    prefix = distribution + "/"
    expected_source = {prefix + name: raw for name, raw in source.items()}
    if set(source_files) != set(expected_source) | {prefix + "PKG-INFO"}:
        raise ValueError("sdist file inventory differs from reviewed source")
    if any(source_files[name] != raw for name, raw in expected_source.items()):
        raise ValueError("sdist source bytes differ")
    info = distribution + ".dist-info/"
    expected_wheel = {
        name.removeprefix("src/"): raw
        for name, raw in source.items()
        if name.startswith("src/hallmark/")
    }
    expected_wheel[info + "licenses/LICENSE.md"] = source["LICENSE.md"]
    generated = {info + name for name in ("METADATA", "WHEEL", "entry_points.txt", "RECORD")}
    if set(wheel_files) != set(expected_wheel) | generated:
        raise ValueError("wheel is not the exact code/type/metadata inventory")
    if any(wheel_files[name] != raw for name, raw in expected_wheel.items()):
        raise ValueError("wheel source bytes differ")
    if wheel_files[info + "METADATA"] != source_files[prefix + "PKG-INFO"]:
        raise ValueError("wheel and sdist metadata differ")
    import base64

    rows = list(csv.reader(io.StringIO(wheel_files[info + "RECORD"].decode())))
    if len(rows) != len(wheel_files) or {row[0] for row in rows} != set(wheel_files):
        raise ValueError("wheel RECORD inventory differs")
    for name, encoded, size in rows:
        if name == info + "RECORD":
            if encoded or size:
                raise ValueError("wheel RECORD must omit its own hash")
        else:
            raw = wheel_files[name]
            expected = "sha256=" + base64.urlsafe_b64encode(
                hashlib.sha256(raw).digest()
            ).decode().rstrip("=")
            if encoded != expected or size != str(len(raw)):
                raise ValueError("wheel RECORD hash mismatch")
    return {
        path.name: {
            "sha256": digest(path.read_bytes()),
            "size": path.stat().st_size,
            "files": file_inventory(files),
        }
        for path, files in ((wheel, wheel_files), (sdist, source_files))
    }


def wheel_tags(filename):
    parts = filename.removesuffix(".whl").split("-")[-3:]
    return {"-".join(tag) for tag in itertools.product(*(part.split(".") for part in parts))}


def environment_inventory(lock, project_wheel=None):
    packages = {p["name"]: p for p in tomllib.loads(lock.read_text())["package"]}
    result = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"]).lower()
        version = dist.version
        if name not in packages or version != packages[name]["version"]:
            raise ValueError("installed dependency absent from exact lock")
        wheel = Parser().parsestr(dist.read_text("WHEEL") or "")
        tags = set(wheel.get_all("Tag", []))
        if not tags:
            raise ValueError("installed dependency is not a wheel")
        if name == "hallmark-research":
            if project_wheel is None:
                raise ValueError("project wheel is not independently supplied")
            artifact = {
                "filename": project_wheel.name,
                "sha256": digest(project_wheel.read_bytes()),
            }
        else:
            matches = [
                w
                for w in packages[name].get("wheels", [])
                if wheel_tags(unquote(urlsplit(w["url"]).path).rsplit("/", 1)[-1]) == tags
            ]
            if len(matches) != 1:
                raise ValueError("installed wheel tags do not select exactly one locked archive")
            match = matches[0]
            artifact = {
                "filename": unquote(urlsplit(match["url"]).path).rsplit("/", 1)[-1],
                "sha256": match["hash"].removeprefix("sha256:"),
                "url": match["url"],
            }
        licences = []
        for file in dist.files or ():
            if file.name.lower().startswith(("license", "licence", "copying", "notice")):
                raw = dist.locate_file(file).read_bytes()
                licences.append({"path": str(file), "size": len(raw), "sha256": digest(raw)})
        licence = dist.metadata.get("License-Expression")
        legacy = dist.metadata.get("License")
        classifiers = [
            c for c in dist.metadata.get_all("Classifier", []) if c.startswith("License ::")
        ]
        if not licence and not legacy and not classifiers and not licences:
            raise ValueError("dependency has no recorded licence metadata or notice")
        result.append(
            {
                "name": name,
                "version": version,
                "artifact": artifact,
                "wheel_tags": sorted(tags),
                "license_expression": licence,
                "license_classifiers": classifiers,
                "legacy_license_sha256": digest(legacy.encode()) if legacy else None,
                "license_files": licences,
                "metadata_sha256": digest((dist.read_text("METADATA") or "").encode()),
                "requires_dist": dist.metadata.get_all("Requires-Dist", []),
            }
        )
    return {
        "schema_id": "hallmark/package-environment/1",
        "python": {
            "version": sys.version,
            "implementation": sys.implementation.name,
            "binary_sha256": digest(Path(sys.executable).read_bytes()),
            "system": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
            "soabi": sysconfig.get_config_var("SOABI"),
            "zlib": zlib.ZLIB_RUNTIME_VERSION,
        },
        "packages": result,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--project-wheel", type=Path)
    args = parser.parse_args()
    print(json.dumps(environment_inventory(args.lock, args.project_wheel), sort_keys=True))


if __name__ == "__main__":
    main()
