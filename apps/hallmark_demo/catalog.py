"""Workflow definitions; proof semantics remain in the existing frozen drivers."""

import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path


@dataclass(frozen=True)
class Stage:
    id: str
    title: str
    markers: tuple[str, ...]


@dataclass(frozen=True)
class Example:
    title: str
    prompt: str
    response: str
    note: str


@dataclass(frozen=True)
class Parameter:
    name: str
    label: str
    hint: str = ""
    kind: str = "text"
    required: bool = False
    default: str = ""
    suggestions: str | None = None
    read_only: bool = False


@dataclass(frozen=True)
class Workflow:
    id: str
    title: str
    summary: str
    scheme: str
    claim: str
    duration: str
    disk_gib: int
    paid_ceiling: str | None
    fields: tuple[Parameter, ...]
    stages: tuple[Stage, ...]
    schema: str | None
    docs: str
    mac_only: bool = True
    example: Example | None = None
    local_when: str | None = None

    def public(self):
        return asdict(self)


LLM_EXAMPLE = Example(
    title="Fixed TinyLlama case",
    prompt="Name the capital of France in one short sentence.",
    response="The capital of France is Paris.",
    note="Pinned quantized TinyLlama-1.1B; 23 linked proof segments through EOS.",
)
LLM_RUN = Parameter(
    "llm_run",
    "Retained LLM run",
    "Paste a directory under runs/; the driver rechecks admission.",
    kind="retained",
    suggestions="llm_run",
)
CLASSIFIER_RUN = Parameter(
    "classifier_run",
    "Classifier preparation",
    "Optional: reuse a completed classifier run.",
    kind="retained",
    suggestions="classifier_run",
)
BUILD_RUN = Parameter(
    "build_run",
    "Cached CUDA build",
    "Optional: reuse an admitted completed CUDA build.",
    kind="retained",
    suggestions="build_run",
)
BALANCE = Parameter(
    "balance",
    "Current prepaid HF balance · USD",
    "Check available prepaid credits immediately before launch.",
    kind="money",
    required=True,
)
LLM_COST = Parameter(
    "max_cost",
    "Maximum paid job cost · USD",
    "At most $2.50, including startup windows. No top-ups or automatic retries.",
    kind="money",
    required=True,
    default="2.50",
)
GPU_COST = Parameter(
    "max_cost",
    "Maximum paid job cost · USD",
    "At most $5.00. No top-ups or automatic job retries.",
    kind="money",
    required=True,
    default="5.00",
)
CIRCLE_STAGES = (
    Stage("mlp", "Train and export MLP", ("mlp-training",)),
    Stage("cnn", "Train and export CNN", ("cnn-training",)),
    Stage(
        "compile", "Build Circle prover and verifier", ("circle-prove-build", "circle-verify-build")
    ),
    Stage("prove", "Prove and check request bindings", ("circle-proofs",)),
)

WORKFLOWS = (
    Workflow(
        id="classifiers-circle",
        title="Circle STARK classifiers",
        summary="Train an MLP and CNN; prove three classifiers on three requests.",
        scheme="STWO / Circle STARK",
        claim="Nine Circle proofs, freshly verified against caller-owned requests.",
        duration="Minutes + first build",
        disk_gib=12,
        paid_ceiling=None,
        fields=(CLASSIFIER_RUN,),
        stages=CIRCLE_STAGES,
        schema="hallmark.circle-e2e-result/1",
        docs="docs/DEMO.md",
    ),
    Workflow(
        id="composed-circle",
        title="End-to-end Circle STARK",
        summary="Verify TinyLlama and bind three fresh Circle classifier proofs to its request.",
        scheme="SASH + STWO / Circle STARK",
        claim="23 linked LLM proofs and three classifier proofs joined by the host; no recursion.",
        duration="Minutes with retained LLM proofs; about 1 hour fresh",
        disk_gib=32,
        paid_ceiling="2.50",
        fields=(LLM_RUN, CLASSIFIER_RUN, replace(LLM_COST, read_only=True)),
        stages=(
            Stage("verify", "Fresh LLM verification", ("Building the verifier", "Verifying twice")),
            *CIRCLE_STAGES,
        ),
        schema="hallmark.circle-composed-request-result/1",
        docs="docs/COMPOSED-DEMO.md",
        example=LLM_EXAMPLE,
        local_when="llm_run",
    ),
    Workflow(
        id="llm",
        title="TinyLlama response",
        summary="Prove the fixed short answer through EOS using bounded HF CPU jobs.",
        scheme="SASH / Circle STARK",
        claim="23 linked segments for the pinned quantized TinyLlama-1.1B case.",
        duration="About 30–60 min",
        disk_gib=16,
        paid_ceiling="2.50",
        fields=(LLM_COST,),
        stages=(
            Stage("prepare", "Prepare model and witnesses", ("python", "Downloading", "witness")),
            Stage("build", "Build prover on HF", ("build:",)),
            Stage("prove", "Prove all 23 segments", ("prove:",)),
            Stage("verify", "Fresh CPU verification", ("verify:",)),
            Stage("checks", "Retain evidence and clean up", ("retention",)),
        ),
        schema="hallmark.llm-e2e-result/1",
        docs="docs/LLM-PROOF.md",
        example=LLM_EXAMPLE,
    ),
    Workflow(
        id="verify-llm",
        title="Verify retained LLM proofs",
        summary="Rebuild the enrolled native verifier and check a retained bundle.",
        scheme="SASH / native Mac",
        claim="Fresh verification of existing proofs; no new LLM inference or proving.",
        duration="Seconds after compilation",
        disk_gib=8,
        paid_ceiling=None,
        fields=(replace(LLM_RUN, required=True),),
        stages=(
            Stage("prepare", "Admit retained proof bundle", ("enrollment",)),
            Stage("compile", "Build enrolled native verifier", ("Building the verifier",)),
            Stage("verify", "Verify proofs and mutations", ("Verifying twice",)),
        ),
        schema="hallmark.native-llm-result/1",
        docs="docs/LLM-PROOF.md#verify-retained-proofs-on-your-mac",
        example=LLM_EXAMPLE,
    ),
    Workflow(
        id="gpu",
        title="CPU / GPU prover benchmark",
        summary="Run matched SIMD and CUDA proving on one H200, then verify.",
        scheme="SASH / generated CUDA",
        claim="Same fixed relation and inputs on both backends; paid remote execution.",
        duration="About 35 min with cached build",
        disk_gib=16,
        paid_ceiling="5.00",
        fields=(replace(LLM_RUN, required=True), BUILD_RUN, BALANCE, GPU_COST),
        stages=(
            Stage("prepare", "Admit retained preparation", ("Inputs",)),
            Stage("build", "Build generated CUDA prover", ("build:",)),
            Stage("prove", "Matched SIMD / CUDA run", ("prove:",)),
            Stage("verify", "Fresh CPU / Mac verification", ("verify:", "Building the verifier")),
            Stage("checks", "Compare artifacts and retain outputs", ("retention",)),
        ),
        schema="hallmark.llm-gpu-result/1",
        docs="docs/GPU-BENCHMARK.md",
        example=LLM_EXAMPLE,
    ),
    Workflow(
        id="conformance",
        title="Software conformance",
        summary="Check the frozen software contracts without generating a proof.",
        scheme="Software check",
        claim="156 software cases; no cryptographic proof or hardware attestation.",
        duration="A few seconds",
        disk_gib=1,
        paid_ceiling=None,
        fields=(),
        stages=(Stage("check", "Run software conformance cases", ()),),
        schema=None,
        docs="docs/START.md",
        mac_only=False,
    ),
)
CATALOG = {item.id: item for item in WORKFLOWS}


def money(value, ceiling=None):
    if not isinstance(value, str) or len(value) > 16:
        raise ValueError("Enter a decimal dollar amount")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("Enter a decimal dollar amount") from None
    if not number.is_finite() or number <= 0 or (ceiling and number > Decimal(ceiling)):
        raise ValueError(
            f"Amount must be positive and at most ${ceiling}"
            if ceiling
            else "Amount must be positive"
        )
    return str(number)


def retained_path(root, value, required=False):
    if not value and not required:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("Select a retained run")
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    if (
        not resolved.is_relative_to((root / "runs").resolve())
        or path.is_symlink()
        or not resolved.is_dir()
    ):
        raise ValueError("Retained inputs must be existing directories under this checkout’s runs/")
    return resolved


def plan(root, workflow, parameters, uv):
    if not isinstance(parameters, dict) or set(parameters) - {
        field.name for field in workflow.fields
    }:
        raise ValueError("Unknown workflow parameter")
    if any(not isinstance(value, str) for value in parameters.values()):
        raise ValueError("Workflow parameters must be strings")
    parameters = {
        field.name: parameters.get(field.name, field.default)
        for field in workflow.fields
        if parameters.get(field.name, field.default)
    }
    for field in workflow.fields:
        if field.required and not parameters.get(field.name):
            raise ValueError("Required: " + field.label)
    args = [str(uv), "run", "--locked", "--python", "3.12.12"]
    paid = workflow.paid_ceiling is not None
    llm = retained_path(root, parameters.get("llm_run"), workflow.id in {"verify-llm", "gpu"})
    classifier = retained_path(root, parameters.get("classifier_run"))
    build = retained_path(root, parameters.get("build_run"))
    maximum = (
        money(parameters.get("max_cost", workflow.paid_ceiling), workflow.paid_ceiling)
        if paid
        else None
    )
    if workflow.id == "classifiers-circle":
        args += ["--extra", "train", "python", "scripts/run_circle_e2e.py"]
        if classifier:
            args += ["--classifier-run", str(classifier)]
    elif workflow.id == "llm":
        args += ["--extra", "llm", "python", "scripts/run_llm_e2e.py", "--max-cost-usd", maximum]
    elif workflow.id == "verify-llm":
        args += ["python", "scripts/verify_llm.py", "--run", str(llm)]
    elif workflow.id == "composed-circle":
        args += ["--extra", "train", "--extra", "llm", "python", "scripts/run_circle_composed.py"]
        if llm:
            args += ["--llm-run", str(llm)]
            paid = False
        if classifier:
            args += ["--classifier-run", str(classifier)]
        if Decimal(maximum) != Decimal(workflow.paid_ceiling):
            raise ValueError("Composed runs use the displayed fixed startup-inclusive ceiling")
    elif workflow.id == "gpu":
        args += [
            "--extra",
            "llm",
            "python",
            "scripts/run_llm_gpu.py",
            "--llm-run",
            str(llm),
            "--credit-balance-usd",
            money(parameters.get("balance")),
            "--max-cost-usd",
            maximum,
        ]
        if build:
            args += ["--build-run", str(build)]
    elif workflow.id == "conformance":
        args += [
            "python",
            "scripts/check_conformance.py",
            "--corpus",
            "tests/vectors/v1/corpus.json",
            "--expected-corpus",
            (root / "tests/vectors/v1/corpus.id").read_text().strip(),
            "--software-only",
            "--self-test",
        ]
    else:
        raise ValueError("Workflow has no command adapter")
    adapter = workflow.id in {"llm", "gpu", "composed-circle"}
    if adapter:
        index = next(i for i, item in enumerate(args) if item.startswith("scripts/"))
        args[index : index + 1] = [
            str(Path(__file__).with_name("execute.py")),
            "--root",
            str(root),
            "--workflow",
            workflow.id,
        ]
        if workflow.id == "composed-circle":
            args += ["--max-cost-usd", maximum]
    return dict(
        command=args,
        paid=paid,
        ceiling=maximum if paid else "0",
        parameters=parameters,
        monitor_adapter=adapter,
    )


def preflight(root, workflow, uv, parameters=None):
    checks = []

    def add(label, ok, detail):
        checks.append(dict(label=label, ok=bool(ok), detail=detail))

    add("Checkout", (root / "research/probes/sash/response-case.json").is_file(), str(root))
    add(
        "Platform",
        not workflow.mac_only or (platform.system(), platform.machine()) == ("Darwin", "arm64"),
        "Apple Silicon Mac" if workflow.mac_only else "macOS / Linux",
    )
    required = workflow.disk_gib
    if workflow.id == "composed-circle" and (parameters or {}).get("llm_run"):
        required = 12
    free = shutil.disk_usage(root).free / 1024**3
    add(
        "Free storage",
        free >= required,
        f"{free:.1f} GiB available / {required} GiB required",
    )
    try:
        version = subprocess.check_output([str(uv), "--version"], text=True, timeout=5).split()[:2]
    except (OSError, subprocess.SubprocessError):
        version = []
    add("Frozen tool", version == ["uv", "0.9.18"], "uv 0.9.18 supplied by the app environment")
    if workflow.id in {"verify-llm", "classifiers-circle", "composed-circle"}:
        add("Rust", shutil.which("cargo"), "Native verifier needs the documented Rust toolchain")
    return checks
