# Glossary

| Term | Canonical meaning |
|---|---|
| Claim A | Hardware-attested model and serving-path provenance for one interaction |
| Claim B | Cryptographically verified execution of the enrolled classifier programs |
| B1 | Opened transcript; verifier independently reconstructs exact classifier inputs |
| B2 | Commitment-only transcript; input binding additionally trusts genuine hardware |
| C0 | Separate genuine evidence objects composed by explicit equality checks |
| Enrollment | Externally authenticated selection of keys, manifests, policies and measurements before verification |
| Manifest | Versioned immutable description whose digest fixes all execution-relevant fields |
| Policy | Rubric, ordered classifier identities and combination rule; neither a quality guarantee nor deployment approval |
| Integer program | Exact exported arithmetic, including ranges, rounding, masking and aggregation |
| Calibration | Selecting a threshold using its dedicated split after the integer candidate is fixed |
| Test set | Frozen held-out evaluation; feedback cannot be used for candidate/threshold selection |
| Group | Shared upstream lineage assigned to one split, including all descendants |
| Replay | Software recomputation under a caller-pinned identity; no hardware/proof implication |
| Qualification | A bounded, measured check of a real graph/backend or hardware path against admission criteria |
| Receipt | Signed interaction statement; signature alone does not establish hardware or proof validity |
| Bundle | Receipt, registry, epoch/collateral and all required classifier proofs in one bounded artifact |
| Verdict | Pass/block under the enrolled integer threshold; equality blocks |
| Accepted | Required evidence and policy checks succeeded under an explicit trust policy |
| Not accepted | A claim is outside caller trust or lacks required evidence; distinct from an invalid proof |
| Independent verifier | Separately implemented parsing/binding/arithmetic/policy checks; shared proof-library dependencies disclosed |
| Admission | Owner-reviewed data/licence/policy/resource permission; a config allowlist is not permission |
| Release | Returning a response after native gating, or private package delivery; context must say which |
| v1 | The complete private hybrid POC, never the existing marker fixture |
| Evidence class | Software replay, statistical evaluation, hardware attestation or real cryptographic proof; no silent promotion |

Use these terms in interfaces, reports and issues. Avoid an unqualified “verified” when only one component was checked.
