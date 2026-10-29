"""Opened request binding and rejection checks for a composed Circle/LLM bundle."""

import copy

import circle_backend as circle
import composed_input


def joined_jobs(enrollment, pin, originals, old_policy, opening, expected, bundle):
    composed_input.check_request(opening, expected)
    return circle.check_bundle(enrollment, pin, originals, old_policy, opening, expected, bundle)


def binding_negatives(enrollment, pin, originals, policy, opening, expected, bundle):
    rejected = []
    for field in (
        "prompt",
        "response",
        "system_ref",
        "salt",
        "model",
        "nonce",
        "interaction_id",
        "policy",
    ):
        opened, request = opening, expected
        if field in ("prompt", "response", "system_ref", "salt"):
            value = getattr(opening, field)
            value = value + "!" if type(value) is str else bytes([value[0] ^ 1]) + value[1:]
            opened = opening.model_copy(update={field: value})
        else:
            value = getattr(expected, field)
            request = expected.model_copy(update={field: bytes([value[0] ^ 1]) + value[1:]})
        try:
            joined_jobs(enrollment, pin, originals, policy, opened, request, bundle)
        except ValueError:
            rejected.append(field)
        else:
            raise ValueError("changed composed request accepted: " + field)
    variants = []
    for index in range(3):
        changed = copy.deepcopy(bundle)
        changed["proofs"][index]["public"][32] ^= 1
        variants.append(("classifier-" + str(index), changed))
    variants += [
        ("missing", dict(bundle, proofs=bundle["proofs"][:-1])),
        ("duplicate", dict(bundle, proofs=[bundle["proofs"][0]] * 3)),
        ("reordered", dict(bundle, proofs=list(reversed(bundle["proofs"])))),
    ]
    for name, changed in variants:
        try:
            joined_jobs(enrollment, pin, originals, policy, opening, expected, changed)
        except ValueError:
            rejected.append(name)
        else:
            raise ValueError("changed composed roster accepted: " + name)
    _, enrolled_policy, _ = circle.resolve(enrollment, pin, originals, policy)
    other_expected, other_opening = composed_input.request(enrolled_policy)
    try:
        joined_jobs(enrollment, pin, originals, policy, other_opening, other_expected, bundle)
    except ValueError:
        rejected.append("cross-request")
    else:
        raise ValueError("cross-request composed evidence accepted")
    try:
        joined_jobs(enrollment + b" ", pin, originals, policy, opening, expected, bundle)
    except ValueError:
        rejected.append("changed-enrollment")
    else:
        raise ValueError("changed caller enrollment accepted")
    return rejected
