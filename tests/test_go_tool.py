"""Compiler dispatch and included-assembly path normalization."""

import hashlib
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
tool = importlib.import_module("go_tool")


@pytest.mark.parametrize("name", ["compile", "link"])
def test_version_and_other_tools_are_forwarded(monkeypatch, name):
    monkeypatch.setattr(sys, "argv", ["go_tool.py", "/tools/" + name, "-V=full"])
    calls = []
    monkeypatch.setattr(tool.os, "execv", lambda *args: calls.append(args))
    tool.main()
    assert calls == [("/tools/" + name, ["/tools/" + name, "-V=full"])]


def test_assembler_cache_identity_includes_the_wrapper(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["go_tool.py", "/tools/asm", "-V=full"])
    monkeypatch.setattr(tool.subprocess, "check_output", lambda *a, **k: "asm version go1.26.8\n")
    tool.main()
    identity = hashlib.sha256(Path(tool.__file__).read_bytes()).hexdigest()
    assert capsys.readouterr().out == "asm version go1.26.8 hallmark-pathmap=" + identity + "\n"


def test_assembly_includes_extend_existing_path_maps(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["go_tool.py", "/tools/asm", "-trimpath", "pkg=>module;tmp=>", "x.s"]
    )
    monkeypatch.setenv("GOMODCACHE", "/cache/one")
    calls = []
    monkeypatch.setattr(tool.os, "execv", lambda *args: calls.append(args))
    tool.main()
    assert calls == [
        (
            "/tools/asm",
            ["/tools/asm", "-trimpath", "pkg=>module;tmp=>;/cache/one=>gomodcache", "x.s"],
        )
    ]


@pytest.mark.parametrize("cache", ["relative", "/cache;other", "/cache=>other"])
def test_ambiguous_module_cache_maps_reject(monkeypatch, cache):
    monkeypatch.setattr(sys, "argv", ["go_tool.py", "/tools/asm", "-trimpath", "pkg=>module"])
    monkeypatch.setenv("GOMODCACHE", cache)
    with pytest.raises(ValueError, match="module cache"):
        tool.main()
