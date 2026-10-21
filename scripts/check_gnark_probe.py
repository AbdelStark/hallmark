"""Compatibility command for the installed pinned probe controller."""

from hallmark._gnark_probe import check, run_cli

if __name__ == "__main__":
    raise SystemExit(run_cli(check, fixture=False))
