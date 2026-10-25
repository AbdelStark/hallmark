"""Caller-owned statement for the fixed, public LLM/classifier composition."""

import secrets
from pathlib import Path

from hallmark._gnark_probe import digest, read_regular
from hallmark.integrity import parse_json
from hallmark.openings import TranscriptOpening
from hallmark.policy import RequestExpectation
from hallmark.wire import H

ROOT = Path(__file__).resolve().parents[1]
CASE_SHA256 = "2ca533976d119b656a987bd1750472132b22abb71eb59593b64f53413eb70075"


def case():
    raw = read_regular(ROOT / "research/probes/sash/response-case.json", 1024**2)
    if digest(raw) != CASE_SHA256:
        raise ValueError("composed LLM case changed")
    return parse_json(raw.decode())


def model_identity(value):
    return H(
        "model",
        dict(
            schema_id="hallmark/sash-research-model/1",
            checkpoint=value["model"],
            quantization=value["spec"],
            calibration_sha256=value["calibration_sha256"],
            source=value["source"],
        ),
    )


def request(policy):
    value = case()
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-proved-request",
        nonce=secrets.token_bytes(32),
        interaction_id=secrets.token_bytes(32),
        model=model_identity(value),
        policy=policy.identity(),
        continuity=None,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=bytes(32),
        prompt=value["prompt"],
        response=value["response"],
        salt=secrets.token_bytes(32),
    )
    return expected, opening


def check_request(opening, expected):
    """Bind opened text to the enrolled tokens; tokenization was enrolled separately."""
    value = case()
    opening, expected = opening._validated(), expected._validated()
    if (
        opening.prompt != value["prompt"]
        or opening.response != value["response"]
        or opening.system_ref != bytes(32)
        or expected.model != model_identity(value)
    ):
        raise ValueError("LLM/classifier request mismatch")
