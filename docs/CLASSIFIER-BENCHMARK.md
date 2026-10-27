# Classifier backend benchmark

Recorded 2026-10-27. **Retain both research paths; keep gnark as the default.**
The exact rule, integer MLP and contextual CNN work under both backends, including
the same complete 96-byte relation and salted SHA-256 input commitment.

In this stateless harness, the warm nine-proof workflow has a **298.88 s Circle
median versus 781.25 s gnark**: a **2.61× ratio of medians**. Circle uses much more
memory and larger proof files. Gnark's instrumented proving stage is shorter in
the representative control; its combined assignment/R1CS/key parsing stage makes
its complete command slower. These results support an implementation trade-off,
not an equal-security or general proof-system speed ranking.

The [numeric evidence](../research/evidence/circle-classifiers-benchmark-2026-10-27.json)
contains every raw sample, stage, source/input/environment hash and all 3,925
retained artifact hashes. Median, minimum, maximum and inclusive-interpolation
IQR are recomputed from those records by the byte audit. No formal sample failed
or was discarded. Earlier failed provisioning fixtures remain separate below.

## What was measured

- One HF `cpu-upgrade` allocation: provider profile 8 vCPU / 32 GB; four proving
  threads, sequential workers. The guest reports AMD EPYC 7R13, 64 online logical
  CPUs and a 32,000,000,000-byte cgroup memory limit. No exclusive physical-host
  allocation is claimed.
- Three fresh and five warm complete workflows per backend, alternating backend
  order by repetition. Each workflow proves three classifiers on each of three
  frozen requests: **144 new measured proofs and 144 fresh Linux verifications**.
- Fresh uses an empty per-workflow object cache and new setup/preprocessing.
  Installed tools, downloaded locked dependencies and OS caches are reused;
  caches are not flushed. Warm reuses the first admitted preparation's files,
  then creates new proofs and fresh verifier processes.
- Models, thresholds and requests are frozen. Training, model downloads and
  global tool bootstrap are outside sample wall time. Full sample wall time
  includes compilation/setup where applicable, host witness work, input copies,
  commands, caller checks, separate native baseline observations and bookkeeping.
- The fixed MLP is always-allow in this 96-byte domain; rule/CNN controls provide
  blocking outcomes. This is an engineering comparison, not a quality evaluation.
  See the [score bound](CIRCLE-CLASSIFIERS.md#mlp-decision-limitation).

The [frozen HF plan](../configs/circle-classifiers/hf-plan.json) and
[decision 0084](decisions/0084-hf-classifier-comparison.md) precede this campaign.
The exploratory Mac acceptance runs are not pooled into these measurements.

The fixed Circle inputs produce nine distinct serialized proof hashes across
72 measured proving invocations. All 72 commands and fresh verifications execute;
repeated deterministic output is expected. Gnark produces 72 distinct proof
hashes across its 72 invocations.

## Complete workflow

Seconds below are **median [minimum–maximum]; IQR**. Each observation contains
nine proofs, their fresh verifications and caller checks. RSS is the maximum
sampled process-tree sum across the phase, in decimal GB; it is not unique physical
memory or GPU memory.

| Phase | Backend | Successful/attempted | Full wall time, s | Maximum tree RSS, GB |
|---|---|---:|---:|---:|
| fresh | gnark/Groth16 | 3/3 | 1248.51 [1140.73–1283.19]; IQR 71.23 | 2.55 |
| fresh | STWO Circle STARK | 3/3 | 428.41 [374.91–445.05]; IQR 35.07 | 19.86 |
| warm | gnark/Groth16 | 5/5 | 781.25 [632.97–1004.78]; IQR 91.11 | 2.65 |
| warm | STWO Circle STARK | 5/5 | 298.88 [289.26–416.51]; IQR 119.78 | 19.96 |

The fresh median ratio is 2.91×; the warm ratio is 2.61×. These are ratios of
workflow medians, not paired speedup confidence intervals. The small sample
counts and observed spread limit performance conclusions.

## Shared compilation and setup

The following medians use the three fresh workflows. Compilation serves nine
proofs per workflow. Each classifier's setup serves its three requests; dividing
that setup by three gives the declared per-request amortization. Warm uses the
first preparation, whose reuse must not be mistaken for zero per-proof costs.


| Backend | Shared preparation components / workflow, s | Amortized / complete request (÷3), s |
|---|---:|---:|
| gnark | 491.53 [473.65–494.37]; IQR 10.36 | 163.84 [157.88–164.79]; IQR 3.45 |
| circle | 103.62 [92.16–105.52]; IQR 6.68 | 34.54 [30.72–35.17]; IQR 2.23 |

This component view sums binary-compilation command walls, all setup/preprocessing
command walls and Circle host program construction for each fresh observation.
It divides each sum by the three complete requests in that workflow. It is not
a separate measurement of the entire preparation function; caller enrollment
and other overhead remain included in full workflow wall time. The engine
components below are already inside setup commands and must not be added twice.

| Backend | Binary compilation, median s [range]; IQR |
|---|---:|
| gnark/Groth16 | 56.21 [53.46–58.71]; IQR 2.63 |
| STWO Circle STARK | 68.47 [60.34–70.73]; IQR 5.20 |

| Classifier | gnark R1CS compile/read, s | gnark setup, s | gnark setup serialization, s | Circle host program construction, s | Circle engine preprocessing, s |
|---|---:|---:|---:|---:|---:|
| Rule | 1.855 | 96.24 | 0.6883 | 3.645 | 3.047 |
| MLP | 1.841 | 96.44 | 0.5914 | 4.155 | 2.918 |
| CNN | 7.692 | 209.2 | 1.129 | 11.2 | 6.091 |

All individual setup/compilation observations and their hashes are in
`byte_audit.raw_samples[*].shared_stages`. Setup-command wall time additionally
includes input materialization, parsing, writing and worker overhead. Fixed
weights share R1CS compilation or the Circle graph/preprocessing commitment;
separate weight-commitment time is `null`, with a reason, rather than zero.

## Per-proof warm results

Each row has five observations for the named request/classifier/backend. Proving
and command times are seconds, formatted as median [range]; IQR. Host witness
work and proof-only verification show medians; their full spreads, fresh results
and all individual measurements are in the numeric evidence. Proof bytes use the
backend's existing uncompressed envelope: gnark's compressed-point binary format
or canonical STWO JSON. They exclude keys, enrollment and witness files.

### `allow`

| Backend / classifier | Host witness, s | Engine proving, s | Complete prover command, s | Fresh proof-only verifier, s | Proof bytes |
|---|---:|---:|---:|---:|---:|
| gnark/Groth16 / Rule | 0.00031 | 4.32 [4.19–6.09]; IQR 0.24 | 54.20 [50.24–74.89]; IQR 2.54 | 4.039 | 292 |
| gnark/Groth16 / MLP | 0.0003471 | 4.56 [4.17–5.52]; IQR 0.77 | 52.67 [50.53–62.79]; IQR 2.86 | 3.989 | 292 |
| gnark/Groth16 / CNN | 0.005283 | 8.35 [6.39–12.65]; IQR 1.11 | 137.42 [117.49–155.89]; IQR 13.09 | 3.913 | 292 |
| STWO Circle STARK / Rule | 3.901 | 8.82 [5.98–13.75]; IQR 4.97 | 17.84 [12.15–26.82]; IQR 8.93 | 0.316 | 1,950,445 |
| STWO Circle STARK / MLP | 4.46 | 8.88 [6.07–13.37]; IQR 2.62 | 18.31 [12.39–27.72]; IQR 7.27 | 0.2893 | 1,931,643 |
| STWO Circle STARK / CNN | 12.01 | 17.89 [12.99–26.66]; IQR 8.12 | 35.91 [25.70–52.67]; IQR 17.11 | 0.3226 | 2,132,638 |

### `cnn-block`

| Backend / classifier | Host witness, s | Engine proving, s | Complete prover command, s | Fresh proof-only verifier, s | Proof bytes |
|---|---:|---:|---:|---:|---:|
| gnark/Groth16 / Rule | 0.0003639 | 5.31 [3.37–6.89]; IQR 0.39 | 58.89 [42.18–79.81]; IQR 8.14 | 4.027 | 292 |
| gnark/Groth16 / MLP | 0.0003932 | 4.82 [3.52–6.83]; IQR 0.68 | 55.23 [43.18–78.11]; IQR 6.70 | 3.655 | 292 |
| gnark/Groth16 / CNN | 0.006224 | 7.53 [5.88–11.10]; IQR 1.23 | 128.69 [99.42–187.06]; IQR 13.55 | 3.689 | 292 |
| STWO Circle STARK / Rule | 3.907 | 9.07 [6.23–12.74]; IQR 4.41 | 17.74 [12.48–26.05]; IQR 9.65 | 0.3759 | 1,934,423 |
| STWO Circle STARK / MLP | 4.58 | 9.17 [7.55–13.17]; IQR 4.35 | 18.78 [14.73–26.41]; IQR 8.92 | 0.2987 | 1,913,275 |
| STWO Circle STARK / CNN | 12.05 | 24.23 [17.57–26.26]; IQR 7.04 | 46.62 [34.19–52.14]; IQR 12.34 | 0.3384 | 2,156,856 |

### `rule-block`

| Backend / classifier | Host witness, s | Engine proving, s | Complete prover command, s | Fresh proof-only verifier, s | Proof bytes |
|---|---:|---:|---:|---:|---:|
| gnark/Groth16 / Rule | 0.0003298 | 4.62 [3.33–7.48]; IQR 0.39 | 53.13 [41.75–83.99]; IQR 5.43 | 3.467 | 292 |
| gnark/Groth16 / MLP | 0.0003348 | 4.70 [3.43–6.11]; IQR 0.86 | 51.60 [41.65–68.66]; IQR 5.47 | 3.533 | 292 |
| gnark/Groth16 / CNN | 0.005559 | 7.16 [5.61–10.87]; IQR 0.69 | 119.34 [95.60–180.60]; IQR 5.35 | 3.593 | 292 |
| STWO Circle STARK / Rule | 4.23 | 10.79 [8.80–14.02]; IQR 4.25 | 23.60 [17.87–28.15]; IQR 8.77 | 0.2935 | 1,952,226 |
| STWO Circle STARK / MLP | 5.012 | 10.84 [8.10–13.65]; IQR 3.32 | 22.19 [16.99–27.66]; IQR 7.79 | 0.3077 | 1,961,706 |
| STWO Circle STARK / CNN | 13.16 | 17.27 [15.82–25.93]; IQR 6.74 | 38.61 [32.18–51.82]; IQR 11.67 | 0.3476 | 2,129,545 |

### Interpreting the stages

Gnark's `parse_assignment_and_keys` covers assignment, R1CS and proving-key
loading. On the warm `allow` rule control its median is much larger than the
proving stage. The timing does not isolate which input file accounts for that
parsing cost. Circle rebuilds twiddles and its preprocessing/model commitment for
every proof, including warm runs; those costs remain charged to the complete
command. It does not reuse an in-memory preprocessing cache.

Gnark constraint solving occurs inside `groth16.Prove`. Circle's host witness
work includes graph construction, native parity checks and witness encoding;
its engine separately builds and commits base and interaction traces. An
isolated engine-stage ratio therefore describes different work boundaries.
Fresh verification also compares native Rust/STWO with separate pure-Python
py-ecc, including process/import/decoding costs. It is not a native-library
comparison of cryptographic verification algorithms.

All engine stage medians below use the warm `allow` control. Raw records retain
each stage separately; no input/commitment work is subtracted from workflow wall.

| Backend / stage | Rule, s | MLP, s | CNN, s |
|---|---:|---:|---:|
| gnark/Groth16 / `parse_assignment_and_keys` | 47.42 | 47.7 | 126.4 |
| gnark/Groth16 / `witness` | 0.0005671 | 0.0005019 | 0.004473 |
| gnark/Groth16 / `groth16_proving` | 4.323 | 4.558 | 8.35 |
| gnark/Groth16 / `proof_serialization` | 0.003102 | 0.005084 | 0.004071 |
| STWO Circle STARK / `admission_twiddles_and_transcript` | 0.1318 | 0.1364 | 0.2305 |
| STWO Circle STARK / `preprocessing_and_model_commitment` | 2.792 | 3.043 | 5.767 |
| STWO Circle STARK / `base_trace_generation` | 0.02005 | 0.02836 | 0.05056 |
| STWO Circle STARK / `base_trace_commitment` | 2.303 | 2.192 | 4.543 |
| STWO Circle STARK / `interaction_generation` | 0.1699 | 0.1985 | 0.3526 |
| STWO Circle STARK / `interaction_commitment` | 2.956 | 2.972 | 5.791 |
| STWO Circle STARK / `stark_proving` | 8.815 | 8.881 | 17.89 |

Circle's additional CLI parse and serialization/write times are preserved under
`worker_timing.cli`; per-proof serialization spreads also appear in the summary.

## Native execution and caller work

These medians cover **all three classifiers on one request**, with admitted
models already loaded. Native-only includes UTF-8 preparation, complete features
and integer inference. Native-plus-binding includes request/commitment work and
native inference. The final caller check reruns native inference too; it is a
separate timing observation, not a residual obtained by subtracting two timers.

| Warm observation | Native-only, s | Native plus binding, s | Final caller binding, s |
|---|---:|---:|---:|
| gnark / `allow` | 0.8746 | 1.834 | 1.895 |
| gnark / `cnn-block` | 0.914 | 1.879 | 1.902 |
| gnark / `rule-block` | 0.8481 | 1.905 | 1.845 |
| circle / `allow` | 0.9389 | 1.805 | 1.831 |
| circle / `cnn-block` | 0.8325 | 1.89 | 2.199 |
| circle / `rule-block` | 1.072 | 2.235 | 1.868 |

The current workflow does not demonstrate a cost saving over native rerun.
A relying party already able to rerun these small classifiers should compare
that option before adding proof-system and enrollment assumptions.

## Artifacts and parameters

| Artifact per classifier | Rule | MLP | CNN |
|---|---:|---:|---:|
| gnark proving key, bytes | 121,484,003 | 122,438,113 | 296,183,989 |
| gnark verification key, bytes | 5,536 | 5,536 | 5,536 |
| gnark R1CS, bytes | 24,577,799 | 24,660,971 | 54,098,539 |
| Circle prover program JSON, bytes | 37,734,097 | 43,590,322 | 117,166,300 |
| Circle engine enrollment JSON, bytes | 643 | 644 | 644 |

All 72 gnark proof files are 292 bytes. The 72 measured Circle JSON proof files
range from 1,913,275 to 2,156,856 bytes. These are serialized proof sizes, not
complete evidence bundles. The Circle verifier consumes enrolled parameters,
public inputs and a proof; it does not need the prover program or full witness.
The retained archive inventory contains 4,453,529,108 regular-file payload bytes;
the gzip archive is 2,084,726,744 bytes. The earlier final storage snapshot records
4,453,415,564 logical bytes before result metadata is written. Allocated-block
sums are not unique physical storage.

Gnark uses Groth16/BLS12-381, with owner-controlled pre-proof setup and a separate
py-ecc verifier. Fresh setup has no independently reviewed ceremony. Circle uses
pinned direct STWO 2.2.0, M31/QM31, Blake2s, 16 PoW bits, 80 FRI queries, blowup
16, fold step one and final-layer log degree five. Its source and preprocessing
root are independently enrolled before proving. The concrete profiles do not
establish equal soundness; both compiler/program mapping and setup/enrollment
assumptions matter. Neither implementation gains independent security
qualification, hardware provenance or witness hiding from this experiment.

## Independent retained-input checks and LLM composition

The byte audit verifies all serialized artifact hashes and recomputes the frozen
statistics. A separate owner-input check matches 112 captured source files and
all five captured request/quantization snapshots to the pre-upload archives.

Fresh Mac processes then verify **all 144 classifier proofs**: 72 Circle proofs
and 72 Groth16 proofs. This takes 119.73 s across 96 processes (one process per
Circle proof, one per three-proof py-ecc set). These are postflight checks,
excluded from the matched Linux measurements. They reconstruct caller inputs and
require the original circuit pins and the caller's Mac Circle enrollment.
Shared cryptographic implementations do not constitute independent verifier
implementations or an audit.

Three additional Circle proofs, excluded from benchmark statistics, bind the
fixed TinyLlama request. The Mac composition check freshly verifies those and
**23 retained SASH proofs / 22 residual links**, rejects all **16 changed-binding
and coverage cases**, and finishes in **11.13 s** including hashes and host work.
It joins results in host code, without recursion or new LLM proving. Verdicts
are `[1,1,0]`, so integrity passes while policy release is false. The original
55-file LLM verifier identity is unchanged. [Join command and boundary](CIRCLE-CLASSIFIERS.md#llm-request-composition).

## Failures, resources and reproducibility

Earlier HF provisioning fixtures are retained and excluded from the formal
matched sample set. Each correction has its own committed source/profile:

| Fixture | Result | Running seconds | Reason or scope |
|---|---|---:|---|
| v1 | Error | 59.640 | Missing ignored output parent before admission |
| v2 | Error | 43.616 | Go embedded graph JSON omitted from isolated compiler inventory |
| v3 | Error | 300.002 | Isolated pairing entrypoint imported an unavailable optional module |
| v4 | Pass | 737.432 | Real rule proof and fresh verification under each backend; plumbing only |

The complete formal HF job runs 10,901.434 s; measured campaign execution is
10,675.380 s. At the verified $0.03/hour rate, formal running compute is an
estimated **$0.091**, or **$0.100** including all four provisioning fixtures.
These are not invoices and omit actual storage/startup billing. The predeclared
startup/storage-inclusive admission ceiling was **$0.30**. All five jobs are
terminal, their outputs retained, and their owned buckets deleted. The campaign's
maximum sampled process-tree RSS is 19,964,153,856 bytes, below the 28 GiB stop;
raw output is below its 16 GiB limit. No automatic paid retry, top-up or ongoing scheduler was
introduced.

- Formal source: `bc5bc0da325f0f9187a1cfc11b35f639cf4e3b81`.
- Source archive SHA-256: `0ed57807a7b0c756e9382a48098d20f9f64847a06615fbe08be3ce8362e91b3a`.
- Inputs archive SHA-256: `379d132caf2700a89de4f5b52f1cabc74508f6ebfc9d7a3544217984fa83a0e0`.
- Retained output archive SHA-256: `5825b1e97da2259e43c499e383c2d5908a00232bdcb75ef78873b40e0ec54a97`.
- Caller Circle enrollment: `56c29c74a4efa0443bff84cc516349b0369360e2feaf347b871b860b06cd635e`.
- [Completed job](https://huggingface.co/jobs/abdelstark/6ae0fe1741e90535df767b67).

Use the [workflow, frozen cloud launch and postflight commands](CIRCLE-CLASSIFIERS.md)
to rerun from admitted inputs. New runs use new directories and retain failures;
do not substitute a prover-supplied enrollment or reuse a saved success flag.
An [actual Make entrypoint reproduction](../research/evidence/circle-make-e2e-2026-10-27.json)
also builds both locked Mac binaries, generates nine proofs, freshly verifies
them and passes the 63/18/3 mutation/swap/roster checks. Its 97.81 s driver time
excludes compilation and is not pooled into the Linux benchmark.
The numeric evidence retains all raw values, complete command/resource records,
input/output hashes and unavailable-value reasons. Historical gnark, Mac
acceptance and LLM/GPU results remain separate and unchanged.

## Recommendation

Retain the specialized Circle path as an experimental alternative and keep gnark
as the default. Circle's complete workflow is faster here, while its roughly
20 GB peak tree RSS and megabyte JSON proofs impose substantial costs. Gnark has
much smaller proofs, an independent py-ecc verifier and shorter instrumented
proving stages in the representative control; its stateless parse/load costs
make its complete workflow slower. Persistent trusted preparation could change
both results and requires a new frozen benchmark.

This decision covers the fixed research workload. Model quality, longer inputs,
witness hiding, audited setup/compiler mapping and operational deployment remain
separate work. It does not adopt a production policy or claim a superior proof
system at equal security.
