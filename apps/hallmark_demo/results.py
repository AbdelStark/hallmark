"""Validate driver reports and produce the result view shared by both clients."""

import math

METRICS = {
    "proofs_verified": "Proofs verified",
    "proofs": "LLM proof segments",
    "llm_proofs_verified": "LLM proofs verified",
    "classifier_proofs_verified": "Classifier proofs verified",
    "cross_request_rejections": "Substitution rejections",
    "mutations_rejected": "Mutations rejected",
    "fresh_verifications": "Fresh honest checks",
    "direct_public_mutations_rejected": "Public-input rejections",
    "roster_rejections": "Roster rejections",
    "residual_links": "Residual links",
    "arithmetic_cases": "Arithmetic cases",
    "matched": "Software cases",
    "baseline_mutations_rejected": "Baseline mutations rejected",
    "native_enrollment_mutations_rejected": "Enrollment mutations rejected",
    "native_boundary_mutations_rejected": "Boundary mutations rejected",
}


def require(condition, message):
    if not condition:
        raise ValueError("Invalid driver result: " + message)


def exact(report, **fields):
    for name, value in fields.items():
        require(type(report.get(name)) is type(value) and report[name] == value, name)


def cases(report):
    rows = report.get("cases", [])
    if "classifier_verdicts" in report:
        rows = [
            dict(
                name="LLM request",
                verdicts=report["classifier_verdicts"],
                release=report.get("policy_release"),
            )
        ]
    require(isinstance(rows, list), "case list")
    for row in rows:
        require(isinstance(row, dict), "case object")
        values = row.get("verdicts")
        require(isinstance(row.get("name"), str), "case name")
        require(isinstance(values, list) and len(values) == 3, "three classifier verdicts")
        require(all(type(v) is int and v in (0, 1) for v in values), "binary integer verdicts")
        require(
            type(row.get("release")) is bool and row["release"] is all(values), "all-pass policy"
        )
    return rows


def summarize(workflow, report):
    require(isinstance(report, dict), "object expected")
    if workflow.schema:
        require(report.get("schema_id") == workflow.schema, "schema identity")
        require(report.get("status") == "passed" or report.get("passed") is True, "passing status")
    kind = "integrity"
    rows = []
    if workflow.id == "classifiers-circle":
        exact(
            report,
            backend="circle",
            proofs_verified=9,
            cross_request_rejections=18,
            direct_public_mutations_rejected=63,
            roster_rejections=3,
            intermediate_parity=True,
            qualified_backend=False,
            hardware_claim="not-accepted",
            hiding_claim=False,
        )
        rows = cases(report)
        require(
            len(rows) == 3 and all(r.get("proofs_verified") == 3 for r in rows),
            "nine verified Circle classifier proofs",
        )
    elif workflow.id == "composed-circle":
        exact(
            report,
            backend="circle",
            llm_proofs_verified=23,
            residual_links=22,
            fresh_llm_verifications=2,
            classifier_proofs_verified=3,
            qualified_backend=False,
            hiding_claim=False,
            hardware_claim="not-accepted",
            classifier_scope="prompt",
            safety_quality_claim=False,
            host_join=True,
            recursion=False,
        )
        rejected = report.get("binding_rejections")
        require(
            isinstance(rejected, list) and len(rejected) == 16 and len(set(rejected)) == 16,
            "sixteen distinct binding rejections",
        )
        rows = cases(report)
        require(len(rows) == 1, "one composed Circle case")
    elif workflow.id == "llm":
        exact(
            report,
            proofs=23,
            residual_links=22,
            fresh_verifications=2,
            mutations_rejected=14,
            qualified_backend=False,
            hiding_claim=False,
            all_buckets_deleted=True,
        )
    elif workflow.id == "verify-llm":
        exact(
            report,
            proofs=23,
            residual_links=22,
            fresh_verifications=2,
            baseline_mutations_rejected=14,
            native_enrollment_mutations_rejected=2,
            native_boundary_mutations_rejected=20,
            qualified_backend=False,
            security_review=False,
        )
    elif workflow.id == "conformance":
        kind = "software"
        exact(report, software_passed=True, matched=156, mismatched=0, all_required_executed=False)
    elif workflow.id == "gpu":
        exact(
            report,
            proof_bytes_equal=True,
            repetitions=1,
            all_buckets_deleted=True,
            qualified_backend=False,
            hiding_claim=False,
        )
        measurements = report.get("measurements")
        require(
            isinstance(measurements, list) and len(measurements) == 2, "one paired GPU measurement"
        )
        require({r.get("backend") for r in measurements} == {"simd", "cuda"}, "matched backends")
        for row in measurements:
            for name in (
                "prove_seconds",
                "commands_seconds",
                "sampled_peak_rss_bytes",
                "serialized_proof_bytes",
            ):
                value = row.get(name)
                require(type(value) in (int, float) and math.isfinite(value) and value > 0, name)
    else:
        kind = "workflow"
    metrics = [
        dict(label=label, value=report[name], unit="count")
        for name, label in METRICS.items()
        if type(report.get(name)) is int
    ]
    if type(report.get("compute_bound_micro_usd")) is int:
        metrics.append(
            dict(
                label="Running-compute estimate · not an invoice",
                value=report["compute_bound_micro_usd"] / 1_000_000,
                unit="USD",
            )
        )
    return dict(
        kind=kind,
        title={
            "integrity": "Verification passed",
            "software": "Software checks passed",
            "workflow": "Workflow completed",
        }[kind],
        metrics=metrics,
        cases=rows,
        response=report.get("response"),
        measurements=report.get("measurements", []),
        note="No cryptographic proof was generated." if kind == "software" else workflow.claim,
    )
