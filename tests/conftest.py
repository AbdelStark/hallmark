from pathlib import Path

import pytest

from hallmark.contracts import LinearArtifact

ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--require-train",
        action="store_true",
        help="fail unless every selected train test executes and passes without skips or xfails",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--require-train"):
        config.pluginmanager.register(_TrainingGate(), "required-training")


class _TrainingGate:
    def __init__(self) -> None:
        self.phases: dict[str, set[str]] = {}
        self.failed = False

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.phases = {
            item.nodeid: set()
            for item in session.items
            if item.get_closest_marker("train") is not None
        }

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.nodeid in self.phases:
            if report.passed and not hasattr(report, "wasxfail"):
                self.phases[report.nodeid].add(report.when)
            else:
                self.failed = True

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        complete = (
            self.phases
            and not self.failed
            and all(phases == {"setup", "call", "teardown"} for phases in self.phases.values())
        )
        if exitstatus == pytest.ExitCode.OK and not complete:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
            reporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if reporter is not None:
                reporter.write_sep("=", "required train tests did not all execute and pass")


@pytest.fixture
def root() -> Path:
    return ROOT


@pytest.fixture
def model() -> LinearArtifact:
    weights = [0] * 256
    weights[ord("x")] = 3
    weights[ord("a")] = -1
    return LinearArtifact(
        schema_id="hallmark.integer-byte-linear/1",
        policy_id="fixture.marker",
        scope="response",
        chunk_bytes=4,
        weights=tuple(weights),
        bias=-1,
        threshold=2,
        scale=128,
    )
