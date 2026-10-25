"""Normalize included assembly paths without recording machine paths in build info."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path


def main():
    tool, *args = sys.argv[1:]
    if Path(tool).name == "asm" and args == ["-V=full"]:
        version = subprocess.check_output([tool, *args], text=True).strip()
        identity = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        print(version + " hallmark-pathmap=" + identity)
        return
    if Path(tool).name == "asm" and "-trimpath" in args:
        index = args.index("-trimpath") + 1
        cache = os.environ["GOMODCACHE"]
        if not Path(cache).is_absolute() or ";" in cache or "=>" in cache:
            raise ValueError("invalid module cache path")
        args[index] += ";" + cache + "=>gomodcache"
    os.execv(tool, [tool, *args])


if __name__ == "__main__":
    main()
