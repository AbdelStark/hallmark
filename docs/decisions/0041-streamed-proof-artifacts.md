# 0041 — Stream pinned proof artifacts within existing caps

Date: 2026-10-21. W18 / issue #19. Software boundary preparation.

The maximum commitment now compiles on the approved HF host, but setup and
proving are unmeasured. The current Go reader holds the entire serialized file
before decoding; the Python scaling controller similarly retains setup files as
bytes and copies them between workers. The smallest boundary fixture also shows
that the old Go reader accepts a symbolic link.

Stream the Go decoder input through the existing 256 MiB cap, checking regular
files, single links, exact reported/observed consumption and detected metadata or
path changes. Preserve checked subgroup deserialization and the real verifier.
The underlying gnark constraint decoder still allocates its own serialized input;
this removes one adapter copy, not all decoder allocation. Serialized length
limits do not bound every allocation implied by a malformed header.

Hash worker files in bounded chunks. Carry setup artifacts between commitment
scaling cases as path, digest and size pins from the retained producing receipt.
Copies use exclusive private files, verify the source pin before the next worker,
and retain failed outputs. Keep small text/proof mutations as bounded bytes.
Do not raise artifact caps or add a maximum proving command in this change.

Freeze source/build inputs before tests. Check invalid/truncated/trailing files,
wrong byte counts, links, mutation and failed synchronization, plus bounded Python
copy allocation. Run a tiny actual-proof unit fixture and reverify a retained
commitment proof against its independently retained result hash in a fresh worker.
The HF bootstrap includes the new file-boundary tests in future pinned manifests;
it excludes the tiny proof unit test from its compile-only prerequisite roster.
Historical manifests and results remain unchanged. New controller/binary identities
cannot replace historical source identities.

The receipt audit retains the original 5,540-second base charge and all later
ancillary allowances. Remove only redundant rounding/reservation margins: the
recorded prior total is 7,135.886826 seconds, rounded up to 7,136. Reserve the
remaining 64 seconds, including eight seconds for preparation/audit overhead.
The timed wrapper stops further validation at its remaining allocation. Use the
standard project mypy cache; this is correctness checking, not a performance
comparison. Require `make check`, the core package gate and exact-head hosted
training/guard checks. No additional cloud job or authority increase.

This gate establishes bounded adapter I/O at the existing sizes. Whole-graph
setup/proving, a complete admitted encoder, operational enrollment, independent
verification/security/hiding/setup review and genuine hardware remain open.
