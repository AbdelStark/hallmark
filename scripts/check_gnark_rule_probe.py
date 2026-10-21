"""Compatibility command for the installed pinned probe controller."""

from hallmark._gnark_graph_probe import check
from hallmark._gnark_probe import run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli(check, fixture=True))
