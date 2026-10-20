"""Build a candidate corpus in a fresh directory; never rewrite a frozen corpus."""

import argparse
import hashlib
import json
from pathlib import Path

import cbor2

from hallmark.conformance import (
    CHEATS,
    MANDATORY_REQUIREMENTS,
    Case,
    Corpus,
    Outcome,
    Requirement,
)
from hallmark.manifests import FileRef
from hallmark.wire import DOMAINS

ROOT = Path(__file__).resolve().parents[1]


def enc(value):
    return cbor2.dumps(value, canonical=True)


def digest(domain, raw):
    tag = ("hallmark/v1/" + domain).encode("ascii")
    return hashlib.sha256(len(tag).to_bytes(4, "big") + tag + raw).digest()


def changed(raw, path, value):
    item = cbor2.loads(raw)
    target = item
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return enc(item)


def ok(*digests, integers=()):
    return Outcome(
        accepted=True,
        claim_a="not-accepted",
        claim_b="not-accepted",
        code=None,
        input_digests=tuple(digests),
        integers=integers,
    )


def bad(code):
    return Outcome(
        accepted=False,
        claim_a="not-accepted",
        claim_b="not-accepted",
        code=code,
        input_digests=(),
        integers=(),
    )


def build(output: Path, sources_root: Path = ROOT) -> Corpus:
    output.mkdir(parents=True, exist_ok=False)
    objects = {}

    def put(raw, suffix="cbor"):
        sha = hashlib.sha256(raw).hexdigest()
        name = f"objects/{sha}.{suffix}"
        if name not in objects:
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as handle:
                handle.write(raw)
            objects[name] = FileRef(path=name, size=len(raw), sha256=bytes.fromhex(sha))
        return objects[name]

    def fixture(name):
        return json.loads((ROOT / f"fixtures/wire/{name}-v1.json").read_text())

    def raw(record):
        return bytes.fromhex(record["cbor_hex"])

    enrollment = fixture("enrollment")
    receipts = fixture("receipts")
    openings = fixture("openings")
    policies = fixture("policy-request")
    models = fixture("model-manifest")
    classifiers = fixture("classifier")
    bundles = fixture("bundles")
    rotation = fixture("registry-rotation")
    trusts, requests, cases = {}, {}, []

    def trust_id(value):
        identity = digest("trust", value)
        trusts[identity] = put(value)
        return identity

    def request_id(value):
        identity = hashlib.sha256(value).digest()
        requests[identity] = put(value)
        return identity

    default_trust = trust_id(raw(enrollment["trust"]))
    default_request = request_id(raw(receipts["expected"]))

    def add(
        name,
        check,
        inputs,
        expected,
        requirement,
        *,
        parent=None,
        mutation=None,
        trust=default_trust,
        request=default_request,
        now=150,
    ):
        cases.append(
            Case(
                schema_id="hallmark/conformance-case/1",
                case_id=name,
                parent=parent,
                mutation=mutation,
                evidence_class="software-vector",
                check=check,
                inputs=tuple(put(value) for value in inputs),
                trust=trust,
                expected_request=request,
                now=now,
                expected=expected,
                requirement=requirement,
                unavailable=(),
            )
        )

    # Literal RFC 8949 encodings; expectations use a separate hashlib preimage.
    wire_values = [
        (0, "00"),
        (23, "17"),
        (24, "1818"),
        (255, "18ff"),
        (256, "190100"),
        (65535, "19ffff"),
        (65536, "1a00010000"),
        (2**32 - 1, "1affffffff"),
        (2**32, "1b0000000100000000"),
        (2**64 - 1, "1bffffffffffffffff"),
        (-1, "20"),
        (-24, "37"),
        (-25, "3818"),
        (-(2**63), "3b7fffffffffffffff"),
        (False, "f4"),
        (True, "f5"),
        (None, "f6"),
        (b"", "40"),
        (b"\x01\x02\x03\x04", "4401020304"),
        ("", "60"),
        ("a", "6161"),
        ("IETF", "6449455446"),
        ("é", "62c3a9"),
        ("é", "6365cc81"),
        ("😀", "64f09f9880"),
        ([], "80"),
        ([1, [2, 3], [4, 5]], "8301820203820405"),
        ({}, "a0"),
        ({"b": [2, 3], "a": 1}, "a26161016162820203"),
        ({"aa": 3, "b": 2, "a": 1}, "a361610161620262616103"),
    ]
    for index, (value, encoded) in enumerate(wire_values):
        encoded = bytes.fromhex(encoded)
        assert enc(value) == encoded
        requirement = (
            "wire.integer-extrema"
            if type(value) is int and (value < 0 or value >= 2**32)
            else "wire.types"
            if type(value) in (bool, type(None), bytes)
            else "wire.utf8"
            if type(value) is str
            else "wire.canonical"
        )
        add(
            f"wire.valid-{index:02}",
            "wire",
            (encoded,),
            ok(digest("protocol", encoded)),
            requirement,
        )
    malformed = {
        "empty": "",
        "trailing": "00ff",
        "long-integer": "1800",
        "long-length": "5800",
        "indefinite-bytes": "5f40ff",
        "indefinite-array": "9f00ff",
        "tag": "c000",
        "float": "fa3f800000",
        "nan": "fb7ff8000000000000",
        "simple": "f7",
        "negative-overflow": "3b8000000000000000",
        "utf8": "61ff",
        "overlong-utf8": "62c0af",
        "surrogate": "63eda080",
        "duplicate-key": "a2616100616101",
        "key-order": "a2616200616101",
        "nontext-key": "a10100",
        "truncated": "8200",
    }
    for index, encoded in enumerate(
        [
            "",
            "00ff",
            "1800",
            "190018",
            "1a00000100",
            "1b0000000000010000",
            "3800",
            "5800",
            "7800",
            "9800",
            "b800",
            "1c",
            "1d",
            "1e",
            "1f",
            "ff",
            "5f40ff",
            "7f60ff",
            "9f00ff",
            "bf616100ff",
            "c000",
            "c24101",
            "d81c80",
            "d81d00",
            "e0",
            "f7",
            "f814",
            "f818",
            "f90000",
            "fa3f800000",
            "fb7ff8000000000000",
            "3b8000000000000000",
            "61ff",
            "62c0af",
            "63eda080",
            "64f4908080",
            "a2616100616101",
            "a2616200616101",
            "a10100",
            "a1416100",
            "a1810000",
            "a1f400",
            "1b00",
            "4161ff",
            "8200",
            "a16161",
            "5bffffffffffffffff",
        ]
    ):
        if encoded not in malformed.values():
            malformed[f"encoding-{index:02}"] = encoded
    for name, encoded in malformed.items():
        requirement = (
            "wire.utf8" if "utf8" in name or name == "surrogate" else "error.INPUT_INVALID"
        )
        add(
            "wire.invalid-" + name,
            "wire",
            (bytes.fromhex(encoded),),
            bad("INPUT_INVALID"),
            requirement,
            parent="wire.valid-00",
            mutation="wire-encoding",
        )
    add(
        "wire.small-valid",
        "wire-small",
        (enc([0]),),
        ok(digest("protocol", enc([0]))),
        "wire.bounds",
    )
    for name, value in (("bytes", b"x" * 65), ("depth", [[[[0]]]]), ("items", [0] * 9)):
        add(
            "wire.limit-" + name,
            "wire-small",
            (enc(value),),
            bad("LIMIT_EXCEEDED"),
            "error.LIMIT_EXCEEDED",
            parent="wire.small-valid",
            mutation="container-" + name,
        )
    for name, encoded in (("huge-array", "9bffffffffffffffff"), ("huge-map", "bbffffffffffffffff")):
        add(
            "wire." + name,
            "wire",
            (bytes.fromhex(encoded),),
            bad("LIMIT_EXCEEDED"),
            "wire.bounds",
            parent="wire.valid-00",
            mutation="declared-length",
        )
    for name, value in (
        ("exact-bytes", b"x" * 62),
        ("exact-items", [0] * 7),
        ("exact-depth", [[[0]]]),
    ):
        add(
            "wire." + name,
            "wire-small",
            (enc(value),),
            ok(digest("protocol", enc(value))),
            "wire.bounds",
        )
    add(
        "identity.domains",
        "domains",
        (enc(42),),
        ok(*(digest(domain, enc(42)) for domain in sorted(DOMAINS))),
        "identity.domains",
    )

    model = bytes.fromhex(models["cbor_hex"])
    add(
        "model.valid",
        "model",
        (model,),
        ok(bytes.fromhex(models["identity_hex"])),
        "identity.immutable",
    )
    for name, path, value in (
        ("bool-int", ("generation", "seed"), True),
        ("version", ("schema_id",), "hallmark/model/999"),
        ("path-traversal", ("files", 0, "path"), "../private"),
        ("absolute-path", ("files", 0, "path"), "/private"),
        ("empty-files", ("files",), []),
    ):
        add(
            "model." + name,
            "model",
            (changed(model, path, value),),
            bad("INPUT_INVALID"),
            "wire.types" if name == "bool-int" else "error.INPUT_INVALID",
            parent="model.valid",
            mutation=name,
        )
    content = models["content_utf8"].encode()
    add("model.files-valid", "model-files", (model, content), ok(), "identity.immutable")
    add(
        "model.swapped-file",
        "model-files",
        (model, b"x" + content[1:]),
        bad("INPUT_INVALID"),
        "prd.swapped-model-file",
        parent="model.files-valid",
        mutation="file-byte",
    )

    policy = raw(policies["policy"])
    group = tuple(bytes.fromhex(value) for value in policies["classifiers_cbor_hex"])
    add(
        "policy.valid",
        "policy",
        (policy, *group),
        ok(bytes.fromhex(policies["policy"]["identity_hex"])),
        "claims.separation",
    )
    add(
        "policy.classifier-swap",
        "policy",
        (policy, group[1], group[0], group[2]),
        bad("INPUT_INVALID"),
        "prd.classifier-swap",
        parent="policy.valid",
        mutation="classifier-order",
    )
    request = raw(policies["request"])
    request_context = request_id(raw(policies["expectation"]))
    request_args = (request, bytes.fromhex(policies["model_cbor_hex"]), policy, *group)
    add("request.valid", "request", request_args, ok(), "binding.B1", request=request_context)
    for name, field, value in (
        ("nonce", "nonce", b"x" * 32),
        ("audience", "audience", "other"),
        ("model", "model", b"x" * 32),
        ("policy", "policy", b"x" * 32),
    ):
        add(
            "request." + name,
            "request",
            (changed(request, ("expected", field), value), *request_args[1:]),
            bad("REQUEST_MISMATCH"),
            "error.REQUEST_MISMATCH",
            parent="request.valid",
            mutation=field,
            request=request_context,
        )

    opening_case = openings["cases"][1]
    opening = raw(opening_case["opening"])
    commitment = bytes.fromhex(opening_case["transcript_hex"])
    opening_context = request_id(raw(openings["expected"]))
    add(
        "opening.valid",
        "opening",
        (opening, commitment),
        ok(commitment, bytes.fromhex(opening_case["context_hex"])),
        "binding.B1",
        request=opening_context,
    )
    for name, field, value in (
        ("altered-prompt", "prompt", "changed"),
        ("altered-response", "response", "changed"),
        ("wrong-salt", "salt", b"x" * 32),
    ):
        add(
            "opening." + name,
            "opening",
            (changed(opening, (field,), value), commitment),
            bad("OPENING_FAILED"),
            "prd." + name,
            parent="opening.valid",
            mutation=field,
            request=opening_context,
        )
    add(
        "opening.mismatch-code",
        "opening",
        (opening, b"x" * 32),
        bad("OPENING_FAILED"),
        "error.OPENING_FAILED",
        parent="opening.valid",
        mutation="external-commitment",
        request=opening_context,
    )
    mlp = raw(openings["classifiers"]["mlp"])
    byte_profile = raw(openings["profiles"]["bytes"])
    add(
        "input.valid",
        "input-bytes",
        (opening, mlp, byte_profile),
        ok(bytes.fromhex(opening_case["inputs"][1]["digest_hex"])),
        "arithmetic.coverage",
    )
    bounded_profile = changed(byte_profile, ("max_units",), 512)
    bounded_mlp = changed(mlp, ("input_profile",), digest("input-profile", bounded_profile))
    bounded_opening = changed(opening, ("prompt",), "a" * 512)

    def input_hash(opened, manifest, profile):
        value = cbor2.loads(opened)
        units = list(value["prompt"].encode())
        salt = digest("input-salt", enc([value["salt"], digest("classifier", manifest)]))
        return digest("input", enc([salt, digest("input-profile", profile), len(units), units]))

    add(
        "input.exact-limit",
        "input-bytes",
        (bounded_opening, bounded_mlp, bounded_profile),
        ok(input_hash(bounded_opening, bounded_mlp, bounded_profile)),
        "arithmetic.coverage",
    )
    add(
        "input.over-limit",
        "input-bytes",
        (changed(bounded_opening, ("prompt",), "a" * 512 + "x"), bounded_mlp, bounded_profile),
        bad("LIMIT_EXCEEDED"),
        "prd.late-payload",
        parent="input.exact-limit",
        mutation="prompt-length",
    )
    tail = changed(opening, ("prompt",), "a" * 512 + "x")
    add(
        "input.complete-tail",
        "input-bytes",
        (tail, mlp, byte_profile),
        ok(input_hash(tail, mlp, byte_profile)),
        "prd.late-payload",
    )

    add(
        "classifier.valid",
        "classifier",
        (mlp,),
        ok(digest("classifier", mlp)),
        "identity.immutable",
    )
    altered_classifier = changed(mlp, ("threshold",), cbor2.loads(mlp)["threshold"] + 1)
    add(
        "classifier.changed-identity",
        "classifier",
        (altered_classifier,),
        ok(digest("classifier", altered_classifier)),
        "identity.immutable",
        parent="classifier.valid",
        mutation="threshold",
    )
    add(
        "input-profile.valid",
        "input-profile",
        (byte_profile,),
        ok(digest("input-profile", byte_profile)),
        "identity.immutable",
    )
    receipt = raw(receipts["receipt"])
    proof = raw(receipts["proofs"][1])
    proof_value = cbor2.loads(proof)
    public = enc(proof_value["public_inputs"])
    profile = raw(receipts["profiles"]["bytes"])
    classifier = raw(receipts["classifiers"]["mlp"])
    public_value = cbor2.loads(public)
    fields = tuple(
        [
            *public_value["context"],
            *public_value["classifier"],
            *public_value["input_digest"],
            public_value["unit_count"],
            public_value["chunk_count"],
            public_value["threshold"] + 2**31,
            int(public_value["verdict"]),
        ]
    )
    add(
        "fields.valid",
        "proof-fields",
        (enc(list(fields)),),
        ok(integers=fields),
        "arithmetic.range",
    )
    for name, index, value in (
        ("byte-alias", 0, 256),
        ("negative-byte", 0, -1),
        ("threshold-alias", 98, 2**32),
        ("bool-field", 99, True),
        ("verdict-alias", 99, 2),
    ):
        altered = list(fields)
        altered[index] = value
        add(
            "fields." + name,
            "proof-fields",
            (enc(altered),),
            bad("INPUT_INVALID"),
            "arithmetic.range",
            parent="fields.valid",
            mutation=name,
        )
    add(
        "profile.valid",
        "proof-profile",
        (public, classifier, profile),
        ok(integers=fields),
        "arithmetic.coverage",
    )
    for name, index, value, requirement in (
        (
            "threshold-swap",
            0,
            changed(public, ("threshold",), public_value["threshold"] + 1),
            "prd.threshold-swap",
        ),
        (
            "omitted-chunk",
            0,
            changed(public, ("chunk_count",), public_value["chunk_count"] + 1),
            "error.INPUT_BINDING_FAILED",
        ),
        ("tokenizer-swap", 1, raw(receipts["classifiers"]["encoder"]), "prd.tokenizer-swap"),
    ):
        args = [public, classifier, profile]
        args[index] = value
        add(
            "profile." + name,
            "proof-profile",
            tuple(args),
            bad("INPUT_BINDING_FAILED"),
            requirement,
            parent="profile.valid",
            mutation=name,
        )
    add(
        "receipt.valid",
        "receipt",
        (receipt,),
        ok(bytes.fromhex(receipts["receipt"]["identity_hex"])),
        "claims.separation",
        now=receipts["now"],
    )
    add(
        "receipt.expired",
        "receipt",
        (receipt,),
        bad("STALE_EVIDENCE"),
        "error.STALE_EVIDENCE",
        parent="receipt.valid",
        mutation="verification-clock",
        now=cbor2.loads(receipt)["expires_at"],
    )
    add(
        "receipt.chain-break",
        "receipt",
        (changed(receipt, ("previous",), b"x" * 32),),
        bad("INPUT_INVALID"),
        "prd.chain-break",
        parent="receipt.valid",
        mutation="previous",
        now=receipts["now"],
    )
    add(
        "proof.declaration-valid",
        "proof-declaration",
        (proof, public, classifier, profile),
        ok(),
        "claims.separation",
    )
    add(
        "proof.different-receipt",
        "proof-declaration",
        (changed(proof, ("public_inputs", "context"), b"x" * 32), public, classifier, profile),
        bad("INPUT_BINDING_FAILED"),
        "prd.different-receipt-proof",
        parent="proof.declaration-valid",
        mutation="public-context",
    )
    bundle = raw(bundles["records"][0])
    bundle_trust = trust_id(bytes.fromhex(bundles["external_trust_cbor_hex"]))
    add(
        "bundle.valid-container", "bundle", (bundle,), ok(), "claims.separation", trust=bundle_trust
    )
    for name, path, value in (
        ("missing-proofs", ("proofs",), []),
        ("changed-file", ("files", 0, "content"), b"changed"),
        ("private-opening", ("opening",), cbor2.loads(opening)),
    ):
        add(
            "bundle." + name,
            "bundle",
            (changed(bundle, path, value),),
            bad("INPUT_INVALID"),
            "prd.false-gateway-pass" if name == "missing-proofs" else "error.INPUT_INVALID",
            parent="bundle.valid-container",
            mutation=name,
            trust=bundle_trust,
        )

    snapshot, checkpoint = raw(enrollment["signed-registry"]), raw(enrollment["registry-state"])
    body = cbor2.loads(snapshot)["body"]
    entry = next(value for value in body["entries"] if value["kind"] == "model")
    enrollment_result = ok(
        bytes.fromhex(enrollment["registry"]["identity_hex"]),
        bytes.fromhex(enrollment["trust"]["identity_hex"]),
    )
    add(
        "enrollment.valid",
        "enrollment",
        (snapshot, checkpoint, enc(entry)),
        enrollment_result,
        "registry.rollback",
        now=enrollment["now"],
    )
    add(
        "enrollment.unknown-model",
        "enrollment",
        (snapshot, checkpoint, enc(entry | {"digest": b"x" * 32})),
        bad("TRUST_MISSING"),
        "prd.unregistered-model",
        parent="enrollment.valid",
        mutation="required-model",
    )
    add(
        "enrollment.wrong-checkpoint",
        "enrollment",
        (snapshot, changed(checkpoint, ("digest",), b"x" * 32), enc(entry)),
        bad("REGISTRY_INVALID"),
        "error.REGISTRY_INVALID",
        parent="enrollment.valid",
        mutation="checkpoint-digest",
    )
    add(
        "enrollment.wrong-signature",
        "enrollment",
        (changed(snapshot, ("signatures", 0, "signature"), b"x" * 64), checkpoint, enc(entry)),
        bad("SIGNATURE_INVALID"),
        "error.SIGNATURE_INVALID",
        parent="enrollment.valid",
        mutation="signature",
    )
    add(
        "enrollment.unknown-code",
        "enrollment",
        (snapshot, checkpoint, enc(entry | {"digest": b"z" * 32})),
        bad("TRUST_MISSING"),
        "error.TRUST_MISSING",
        parent="enrollment.valid",
        mutation="required-model",
    )
    policy_entry = next(value for value in body["entries"] if value["kind"] == "policy")
    add("entry.valid", "entry-time", (enc(policy_entry), enc(100)), ok(), "registry.retirement")
    add(
        "entry.retired",
        "entry-time",
        (enc(policy_entry | {"retired_at": 150}), enc(100)),
        bad("ARTIFACT_RETIRED"),
        "prd.retired-policy",
        parent="entry.valid",
        mutation="retired-at",
    )
    add(
        "entry.retired-code",
        "entry-time",
        (enc(policy_entry | {"retired_at": 149}), enc(100)),
        bad("ARTIFACT_RETIRED"),
        "error.ARTIFACT_RETIRED",
        parent="entry.valid",
        mutation="retired-at",
    )
    add(
        "entry.expired",
        "entry-time",
        (enc(policy_entry), enc(policy_entry["valid_until"])),
        bad("STALE_EVIDENCE"),
        "registry.retirement",
        parent="entry.valid",
        mutation="receipt-clock",
    )
    previous = raw(rotation["previous"])
    previous_body = cbor2.loads(previous)["body"]
    rotation_state = enc(
        {
            "schema_id": "hallmark/registry-state/1",
            "sequence": previous_body["sequence"],
            "digest": digest("registry", enc(previous_body)),
        }
    )
    rotation_inputs = (
        raw(rotation["snapshot"]),
        raw(rotation["transition"]),
        raw(rotation["old_trust"]),
        previous,
        rotation_state,
    )
    new_trust = trust_id(raw(rotation["new_trust"]))
    add(
        "rotation.valid",
        "rotation",
        rotation_inputs,
        ok(digest("registry", enc(cbor2.loads(rotation_inputs[0])["body"])), new_trust),
        "registry.rotation",
        trust=new_trust,
    )
    for side in ("old", "new"):
        altered = changed(
            rotation_inputs[1],
            (side + "_signatures",),
            cbor2.loads(rotation_inputs[1])[side + "_signatures"][:1],
        )
        add(
            "rotation." + side + "-insufficient",
            "rotation",
            (rotation_inputs[0], altered, *rotation_inputs[2:]),
            bad("SIGNATURE_INVALID"),
            "registry.rotation",
            parent="rotation.valid",
            mutation=side + "-threshold",
            trust=new_trust,
        )

    arithmetic = raw(classifiers["arithmetic"])
    parameters = enc(
        {name: bytes.fromhex(value) for name, value in classifiers["parameters"].items()}
    )
    add(
        "arithmetic.static-valid",
        "arithmetic",
        (arithmetic, parameters),
        ok(bytes.fromhex(classifiers["arithmetic"]["identity_hex"])),
        "arithmetic.range",
    )
    parameter_values = cbor2.loads(parameters)
    first_parameter = sorted(parameter_values)[0]
    parameter_values[first_parameter] = b"\x00"
    add(
        "arithmetic.parameter-swap",
        "arithmetic",
        (arithmetic, enc(parameter_values)),
        bad("INPUT_INVALID"),
        "arithmetic.mask",
        parent="arithmetic.static-valid",
        mutation="parameter-file",
    )
    weights = [0] * 256
    weights[ord("x")], weights[ord("a")] = 3, -1
    linear = {
        "schema_id": "hallmark.integer-byte-linear/1",
        "policy_id": "fixture.marker",
        "scope": "response",
        "chunk_bytes": 4,
        "weights": weights,
        "bias": -1,
        "threshold": 2,
        "scale": 1,
    }
    linear_raw = json.dumps(linear, sort_keys=True).encode()
    for name, text, score, passes, requirement in (
        ("empty", "", -1, 1, "arithmetic.empty"),
        ("equality", "x", 2, 0, "arithmetic.threshold"),
        ("negative", "aaaa", -5, 1, "arithmetic.signed"),
        ("late", "aaaax", 2, 0, "arithmetic.coverage"),
        ("exact", "aaax", -1, 1, "arithmetic.coverage"),
    ):
        add(
            "linear." + name,
            "linear",
            (linear_raw, text.encode()),
            ok(integers=(score, passes)),
            requirement,
        )
    for name, code in (
        ("input", "INPUT_INVALID"),
        ("memory", "RESOURCE_EXHAUSTED"),
        ("storage", "STORAGE_FAILED"),
        ("internal", "INTERNAL_ERROR"),
    ):
        add("diagnostic." + name, "diagnostic", (name.encode(),), bad(code), "error." + code)

    hybrid_policy = cbor2.loads(raw(enrollment["trust"])) | {
        "required_claims": "A+B",
        "hardware_roots": [b"h" * 32],
        "measurements": [b"m" * 32],
    }
    hybrid_trust = trust_id(enc(hybrid_policy))
    b2_trust = trust_id(enc(hybrid_policy | {"binding": "B2"}))

    def missing(
        name,
        evidence,
        expected,
        requirement,
        parent=None,
        mutation=None,
        dependencies=(),
        trust=None,
    ):
        cases.append(
            Case(
                schema_id="hallmark/conformance-case/1",
                case_id=name,
                parent=parent,
                mutation=mutation,
                evidence_class=evidence,
                check="unavailable",
                inputs=(),
                trust=trust or (default_trust if evidence == "real-proof" else hybrid_trust),
                expected_request=default_request,
                now=150,
                expected=expected,
                requirement=requirement,
                unavailable=tuple(sorted(dependencies)),
            )
        )

    def genuine(accepted, evidence, code=None):
        claim_a = "accepted" if accepted and evidence != "real-proof" else "not-accepted"
        claim_b = "accepted" if accepted and evidence != "real-hardware" else "not-accepted"
        if code in ("ATTESTATION_INVALID", "MEASUREMENT_UNKNOWN"):
            claim_a = "rejected"
        if code in ("OPENING_FAILED", "INPUT_BINDING_FAILED", "PROOF_INVALID", "VERDICT_MISMATCH"):
            claim_a = "accepted" if evidence == "hybrid" else "not-accepted"
            claim_b = "rejected"
        if code == "POLICY_BLOCKED":
            claim_a, claim_b = "accepted", "accepted"
        return Outcome(
            accepted=accepted,
            claim_a=claim_a,
            claim_b=claim_b,
            code=code,
            input_digests=(),
            integers=(),
        )

    missing(
        "full.hardware-valid",
        "real-hardware",
        genuine(True, "real-hardware"),
        "claims.separation",
        dependencies=("W22-genuine-evidence",),
    )
    missing(
        "full.proof-valid",
        "real-proof",
        genuine(True, "real-proof"),
        "claims.separation",
        dependencies=("W18-qualified-backend", "W19-W21-real-proofs"),
    )
    missing(
        "full.hybrid-valid",
        "hybrid",
        genuine(True, "hybrid"),
        "binding.B1",
        dependencies=("W26-complete-bundle", "W28-full-verifier"),
    )
    missing(
        "full.b2-valid",
        "hybrid",
        genuine(True, "hybrid"),
        "binding.B2",
        dependencies=("W22-genuine-evidence", "W28-full-verifier"),
        trust=b2_trust,
    )
    integration_codes = {
        "altered-prompt": "OPENING_FAILED",
        "altered-response": "OPENING_FAILED",
        "swapped-model-file": "ATTESTATION_INVALID",
        "unregistered-model": "TRUST_MISSING",
        "classifier-swap": "INPUT_BINDING_FAILED",
        "threshold-swap": "INPUT_BINDING_FAILED",
        "replay": "REQUEST_MISMATCH",
        "chain-break": "REQUEST_MISMATCH",
        "wrong-salt": "OPENING_FAILED",
        "tokenizer-swap": "INPUT_BINDING_FAILED",
        "late-payload": "INPUT_BINDING_FAILED",
        "false-gateway-pass": "INPUT_INVALID",
        "different-receipt-proof": "PROOF_INVALID",
        "retired-policy": "ARTIFACT_RETIRED",
        "debug-quote": "ATTESTATION_INVALID",
    }
    for cheat in CHEATS:
        missing(
            "full.prd-" + cheat,
            "hybrid",
            genuine(False, "hybrid", integration_codes[cheat]),
            "prd." + cheat,
            parent="full.hybrid-valid",
            mutation=cheat,
            dependencies=("W26-complete-bundle", "W28-full-verifier"),
        )
    # Full graph rounding, padding, masks and all chunks require the qualified proof/runtime pair.
    for boundary in ("rounding", "range", "mask", "empty", "signed", "threshold", "coverage"):
        missing(
            "full.arithmetic-" + boundary,
            "real-proof",
            genuine(False, "real-proof", "PROOF_INVALID"),
            "arithmetic." + boundary,
            parent="full.proof-valid",
            mutation=boundary,
            dependencies=(
                "W11-W12-integer-runtimes",
                "W18-qualified-backend",
                "W19-W21-real-proofs",
            ),
        )
    covered = {case.requirement for case in cases}
    for requirement in sorted(MANDATORY_REQUIREMENTS - covered):
        assert requirement.startswith("error."), requirement
        code = requirement.split(".", 1)[1]
        missing(
            "full.error-" + code.lower(),
            "hybrid",
            genuine(False, "hybrid", code),
            requirement,
            parent="full.hybrid-valid",
            mutation=code,
            dependencies=("W22-genuine-evidence", "W28-full-verifier"),
        )

    sources = {}
    requirements = []
    for requirement in sorted(MANDATORY_REQUIREMENTS):
        source = (
            "research/source/hybrid-specification.txt"
            if requirement.startswith("prd.")
            else "docs/spec/04-error-model.md"
            if requirement.startswith("error.")
            else "docs/spec/07-testing-strategy.md"
        )
        if source not in sources:
            content = (sources_root / source).read_bytes()
            target = output / "sources" / source
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            sources[source] = FileRef(
                path="sources/" + source, size=len(content), sha256=hashlib.sha256(content).digest()
            )
        locator = (
            "section-13.2-negative-corpus"
            if requirement.startswith("prd.")
            else requirement.removeprefix("error.")
            if requirement.startswith("error.")
            else "required-layers"
        )
        requirements.append(Requirement(id=requirement, source=sources[source], locator=locator))
    corpus = Corpus(
        schema_id="hallmark/conformance-corpus/1",
        revision="software-foundation-1",
        evidence_notice="public-synthetic-fixtures-only",
        trust_policies=tuple(trusts[key] for key in sorted(trusts)),
        expectations=tuple(requests[key] for key in sorted(requests)),
        requirements=tuple(requirements),
        cases=tuple(sorted(cases, key=lambda case: case.case_id)),
    )
    (output / "corpus.json").write_text(corpus.model_dump_json(indent=2) + "\n")
    (output / "corpus.id").write_text(corpus.identity().hex() + "\n")
    return corpus


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sources", type=Path, default=ROOT)
    args = parser.parse_args()
    built = build(args.output, args.sources)
    print(json.dumps({"corpus": built.identity().hex(), "cases": len(built.cases)}))
