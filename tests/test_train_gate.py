"""Exercise the guard through real pytest subprocesses, including false-green cases."""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def suite(
    pytester: pytest.Pytester, root: Path, monkeypatch: pytest.MonkeyPatch
) -> pytest.Pytester:
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    pytester.makeconftest((root / "tests/conftest.py").read_text())
    pytester.makeini("[pytest]\nmarkers = train: local training fixture\n")
    return pytester


@pytest.mark.parametrize(
    "source",
    [
        "def test_case():\n    pass",
        "import pytest\n@pytest.mark.train\ndef test_case():\n    pytest.skip('forced skip')",
        "import pytest\n@pytest.mark.train\n@pytest.mark.skip\ndef test_case():\n    pass",
        "import pytest\n@pytest.mark.train\n@pytest.mark.xfail\ndef test_case():\n    assert False",
        "import pytest\n@pytest.mark.train\n@pytest.mark.xfail(strict=False)\n"
        "def test_case():\n    pass",
        "import pytest\n@pytest.mark.train\ndef test_case():\n"
        "    pytest.importorskip('_missing_hallmark_training_extra_')",
        "import pytest\npytest.importorskip('_missing_hallmark_training_extra_')",
        "import pytest\n@pytest.fixture\ndef setup():\n    pytest.skip('setup skip')\n"
        "@pytest.mark.train\ndef test_case(setup):\n    pass",
        "import pytest\n@pytest.fixture\ndef cleanup():\n    yield\n"
        "    pytest.skip('teardown skip')\n"
        "@pytest.mark.train\ndef test_case(cleanup):\n    pass",
        "import pytest\n@pytest.mark.train\ndef test_pass():\n    pass\n"
        "@pytest.mark.train\ndef test_skip():\n    pytest.skip('partial skip')",
        "import pytest\n@pytest.mark.train\ndef test_case():\n    assert False",
    ],
    ids=[
        "no-training",
        "call-skip",
        "marker-skip",
        "xfail",
        "xpass",
        "missing-extra",
        "collection-skip",
        "setup-skip",
        "teardown-skip",
        "partial-pass",
        "assertion-failure",
    ],
)
def test_required_training_rejects_missing_or_incomplete_execution(
    suite: pytest.Pytester, source: str
) -> None:
    suite.makepyfile(source)
    result = suite.runpytest_subprocess("--require-train", "-q", timeout=20)
    assert result.ret in (pytest.ExitCode.TESTS_FAILED, pytest.ExitCode.NO_TESTS_COLLECTED)


@pytest.mark.parametrize("mode", [("--collect-only",), ("--setup-only",), ("-m", "not train")])
def test_collection_or_setup_alone_is_not_training(
    suite: pytest.Pytester, mode: tuple[str, ...]
) -> None:
    suite.makepyfile("import pytest\n@pytest.mark.train\ndef test_case():\n    pass\n")
    result = suite.runpytest_subprocess("--require-train", "-q", *mode, timeout=20)
    assert result.ret in (pytest.ExitCode.TESTS_FAILED, pytest.ExitCode.NO_TESTS_COLLECTED)


def test_required_training_accepts_complete_parametrized_execution(suite: pytest.Pytester) -> None:
    suite.makepyfile(
        "import pytest\n@pytest.mark.train\n@pytest.mark.parametrize('x', [1, 2])\n"
        "def test_case(x):\n    assert x > 0\n"
    )
    result = suite.runpytest_subprocess("--require-train", "-m", "train", "-q", timeout=20)
    result.assert_outcomes(passed=2)
    assert result.ret == pytest.ExitCode.OK


def test_core_only_run_can_skip_training(suite: pytest.Pytester) -> None:
    suite.makepyfile(
        "import pytest\n@pytest.mark.train\ndef test_case():\n    pytest.skip('optional extra')\n"
    )
    result = suite.runpytest_subprocess("-q", timeout=20)
    result.assert_outcomes(skipped=1)
    assert result.ret == pytest.ExitCode.OK
