"""Caller guard tests. Real cryptographic results live in the research evidence."""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/probes/sash"))
import check_response as response

PROBE = Path(__file__).resolve().parents[1] / "research/probes/sash"


def inputs(index=0):
    prompt, answer = [529] * 25, [1576] * 7 + [2]
    params = dict(
        s=32,
        c=0,
        nh=32,
        hd=64,
        head_groups=[16, 8, 8],
        diagonal_block=True,
        round="even",
        log_table=21,
        mats=[dict(name="qkv/v", variant="chain")],
        residual_stream=dict(head_norm=True),
    )
    fixed = dict(
        params=params,
        layer=index,
        block=0,
        log_blowup=1,
        n_queries=100,
        pow_bits=0,
        pre_root="pre",
        model_root="model",
        model="manifest",
    )
    if index == 0:
        fixed["tok_in"] = prompt + answer[:-1]
    if index == 22:
        fixed["tok_out"] = [529] * 24 + answer
    row = dict(
        log_table=21,
        pre_root="pre",
        model_root="model",
        model="manifest",
        frac_per_head=[19.0] * 32,
        shape_key=response.shape_key(params, [19.0] * 32),
    )
    return fixed, row, prompt, answer


@pytest.mark.parametrize(
    "edit,reason",
    [
        (lambda f: f.__setitem__("layer", True), "wrong layer"),
        (lambda f: f.__setitem__("block", 1), "wrong block"),
        (lambda f: f.__setitem__("n_queries", 1), "security parameters"),
        (lambda f: f.__setitem__("model_root", "other"), "wrong model_root"),
        (lambda f: f["params"].__setitem__("q_bits", 1), "unenrolled parameters"),
        (lambda f: f["params"]["mats"][0].__setitem__("variant", "fold"), "open-scale"),
        (lambda f: f["tok_in"].__setitem__(0, True), "invalid token IDs"),
        (lambda f: f["tok_in"].__setitem__(0, 2**32 + 529), "invalid token IDs"),
        (lambda f: f["tok_in"].__setitem__(0, 530), "wrong input tokens"),
    ],
)
def test_statement_mutations(edit, reason):
    fixed, row, prompt, answer = inputs()
    response.statement(fixed, row, 0, prompt, answer)
    edit(fixed)
    with pytest.raises(ValueError, match=reason):
        response.statement(fixed, row, 0, prompt, answer)


def test_head_requires_final_norm_even_with_matching_parameter_digest():
    fixed, row, prompt, answer = inputs(22)
    response.statement(fixed, row, 22, prompt, answer)
    fixed["params"]["residual_stream"]["head_norm"] = False
    row["shape_key"] = response.shape_key(fixed["params"], row["frac_per_head"])
    with pytest.raises(ValueError, match="final norm"):
        response.statement(fixed, row, 22, prompt, answer)


def test_head_covers_final_output_and_calibration():
    fixed, row, prompt, answer = inputs(22)
    bad = copy.deepcopy(fixed)
    bad["tok_out"][-1] = 3
    with pytest.raises(ValueError, match="wrong output tokens"):
        response.statement(bad, row, 22, prompt, answer)
    row["frac_per_head"][0] += 1
    with pytest.raises(ValueError, match="unenrolled parameters"):
        response.statement(fixed, row, 22, prompt, answer)


def test_caller_rejects_the_native_output_token_field_alias():
    fixed, row, prompt, answer = inputs(22)
    fixed["tok_out"][-1] += 2**31 - 1
    with pytest.raises(ValueError, match="invalid token IDs"):
        response.statement(fixed, row, 22, prompt, answer)


@pytest.mark.parametrize("raw", ['{"a":1,"a":2}', "[NaN]", "[Infinity]", ""])
def test_json_rejects_ambiguous_input(tmp_path, raw):
    path = tmp_path / "input.json"
    path.write_text(raw)
    with pytest.raises(ValueError):
        response.read_json(path)


def test_json_rejects_symlink_and_oversize(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"a":1}')
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="invalid JSON file"):
        response.read_json(link)
    with pytest.raises(ValueError, match="invalid JSON file"):
        response.read_json(path, limit=1)


def test_checks_survive_python_optimization():
    result = subprocess.run(
        [sys.executable, "-O", "-c", "import check_response as r; r.token_ids([True], 1)"],
        cwd=PROBE,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "ValueError: invalid token IDs" in result.stderr


def test_missing_segment_rejects_before_proof_verifier(tmp_path):
    fixed, row, prompt, answer = inputs()
    roots = [dict(row, tag=t, layer=i, block=0, c=0) for i, t in enumerate(response.TAGS)]
    (tmp_path / "B0L0.fixed.json").write_text(json.dumps(fixed))
    with pytest.raises(ValueError, match="missing or extra proof files"):
        response.bundle(tmp_path, dict(prompt_ids=prompt, answer_ids=answer, roots=roots))
