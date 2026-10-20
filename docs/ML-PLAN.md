# ML engineering plan

Decision: preserve the hybrid architecture, establish a measured classifier/prover Pareto frontier, then choose a first provable student. Do not pick an encoder by parameter count or a vendor's headline benchmark. All model downloads, datasets, external inference and GPU campaigns remain separately admitted work.

## Targets and baselines

Separate policy tasks: prompt injection, jailbreak/attack intent and response-policy violations. An injection detector is not a response safety classifier. Policy definitions, annotation instructions, abstention and disagreement resolution precede training. The current marker fixture is none of these tasks.

Start with majority/block-all/pass-all sanity checks, the shipped byte-logistic floor, a word/character n-gram baseline, an existing task-matched guard and one compact encoder. These additional baselines are planned, not shipped. Candidate encoder families from the inherited packet include classic BERT, Ettin and DeBERTa. Benchmark exact operator graphs, tokenizer and sequence policy before selecting a checkpoint. Relative attention, layer normalization, nonlinear activations, padding and dynamic shape support can dominate proof integration; do not infer support from ONNX export alone.

Use Laya as a candidate open decision-model teacher or hardware-tier classifier after checking the exact checkpoint, licence and serving surface. Do not assert its parameter count, task quality or relative speed from the historical packet without fresh model/config/benchmark verification. Hosted Jev-style systems are comparison candidates only on explicitly approved public/synthetic inputs; no confidential transcripts leave the research environment.

## Dataset pipeline and governance

The source packet inventories possible Hub datasets and tooling. None is admitted by being listed there. For each selected source, retain exact revision, licence text/hash, commercial/redistribution/derivative restrictions, consent/privacy review, original task/labels, contamination risk and intended use. Gated terms require the owner's acceptance. Store approval evidence outside the config allowlist. Keep raw downloads and checkpoints out of git.

Normalize into the strict record schema without silently altering model input. Preserve raw byte hashes and reversible provenance for any cleaning. Deduplicate before grouped splitting, with exact match plus separately validated near-duplicate/family clustering. Human-review policy mappings and difficult negatives. Synthetic generators pin prompt/template/model/revision/seed and parent lineage; generated variants remain in the parent's split. A generator's labels are weak supervision, not ground truth. Audit a prespecified stratified sample with adjudication and agreement rates.

No curation framework is needed for 52 synthetic records. Add NeMo Curator or equivalent only when measured scale and a documented pipeline justify the dependency, and validate its licence and transformations first.

## Training, distillation and quantization

1. Establish the task-specific real-data baseline on an approved frozen split. Report balanced and naturally occurring prevalence separately. Optimize calibrated low-FPR operation, not just balanced accuracy.
2. Train the selected compact encoder in a bounded, pinned environment, with at least three prespecified seeds for a confirmatory comparison. Fit tokenizer/preprocessing only where applicable on train, never test. Save optimizer/scheduler/RNG state, checkpoint hashes and termination reasons.
3. Distill the teacher into the student using train-only teacher outputs; record temperature, hard/soft loss weights, teacher identity and any label disagreement. Independently human-check difficult teacher-positive and teacher-negative slices. Do not distill away policy uncertainty.
4. Compare float, PTQ integer and, only if justified, QAT candidates using identical inputs. Export the integer semantics as normative. Freeze scales, signed representation, rounding, clipping, accumulators and mask behavior. Report decision disagreements near the threshold and on long text.
5. Calibrate the exported integer model. Freeze before test. Run the real proof backend on the exact graph/weights selected; retraining after compiler failure changes the experiment.

The executable baseline implements only float64 logistic fitting, power-of-two PTQ and integer calibration. It does not implement teacher inference, encoder training, distillation, QAT, ONNX export or proving. Training long inputs is rejected until a justified multiple-instance or chunk-labeling objective exists.

## Operator and system bake-off

Predeclare sequence lengths and batch size, then probe embedding lookup, matmul, signed scaling, normalization, GELU/ReLU alternatives, softmax/attention, masks and final threshold. Include empty input, Unicode, padding, extreme activations and length boundaries. Capture compiler rejection and numerical mismatch, not just successful paths. Measure constraints/rows or equivalent backend units, witness/prove/verify time and peak memory. A 17M model with hostile operators may cost more than a larger friendly graph.

First compare byte-linear/rule circuits, then a tiny MLP, then one compact encoder. EZKL is a candidate ONNX/Halo2 path, not an integrated or endorsed choice. A zkVM is an alternate semantics path with a different cost model. Select on quality, exactness, total latency/memory, setup assumptions, licence and reviewability. No speedup or feasibility number is asserted before local reproduction.

## Resource accounting and gates

Training memory budget must include weights, gradients, optimizer state, activations and allocator overhead. For `P` parameters, Adam-style mixed precision can require roughly `16P` bytes for parameter/master/gradient/moments under one common layout, excluding activations; inspect the actual framework rather than treating the estimate as a reservation. Proving memory is measured separately. Tokens per second is not proofs per second.

Bootstrap authority covers one-thread CPU fixture runs only. A GPU proposal specifies dataset/teacher access, host, hours, cost cap, storage, kill condition and owner approval. No autonomous budget escalation, paid API fallback or unbounded search. Failure to meet a latency budget should shrink the graph or change the target statement, not weaken the verifier.
