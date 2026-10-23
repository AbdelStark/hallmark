"""Generate and extract the fixed TinyLlama case with the pinned SASH environment."""

import gc
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main(model, output, case_path):
    import numpy as np
    import torch
    from harness.witness.common import SPECS, setup
    from harness.witness.model import Cache, Model
    from harness.witness.ppl import attention_scales
    from harness.witness.selftest import test_primitives
    from transformers import AutoModelForCausalLM, AutoTokenizer

    case = json.loads(case_path.read_text())
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    setup()
    require(test_primitives(), "SASH primitive checks failed")
    for name, pin in case["model"]["files"].items():
        path = model / name
        require(
            path.stat().st_size == pin["bytes"] and sha(path) == pin["sha256"],
            f"changed model file: {name}",
        )
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, trust_remote_code=False)
    tokens = tokenizer.apply_chat_template(
        [{"role": "user", "content": case["prompt"]}],
        add_generation_prompt=True,
        return_tensors="pt",
        return_dict=True,
    )["input_ids"][0]
    require(tokens.tolist() == case["prompt_ids"], "tokenizer or prompt changed")
    require(
        tokenizer.decode(case["answer_ids"], skip_special_tokens=True) == case["response"],
        "detokenization changed",
    )
    reference = AutoModelForCausalLM.from_pretrained(
        model, dtype=torch.float32, local_files_only=True, trust_remote_code=False
    ).eval()
    with torch.inference_mode():
        reference_logits = reference(tokens.unsqueeze(0)).logits[0].float()
    del reference
    gc.collect()
    native = Model(str(model), SPECS["fp32"])
    logits, _ = native.forward(tokens)
    difference = float((reference_logits - logits).abs().max())
    require(
        difference < 0.05 and torch.equal(reference_logits.argmax(-1), logits.argmax(-1)),
        "reference compatibility failed",
    )
    del native, logits, reference_logits
    gc.collect()
    calibrator = Model(str(model), SPECS["bf16-only"])
    calibrator.attn_calib = {}
    for text in case["calibration_texts"]:
        calibrator.forward(torch.tensor(tokenizer.encode(text)))
    ranges = {
        key: torch.stack(value).amax(0).tolist() for key, value in calibrator.attn_calib.items()
    }
    calibration = output / "attn-ranges.json"
    calibration.write_text(json.dumps(ranges, indent=1, sort_keys=True) + "\n")
    require(
        sha(calibration) == case["calibration_sha256"], "calibration differs from enrolled case"
    )
    del calibrator
    gc.collect()
    spec = SPECS[case["spec"]]
    native = Model(str(model), spec, attn_scales=attention_scales(spec, str(calibration)))
    logits, cache = native.forward(tokens, Cache(native.L))
    answer = []
    for _ in range(16):
        token = int(logits[-1].argmax())
        answer.append(token)
        if token == tokenizer.eos_token_id:
            break
        logits, cache = native.forward(torch.tensor([token]), cache)
    require(answer == case["answer_ids"], "quantized answer changed")
    del native, logits, cache
    gc.collect()
    np.save(output / "input_ids.npy", np.array(case["prompt_ids"] + answer[:-1], dtype=np.int64))
    for name, value in [
        ("prompt_ids", case["prompt_ids"]),
        ("answer_ids", answer),
        ("input_ids", case["prompt_ids"] + answer[:-1]),
    ]:
        (output / f"{name}.json").write_text(json.dumps(value) + "\n")
    commands = []
    common = [
        sys.executable,
        "-m",
        "harness.witness.extract",
        "--tokens",
        "32",
        "--chunk",
        "32",
        "--blocks",
        "all",
        "--spec",
        case["spec"],
        "--ids",
        str(output / "input_ids.npy"),
        "--attn-ranges",
        str(calibration),
        "--diagonal-block",
        "--slim",
    ]
    for name, extra in [
        (
            "layer0",
            ["--layers", "0", "--embed", "--residual-stream", "--out", str(output / "witness")],
        ),
        (
            "layers",
            [
                "--layers",
                ",".join(map(str, range(1, 22))),
                "--residual-stream",
                "--out",
                str(output / "witness"),
            ],
        ),
        ("head", ["--layer", "21", "--head", "--out", str(output / "head")]),
    ]:
        args = common + extra
        print("Extracting " + name, flush=True)
        before = time.monotonic()
        with (
            (output / f"{name}.stdout").open("xb") as stdout,
            (output / f"{name}.stderr").open("xb") as stderr,
        ):
            process = subprocess.run(args, stdout=stdout, stderr=stderr, timeout=300)
        commands.append(
            dict(
                name=name,
                args=args,
                exit_code=process.returncode,
                seconds=time.monotonic() - before,
            )
        )
        (output / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        require(process.returncode == 0, "extraction failed: " + name)
    head = json.loads((output / "head_B0/manifest.json").read_text())
    require(
        head["residual_stream"] == {} and head["head"]["final_norm"] is True,
        "wrong output-head family",
    )
    for i in range(21):
        require(
            (output / f"witness_B0_L{i}/xout.u16").read_bytes()
            == (output / f"witness_B0_L{i + 1}/xin.u16").read_bytes(),
            f"residual mismatch at layer {i}",
        )
    require(
        (output / "witness_B0_L21/xout.u16").read_bytes()
        == (output / "head_B0/xin_head.u16").read_bytes(),
        "head residual mismatch",
    )
    require(
        np.fromfile(output / "head_B0/tok_head.i32", dtype="<i4")[24:32].tolist() == answer,
        "head output mismatch",
    )
    result = dict(
        passed=True,
        prompt=case["prompt"],
        response=case["response"],
        answer_ids=answer,
        max_float_logit_difference=difference,
        calibration_sha256=sha(calibration),
        seconds=time.monotonic() - started,
        proof_produced=False,
    )
    (output / "generation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    require(len(sys.argv) == 4, "usage: prepare_native.py MODEL OUTPUT CASE")
    main(*(Path(arg).resolve() for arg in sys.argv[1:]))
