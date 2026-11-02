"""exp-R1: time the caller's native rerun for the paper's verify-versus-rerun comparison (REV-14).

Two parts, both local, no paid compute:
  classifiers  rule, MLP and CNN native execution on the three frozen C1 requests (repo env).
  llm          TinyLlama greedy answer: the proved quantized relation (y-attnout-w12) and the fp32
               reference, inside the pinned SASH harness env built by `llm-setup`.
Each part writes a new JSON record next to this script; nothing is overwritten.
"""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CASE = ROOT / "research/probes/sash/response-case.json"


def stats(samples):
    return dict(
        n=len(samples),
        median_s=statistics.median(samples),
        min_s=min(samples),
        max_s=max(samples),
    )


def timed(fn, reps, warmup):
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(reps):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return stats(samples)


def host():
    def out(*command):
        result = subprocess.run(command, cwd=HERE, capture_output=True, text=True, check=False)
        return result.stdout.strip() or None

    if sys.platform == "darwin":
        cpu_model = out("sysctl", "-n", "machdep.cpu.brand_string")
    else:
        cpu_model = platform.processor() or None
    return dict(
        commit=out("git", "rev-parse", "HEAD"),
        cpu_model=cpu_model,
        platform=platform.platform(),
        machine=platform.machine(),
        python=platform.python_version(),
        cpu_count=os.cpu_count(),
        omp_num_threads=os.environ.get("OMP_NUM_THREADS"),
    )


def write_record(name, record):
    path = HERE / f"{name}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json"
    with path.open("x") as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(path)


def classifiers(run_dir, reps, warmup):
    sys.path.insert(0, str(ROOT / "scripts"))
    import circle_inputs
    import classifier_comparison as comparison
    import trained_common_input as common

    from hallmark.openings import TranscriptOpening

    records, _ = circle_inputs.native_templates(comparison.exports(run_dir))
    _, corpus = comparison.documents()
    executes = dict(
        zip(
            common.KINDS,
            (common.execute_rule, common.execute_mlp, common.execute_encoder),
            strict=True,
        )
    )
    rows = []
    for case in corpus["requests"]:
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=bytes(32),
            prompt=case["prompt"],
            response="Synthetic response; no inference claim.",
            salt=bytes(32),
        )
        for kind, n in zip(common.KINDS, records, strict=True):
            c, p, profile, arithmetic = (
                n[k] for k in ("classifier", "program", "input_profile", "arithmetic")
            )

            def run(
                execute=executes[kind], args=(opening, c, p, profile, arithmetic), files=n["files"]
            ):
                return execute(*args, **files)

            rows.append(
                dict(
                    request=case["id"],
                    classifier=kind,
                    verdict=run().verdict,
                    **timed(run, reps, warmup),
                )
            )
    write_record(
        "classifiers",
        dict(
            schema_id="hallmark.paper.exp-R1-classifiers/1",
            experiment_id="exp-R1-native-rerun",
            boundary="one in-process native execute_* call per classifier and request; "
            "excludes artifact loading, export and witness construction",
            run_dir=str(run_dir),
            host=host(),
            rows=rows,
        ),
    )


def llm_setup(work):
    case = json.loads(CASE.read_text())
    sys.path.insert(0, str(ROOT / "scripts"))
    from huggingface_hub import hf_hub_download
    from run_llm_e2e import fetch, patch_source, require, sha

    work.mkdir(parents=True, exist_ok=False)
    archive = work / "source.tar.gz"
    fetch(case["source"]["url"], archive, case["source"]["sha256"], case["source"]["bytes"])
    unpacked = work / "source"
    unpacked.mkdir()
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(unpacked, filter="data")
    (source,) = list(unpacked.iterdir())
    env = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR", "LANG") if k in os.environ}
    patch_source(source, work, env, time.monotonic() + 1800)
    subprocess.run(
        ["uv", "sync", "--project", source / "harness", "--locked", "--python", "3.12.12"],
        env=env | {"UV_PROJECT_ENVIRONMENT": str(work / "witness-env")},
        check=True,
    )
    for name, pin in case["model"]["files"].items():
        path = Path(
            hf_hub_download(
                case["model"]["id"],
                name,
                revision=case["model"]["revision"],
                local_dir=work / "model",
                token=False,
            )
        )
        require(
            path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"],
            "model mismatch: " + name,
        )
    print(f"ready: run `llm` with --work {work}")


def llm(work, reps, warmup):
    """Runs inside the SASH harness env; mirrors prepare_native.py's decode."""
    import torch
    from harness.witness.common import SPECS, setup
    from harness.witness.model import Cache, Model
    from harness.witness.ppl import attention_scales
    from transformers import AutoModelForCausalLM, AutoTokenizer

    case = json.loads(CASE.read_text())
    model_dir = work / "model"
    setup()
    tokenizer = AutoTokenizer.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False
    )
    tokens = torch.tensor(case["prompt_ids"])
    calibrator = Model(str(model_dir), SPECS["bf16-only"])
    calibrator.attn_calib = {}
    for text in case["calibration_texts"]:
        calibrator.forward(torch.tensor(tokenizer.encode(text)))
    ranges = {k: torch.stack(v).amax(0).tolist() for k, v in calibrator.attn_calib.items()}
    calibration = work / "attn-ranges.json"
    calibration.write_text(json.dumps(ranges, indent=1, sort_keys=True) + "\n")
    del calibrator
    spec = SPECS[case["spec"]]
    quantized = Model(str(model_dir), spec, attn_scales=attention_scales(spec, str(calibration)))

    def greedy_quantized():
        logits, cache = quantized.forward(tokens, Cache(quantized.L))
        answer = []
        for _ in range(16):
            token = int(logits[-1].argmax())
            answer.append(token)
            if token == tokenizer.eos_token_id:
                break
            logits, cache = quantized.forward(torch.tensor([token]), cache)
        return answer

    reference = AutoModelForCausalLM.from_pretrained(
        model_dir, dtype=torch.float32, local_files_only=True, trust_remote_code=False
    ).eval()

    def greedy_reference():
        with torch.inference_mode():
            out = reference.generate(
                tokens.unsqueeze(0),
                max_new_tokens=16,
                do_sample=False,
                eos_token_id=tokenizer.eos_token_id,
            )
        return out[0, len(case["prompt_ids"]) :].tolist()

    quantized_answer = greedy_quantized()
    reference_answer = greedy_reference()
    write_record(
        "llm",
        dict(
            schema_id="hallmark.paper.exp-R1-llm/1",
            experiment_id="exp-R1-native-rerun",
            boundary="one greedy answer through EOS on CPU from loaded weights; "
            "excludes model load, calibration and tokenization; "
            "torch threads as set by OMP_NUM_THREADS",
            quantized=dict(
                spec=case["spec"],
                answer_matches_proved_case=quantized_answer == case["answer_ids"],
                **timed(greedy_quantized, reps, warmup),
            ),
            fp32_reference=dict(
                answer_ids=reference_answer,
                matches_proved_answer=reference_answer == case["answer_ids"],
                **timed(greedy_reference, reps, warmup),
            ),
            torch_threads=torch.get_num_threads(),
            host=host(),
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="part", required=True)
    c = sub.add_parser("classifiers")
    c.add_argument(
        "--run-dir", type=Path, required=True, help="local classifier run with the frozen exports"
    )
    c.add_argument("--reps", type=int, default=50)
    s = sub.add_parser("llm-setup")
    s.add_argument("--work", type=Path, required=True)
    m = sub.add_parser("llm")
    m.add_argument("--work", type=Path, required=True)
    m.add_argument("--reps", type=int, default=5)
    args = parser.parse_args()
    if args.part == "classifiers":
        classifiers(args.run_dir.resolve(), args.reps, warmup=3)
    elif args.part == "llm-setup":
        llm_setup(args.work.resolve())
    else:
        llm(args.work.resolve(), args.reps, warmup=1)


if __name__ == "__main__":
    main()
