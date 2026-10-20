# Sources and evidence status

Primary pages read during initialization on 2026-10-20. These support interface/tooling choices, not Hallmark performance. The imported packet has its own historical source dates; its verification labels are not new checks in this repository.

| Source | Checked scope | What remains unverified |
|---|---|---|
| [EZKL upstream](https://github.com/zkonduit/ezkl) | README describes ONNX computational graphs and Halo2-based proof tooling | Exact model/operator support, setup assumptions, licence at chosen revision, performance and integration |
| [Laya upstream](https://github.com/NandhaKishorM/laya) | Public decision-model research/tooling description | Selected checkpoint/config/licence, every comparative quality/latency claim and suitability for these policies |
| [Prompt Guard 2 22M model card](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M) | Candidate task-specific prompt-injection guard and access/usage context | Local behavior, use approval and numerical/prover compatibility; not a general response-policy classifier |
| [scikit-learn LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) | Public estimator API used by the optional floor baseline | No inference about safety quality; installed version is recorded per run |
| [uv project guide](https://docs.astral.sh/uv/guides/projects/) | Locked project/environment workflow | Lockfiles alone do not establish platform determinism or supply-chain safety |

Independent derivations in this repo: strict integer threshold rule; signed accumulator bound; zero-false-positive upper bound `1 - alpha^(1/n)`; minimum zero-event sample counts. Unit tests cover these calculations. General machine-learning plans are proposals, not reproduced research.

Do not repeat inherited proving times, vendor valuations, closed-system comparisons, model-card metric tables or dataset sizes as current facts. Re-read the exact primary source and conditions, record a pinned source, then reproduce where possible. Source links are not dataset admission or software-installation approval.
