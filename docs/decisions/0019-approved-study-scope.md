# 0019: Approved prototype study and delegated evaluation design

Date: 2026-10-20. Status: owner-approved scope; agent-specified design.
Scope: [W13 / #14](https://github.com/AbdelStark/hallmark/issues/14).
Supersedes the missing-authority state in decision 0018, not its binding semantics.

The owner approved the English, single-turn, prompt-only `inj.direct/1` study,
acting as prototype decision owner, with FPR at most 1%, TPR at least 90% and
integer conversion quality loss at most two percentage points. The owner
delegated evaluation design and selection of licence-reviewed public datasets,
models and software. This is a normalized decision record, not a transcript,
signature, independent review or adoption of a production safety policy.

The approved local envelope is four CPU threads, 16 GiB memory, 20 GiB working
storage, two hours per job, six hours total and zero monetary spend. The owner
also authorized use of their HF credential/API for GPU Jobs when necessary and
preferred execution on the Mac. [AUTHORITY](../../research/AUTHORITY.json) records
these permissions. The one-job/one-hour/$2 HF envelope is a conservative agent
execution limit under that permission, not a spending figure supplied by the owner.
No job, account top-up, scheduler or confidential-data upload follows from this
record. The credential remains outside version control.

The agent fixes the [evaluation design](../../research/proposals/inj-direct-v1/design.md)
before selecting data or measuring candidates. Its alpha, power assumptions,
joint decision, calibration allocation, paired loss test, retention and resource
criteria are delegated design choices. They are not measured results or separate
owner endorsements. No historical result is reused. Any later design correction
needs a new identity and decision before new measurement.

Approval permits reviewing sources and importing eligible public assets without
another generic approval request. It does not clear the three existing source
holds. Each selected revision still needs a concrete licence/provenance record;
ambiguous rights, gated terms and private inputs are excluded. After import, pin
actual file/split/candidate/evaluator identities before confirmatory measurement.
The incomplete proposal must continue to reject as an `AdmissionProtocol`.
Engineering work on import, runtimes and proof adapters can proceed on fixtures.

The owner requested options for genuine hardware and an independent reviewer.
The [options](../../research/proposals/inj-direct-v1/compute-and-review-options.md)
do not authorize buying another cloud host, contacting a reviewer or claiming
independence. Hardware evidence and external verification remain separate gates.
