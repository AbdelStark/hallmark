# 0048 — Execute proof workers on local disk and retain outputs afterward

Date: 2026-10-21. W18 / issue #19.

The CPU attempt in decision 0047 passes the dependency/Go fixture gates, all
seven circuit fingerprints, network denial, tiny setup/prove/verify and changed
public-input rejection. Maximum export reports 40,015,721 constraints and
141.093003386 seconds. The controller then raises `ValueError("changed file")`
while checking an output on the mounted bucket. Its maximum worker cost record
was not completed, so maximum RSS and CPU usage are unavailable.

Download all 37 files before removing the temporary bucket. The 2,566,643,378-byte
circuit exactly matches the independently retained Mac SHA-256
`cd91ff70e706fb2d3aecb83d40eae5d82c34611923b67b16a539f69291d0e489`.
This supports a bucket file identity/metadata change during inspection rather
than different retained circuit bytes. The exact changed stat field was not
logged. Do not weaken the file-integrity guard or relabel the failed run a pass.
No maximum setup or proof occurred.

Change only execution/storage plumbing: workers use the job's local ephemeral
disk. After the controller stops, a separate bounded child copies every complete
and failed output into a fresh private bucket, pinning each source file's bytes.
It rejects links, unsafe directories, changed sources, excess size and overwrite;
only a complete copy writes the retention manifest. Verify downloaded bytes
against both worker costs and the retention manifest before deleting the bucket.
This does not establish remote filesystem durability or trusted hardware.

The mutable source paths are the optional maximum controller, HF bootstrap and
focused retention tests. Circuit, patches, native fixtures, evaluator roster,
thresholds and case budgets are unchanged. New protocol/source/run identities
are required. The smallest copy fixture must retain partial failures and reject
unsafe paths and oversized files; the existing tiny real proof runs before the
maximum work. Run repository/package checks and exact-runtime-head Linux CI
before submission. No prior failed proof outcome is reused as successful evidence.

Use one fresh `cpu-performance` job under standing approval. Keep the 170 GB RSS,
150 GB sampled stop, 48-thread upper bound on 32 vCPU, 24 GiB/file and 96 GiB output
caps. The proof controller retains its 6,600-second campaign budget. Add a separate
900-second output-copy window; cap the bootstrap at 8,350 seconds, provider runtime
at 8,400 seconds and creation-to-cancellation at 9,000 seconds. New compute is
bounded by USD 4.80 (151 priced minutes). Combined with conservative charges for
both earlier attempts and temporary storage, retain the USD 10 campaign ceiling.
No concurrent job, automatic retry, top-up, private input upload or scheduler.

Pass still requires all three commitment proofs and the frozen rejection roster,
then fresh local verification under separately retained key/proof/native-input
pins. Full classifier/encoder qualification, independent review, hiding and
accepted setup lineage remain separate gates.
