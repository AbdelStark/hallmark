"""Caller checks for the fixed TinyLlama response experiment; not a proof verifier.

The caller must enroll roots and tokenize its text independently. A successful
check only admits the bundle to SASH's cryptographic boundary-grid verifier.
"""

import hashlib
import json
import stat
import struct

TAGS = [f"B0L{i}" for i in range(22)] + ["head"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pairs(items):
    out = {}
    for key, value in items:
        require(key not in out, "duplicate JSON key")
        out[key] = value
    return out


def nonfinite(_):
    raise ValueError("nonfinite JSON")


def read_json(path, limit=1048576):
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and 0 < st.st_size <= limit, "invalid JSON file")
    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=nonfinite)


def token_ids(value, length):
    require(
        type(value) is list
        and len(value) == length
        and all(type(x) is int and 0 <= x < 32000 for x in value),
        "invalid token IDs",
    )


def float_bits(value):
    return struct.unpack("<Q", struct.pack("<d", value))[0]


def shape_key(params, fracs):
    require(
        len(fracs) == 32
        and all(type(x) in (int, float) and x == int(x) and 0 <= x < 64 for x in fracs),
        "invalid calibration",
    )
    fracs = list(map(float, fracs))
    master = max(fracs)
    calibration = []
    offset = 0
    for n in params["head_groups"]:
        fs = fracs[offset : offset + n]
        offset += n
        calibration.append(
            dict(
                frac=master,
                frac_bits=float_bits(master),
                frac_per_inst=fs,
                frac_per_inst_bits=list(map(float_bits, fs)),
                delta=[1 << int(master - x) for x in fs],
            )
        )
    inputs = dict(version="zk-shape-root-v1", params=params, calibration=calibration)
    raw = json.dumps(inputs, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def statement(fixed, row, index, prompt, answer):
    p = fixed["params"]
    require(type(fixed["layer"]) is int and fixed["layer"] == index, "wrong layer")
    require(type(fixed["block"]) is int and fixed["block"] == 0, "wrong block")
    require((p["s"], p["c"], p["nh"], p["hd"]) == (32, 0, 32, 64), "wrong shape")
    require(p["head_groups"] == [16, 8, 8] and p["diagonal_block"] is True, "wrong groups")
    require(p["round"] == "even" and p["log_table"] == row["log_table"], "wrong arithmetic")
    require(
        (fixed["log_blowup"], fixed["n_queries"], fixed["pow_bits"]) == (1, 100, 0),
        "wrong security parameters",
    )
    for key in ("pre_root", "model_root", "model"):
        require(fixed[key] == row[key], f"wrong {key}")
    require(
        all(m["variant"] == ("pow2" if m["name"] == "lm_head" else "chain") for m in p["mats"]),
        "open-scale matmul profile",
    )
    require(shape_key(p, row["frac_per_head"]) == row["shape_key"], "unenrolled parameters")
    if index == 0:
        token_ids(fixed["tok_in"], 32)
        require(fixed["tok_in"] == prompt + answer[:-1], "wrong input tokens")
    else:
        require(fixed.get("tok_in", []) == [], "unexpected input tokens")
    if index == 22:
        require(p["residual_stream"]["head_norm"] is True, "head must prove its final norm")
        token_ids(fixed["tok_out"], 32)
        require(fixed["tok_out"][24:32] == answer, "wrong output tokens")
    else:
        require(fixed.get("tok_out", []) == [], "unexpected output tokens")


def bundle(directory, expected):
    prompt, answer = expected["prompt_ids"], expected["answer_ids"]
    token_ids(prompt, 25)
    token_ids(answer, 8)
    require(answer[-1] == 2, "answer must include EOS")
    roots = expected["roots"]
    require([x["tag"] for x in roots] == TAGS, "wrong segment coverage")
    wanted = {f"{tag}.{kind}.json" for tag in TAGS for kind in ("fixed", "claims", "proof")}
    require({p.name for p in directory.iterdir()} == wanted, "missing or extra proof files")
    for i, (tag, row) in enumerate(zip(TAGS, roots, strict=True)):
        require((row["layer"], row["block"], row["c"]) == (i, 0, 0), "wrong root coordinates")
        for kind in ("claims", "proof"):
            st = (directory / f"{tag}.{kind}.json").lstat()
            require(
                stat.S_ISREG(st.st_mode) and 0 < st.st_size <= 128 * 1024**2, "invalid proof file"
            )
        statement(read_json(directory / f"{tag}.fixed.json"), row, i, prompt, answer)
