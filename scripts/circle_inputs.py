"""Caller-owned native preparation; proof enrollment is supplied by Circle later."""

import secrets
from pathlib import Path

import classifier_comparison as comparison
import trained_common_input as common

from hallmark._worker import read_regular, write_new
from hallmark.classifier_manifest import ClassifierManifest
from hallmark.integrity import parse_json
from hallmark.openings import TranscriptOpening
from hallmark.policy import Policy, RequestExpectation
from hallmark.wire import H

# Independently enrolled on the Mac and confirmed by the published Linux campaign.
ENROLLMENT_PIN = "56c29c74a4efa0443bff84cc516349b0369360e2feaf347b871b860b06cd635e"


def native_templates(exported):
    records = [common.rule_native()]
    e = exported["mlp"]
    descriptor = ClassifierManifest(
        schema_id="hallmark/classifier/1",
        kind="mlp",
        program=e["program"].identity(),
        weights=e["program"].weights.sha256,
        tokenizer=None,
        input_profile=e["profile"].identity(),
        arithmetic=e["arithmetic"].identity(),
        threshold=0,
        scope="prompt",
        labels=("fixture-benign", "fixture-marker"),
        backend=H("backend", "native-template/1"),
        verifier_key=H("key", ["native-template/1", e["program"].identity()]),
        setup=H("setup", ["native-template/1", e["program"].identity()]),
    )
    for kind, c in (("mlp", descriptor), ("encoder", exported["encoder"]["classifier"])):
        e = exported[kind]
        records.append(
            dict(
                classifier=c,
                program=e["program"],
                input_profile=e["profile"],
                arithmetic=e["arithmetic"],
                files={k: e[k] for k in ("weights", "parameters", "tokenizer") if k in e},
                exported=e,
            )
        )
    for record in records:
        c, program = record["classifier"], record["program"].identity()
        # Native template IDs are replaced by actual Circle enrollment before any proof.
        record["classifier"] = c.model_copy(
            update=dict(
                backend=H("backend", "native-template/1"),
                verifier_key=H("key", ["native-template/1", program]),
                setup=H("setup", ["native-template/1", program]),
            )
        )._validated()
        record["classifier"].validate_profiles(
            record["input_profile"], record["arithmetic"], parameters=record["files"]["parameters"]
        )
    policy = Policy(
        schema_id="hallmark/policy/1",
        rubric=H("policy", "synthetic-trained-common/1"),
        classifiers=tuple(r["classifier"].identity() for r in records),
        combination="all-pass",
        language="en",
        scope="prompt",
        max_prompt_bytes=96,
        max_response_bytes=128,
    )
    policy.validate_classifiers(tuple(r["classifier"] for r in records))
    return records, policy


def manifest(directory):
    exported = comparison.exports(directory)
    records, policy = native_templates(exported)
    _, corpus = comparison.documents()
    requests = {}
    for case in corpus["requests"]:
        path = directory / "requests" / (case["id"] + "-request.json")
        opening, expected = comparison.request(path.parent, case["id"])
        if opening.prompt != case["prompt"] or expected.policy != policy.identity():
            raise ValueError("native caller request differs from the frozen controls")
        requests[path.name] = comparison.sha(read_regular(path, 65536))
    value = dict(
        schema_id="hallmark.circle-native-preparation/1",
        quantizations={
            k: comparison.sha(read_regular(directory / k, 65536)) for k in comparison.EXPORTS
        },
        programs=[r["program"].identity().hex() for r in records],
        requests=requests,
        licence="MIT",
        purpose="synthetic classifier command acceptance",
    )
    return value, exported, records, policy


def create(directory):
    _, policy = native_templates(comparison.exports(directory))
    _, corpus = comparison.documents()
    request_root = directory / "requests"
    request_root.mkdir()
    for case in corpus["requests"]:
        expected = RequestExpectation(
            schema_id="hallmark/request-expectation/1",
            audience="local-circle-classifiers",
            nonce=secrets.token_bytes(32),
            interaction_id=secrets.token_bytes(32),
            model=H("model", "synthetic-no-inference/1"),
            policy=policy.identity(),
            continuity=None,
        )
        opening = TranscriptOpening(
            schema_id="hallmark/transcript-opening/1",
            system_ref=bytes(32),
            prompt=case["prompt"],
            response="Synthetic response; no inference claim.",
            salt=secrets.token_bytes(32),
        )
        write_new(
            request_root / (case["id"] + "-request.json"),
            comparison.encoded(
                dict(
                    opening_cbor_hex=opening.encode().hex(),
                    expected_cbor_hex=expected.encode().hex(),
                )
            ),
        )
    raw = comparison.encoded(manifest(directory)[0])
    write_new(directory / "native-preparation.json", raw)
    pin = comparison.sha(raw)
    write_new(
        directory / "native-preparation-pin.json",
        comparison.encoded(
            dict(
                sha256=pin,
                before_proving=True,
            )
        ),
    )
    return pin


def admit(directory: Path, pin: str):
    raw = read_regular(directory / "native-preparation.json", 65536)
    if comparison.sha(raw) != pin:
        raise ValueError("caller native preparation pin mismatch")
    value, exported, records, policy = manifest(directory)
    if parse_json(raw.decode()) != value or raw != comparison.encoded(value):
        raise ValueError("native preparation/model/request mismatch")
    return exported, records, policy
