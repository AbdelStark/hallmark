"""Native export and caller-reconstructed rows for the preselected contextual CNN."""

from fractions import Fraction

import contextual_cnn as cnn

from hallmark._worker import digest
from hallmark.integer_encoder import execute_encoder
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.policy import RequestExpectation
from hallmark.receipts import ProofInputs
from hallmark.wire import H

THRESHOLD = -3733


def export(q):
    e = cnn.export(q, threshold=THRESHOLD)
    if len(q["values"]["bias"]) != 32:
        raise ValueError("proof requires the 32-channel CNN")
    p, f = q["values"], q["fractions"]
    e["model"] = dict(
        schema_id="hallmark.contextual-cnn-graph/1",
        program=e["program"].identity().hex(),
        input_profile=e["profile"].identity().hex(),
        arithmetic=e["arithmetic"].identity().hex(),
        weights_sha256=digest(e["weights"]),
        embedding_fraction=f["embedding"],
        kernel_fraction=f["kernel"],
        head_fraction=f["head"],
        embedding=p["embedding"],
        kernel=p["kernel"],
        bias=p["bias"],
        head=p["head"][0],
        output_bias=p["out"][0],
    )
    return e


def native_row(e, c, capacity, prompt, index):
    if type(capacity) is not int or capacity not in (8, 96) or len(prompt.encode()) > capacity:
        raise ValueError("proof capacity exceeded")
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-contextual-cnn",
        nonce=bytes([index + 1]) * 32,
        interaction_id=bytes([index + 10]) * 32,
        model=b"m" * 32,
        policy=H("policy", [c.identity(), c.threshold]),
        continuity=None,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt=prompt,
        response="Synthetic response; no inference provenance claim.",
        salt=b"t" * 32,
    )
    result = execute_encoder(
        opening,
        c,
        e["program"],
        e["profile"],
        e["arithmetic"],
        **{k: e[k] for k in ("weights", "tokenizer", "parameters")},
    )
    public = ProofInputs(
        schema_id="hallmark/proof-inputs/1",
        context=opening.context(expected),
        classifier=c.identity(),
        input_digest=result.input_digest,
        unit_count=result.unit_count,
        chunk_count=1,
        threshold=c.threshold,
        verdict=result.verdict,
    )
    public.validate_profile(c, e["profile"])
    row = dict(public=list(public.to_fields()))
    row["salt"] = list(derive_input_salt(opening.salt, c.identity()))
    tensors = result.chunks[0].tensors
    trace, model = [], e["model"]
    for pos in range(96):
        values = tensors["flat"][pos * 96 : (pos + 1) * 96]
        for h in range(32):
            acc = model["bias"][h] + sum(
                x * w for x, w in zip(values, model["kernel"][h], strict=True)
            )
            z = tensors["convolution"][pos * 32 + h]
            assert z == round(
                Fraction(acc, 2 ** (model["embedding_fraction"] + model["kernel_fraction"])) * 256
            )
            trace.extend((acc, z, tensors["relu"][pos * 32 + h]))
    pooled = tensors["pooled"]
    output = model["output_bias"] + sum(x * w for x, w in zip(pooled, model["head"], strict=True))
    assert result.score == round(Fraction(output, 2 ** model["head_fraction"]))
    row["trace"] = trace + list(pooled) + [output, result.score]
    return row, dict(
        expected_cbor_hex=expected.encode().hex(),
        opening_cbor_hex=opening.encode().hex(),
        public_cbor_hex=public.encode().hex(),
        native_score=result.score,
        verdict=result.verdict,
    )
