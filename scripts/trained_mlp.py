"""Native export and caller-reconstructed rows for the frozen trained MLP."""

from hallmark._worker import digest
from hallmark.classifier_manifest import InputProfile
from hallmark.integer_mlp import execute_mlp
from hallmark.mlp_export import compile_mlp
from hallmark.openings import TranscriptOpening, derive_input_salt
from hallmark.policy import RequestExpectation
from hallmark.receipts import ProofInputs
from hallmark.wire import H

CASES = (8, 1024)


def export(quantization):
    q = quantization._validated()
    if len(q.weights.hidden_bias) != 4:
        raise ValueError("unsupported trained MLP width")
    profile = InputProfile(
        schema_id="hallmark/input-profile/1",
        encoding="utf8-bytes",
        tokenizer_files=(),
        prefix_tokens=(),
        suffix_tokens=(),
        chunk_size=512,
        overlap=0,
        max_units=32768,
        padding_id=0,
        padding_side="right",
    )
    program, arithmetic, weights, parameters = compile_mlp(
        q.weights,
        profile,
        first_fraction=q.first_fraction,
        hidden_fraction=0,
        last_fraction=q.last_fraction,
    )
    model = dict(
        schema_id="hallmark.trained-mlp-graph/1",
        program=program.identity().hex(),
        input_profile=profile.identity().hex(),
        arithmetic=arithmetic.identity().hex(),
        weights_sha256=digest(weights),
        first_fraction=q.first_fraction,
        last_fraction=q.last_fraction,
        **q.weights.model_dump(mode="json", exclude={"schema_id"}),
    )
    return dict(
        model=model,
        program=program,
        profile=profile,
        arithmetic=arithmetic,
        weights=weights,
        parameters=parameters,
    )


def native_row(exported, c, capacity, prompt, index):
    if type(capacity) is not int or capacity not in CASES or len(prompt.encode()) > capacity:
        raise ValueError("proof capacity exceeded")
    expected = RequestExpectation(
        schema_id="hallmark/request-expectation/1",
        audience="local-trained-mlp",
        nonce=bytes([index + 1]) * 32,
        interaction_id=bytes([index + 10]) * 32,
        model=b"m" * 32,
        policy=H("policy", [c.identity(), 0]),
        continuity=None,
    )
    opening = TranscriptOpening(
        schema_id="hallmark/transcript-opening/1",
        system_ref=b"s" * 32,
        prompt=prompt,
        response="Synthetic response; no inference claim.",
        salt=b"t" * 32,
    )

    def execute(o):
        return execute_mlp(
            o,
            c,
            exported["program"],
            exported["profile"],
            exported["arithmetic"],
            weights=exported["weights"],
            parameters=exported["parameters"],
        )

    result = execute(opening)
    public = ProofInputs(
        schema_id="hallmark/proof-inputs/1",
        context=opening.context(expected),
        classifier=c.identity(),
        input_digest=result.input_digest,
        unit_count=result.unit_count,
        chunk_count=len(result.chunks),
        threshold=c.threshold,
        verdict=result.verdict,
    )
    public.validate_profile(c, exported["profile"])
    row = dict(public=list(public.to_fields()))
    row["salt"] = list(derive_input_salt(opening.salt, c.identity()))
    chunks = list(result.chunks)
    if len(chunks) < (capacity + 511) // 512:
        chunks += list(execute(opening.model_copy(update={"prompt": ""})).chunks)
    row["trace"] = [
        v
        for chunk in chunks
        for v in (
            *chunk.hidden_accumulators,
            *chunk.hidden,
            *chunk.activated,
            chunk.output_accumulator,
            chunk.score,
        )
    ]
    return row, dict(
        opening_cbor_hex=opening.encode().hex(),
        expected_cbor_hex=expected.encode().hex(),
        classifier_cbor_hex=c.encode().hex(),
        native_score=result.score,
        verdict=result.verdict,
    )
