# 0047 — CPU host for the unchanged maximum proof roster

Date: 2026-10-21. W18 / issue #19.

PR #72 is merged as `89c2585619d4404d702439a46c825c8f8241cef9`; all 28 final
candidate jobs and all 14 merged-main jobs pass. Issue #19 stays open: staged
proof tooling is complete enough to merge under the owner's explicit instruction,
while complete encoder and independent qualification gates remain unfinished.

The L4 attempt from decision 0046 remained queued for requested hardware through
315 seconds of observation. Cancellation is confirmed. It produced no bucket
files or observed proof execution. Preserve its submission, status and logs; an
unavailable host is not a failed circuit. Download/check the empty inventory and
remove that temporary bucket before launching another job.

The full authenticated HF hardware inventory and the official
[hardware table](https://huggingface.co/docs/huggingface_hub/v1.27.0/en/guides/jobs)
expose `cpu-performance`: 32 vCPU, 256 GB RAM, 1,024 GB ephemeral storage,
USD 1.90/hour. This is a better fit for the CPU-only prover than renting unused
GPUs. Use one fresh experiment and empty temporary private bucket under the
owner's standing full approval. This is a deliberate host change after a
confirmed cancellation, not an automatic retry or additional permission gate.

Keep the exact reviewed image, Go/module/source hashes, optional patches,
fixture bytes, circuit pin, evaluator, case deadlines and negative roster from
0046. Fetch the already checked public runtime commit
`4bd86ba46775ea21e72efe65b257752622fa6897`; require every runtime source byte to
match merged main. The unchanged worker permits up to 48 Go execution threads
on this 32-vCPU host; this is an upper bound and may oversubscribe the host.
Record that limitation in diagnostic timings. No speed comparison is admitted.
The 170 GB RSS cap and 150 GB sampled stop remain unchanged despite larger RAM.

Keep the 7,200-second provider timeout, 7,800-second creation deadline, 24 GiB
per-file and 96 GiB total output caps. Limit the new job's compute estimate to
USD 4.15 (131 priced minutes). Combined new CPU/L4-attempt compute and temporary
storage remain below the existing USD 10 envelope, conservatively charging the
entire observed cancelled queue time at the L4 rate until billing is known.
No concurrent jobs, automatic retries, account top-up or scheduler. Keep the HF
token on the Mac; retrieve and verify all synthetic output bytes before deleting
the temporary bucket. Historical experiments stay immutable.

Pass/fail and scientific limits are unchanged: three maximum-capacity commitment
proofs, all frozen rejections and fresh local verification must pass. No result
qualifies the complete classifier/encoder, independent verifier or setup lineage.
