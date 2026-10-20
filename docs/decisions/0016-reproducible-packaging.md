# 0016: Reproducible package builds and inventories

Date: 2026-10-20. Status: implemented engineering gate for W37 / #38; no package
release, licensing decision or scientific protocol adoption is supplied.

## Decision

Pin the complete six-package build environment and retain separate core and
optional-train installation gates. Build twice from the same reviewed Git-path
snapshot under a fixed epoch and actual recorded environment. Fail on unequal
archive hashes; rebuild the same wheel from the sdist and run installed fixtures
using that archive's scripts/data. Do not infer source distribution completeness
from a wheel smoke test alone.

The initial stricter archive check caught Hatch's automatic inclusion of a parent
`.gitignore`. Clean source roots now terminate VCS exclusion discovery with empty
`.git` and `.hg` boundary directories. Negative fixtures cover unexpected source
members so this behavior cannot silently change the archive inventory again.
The first installed-train run also exceeded a 20-second limit; the failed output
is retained. A diagnostic rerun passed unchanged, and the installed fixture now
has a 45-second timeout within the existing 60-second command budget. This is not
a performance result or an automatic compute-budget increase.

The source identity hashes sorted path/mode/size/content-hash records. It excludes
untracked local material and does not confuse a dirty snapshot with HEAD. The
artifact inventory checks exact membership and payloads, safe bounded regular
members, wheel RECORDs and recognizable credential patterns. Python tooling,
interpreter/platform/zlib and actual installed wheel/notice hashes travel with
the result. Each invocation retains a fresh output directory, including failures.

Initial hosted checks then exposed a portability error: reading a file can update
its access timestamp, so comparing complete `stat` records rejected unchanged
source. The snapshot now compares device/inode, mode, link count, ownership, size,
mtime and ctime, excluding access time. The [follow-up evidence](../../research/evidence/w37-source-snapshot-fix-2026-10-20.json)
retains the failing CI/reproduction and verifies both permitted reads and rejected
identity/modification changes.

## Limits and compatibility

[PACKAGING](../PACKAGING.md) specifies commands, bounds and supported CI matrix;
[DEPENDENCIES](../DEPENDENCIES.md) records actual upstream licence metadata and
notice provenance. No runtime classifier, error/event contract, fixture identity,
frozen conformance corpus or historical result changes. Optional training still
requires explicit installation; core checks assert its absence.

The repository is public by owner instruction. `LicenseRef-Proprietary` remains
unchanged and no public package release or open-source licence is inferred.
Installed software may contain bundled native components with additional notices;
retain and review their full artefact notices before authorized redistribution.
No model/data assets, operational keys, GPU jobs or hosted evidence are added.

The gate is not a reproducible OS image, a secret-classification oracle or a sandbox
against malicious build code or concurrent changes by the same OS account. It
checks equality within a recorded environment, not across all Python/platforms.
A source-tree hash is not release authorization or authenticated historical
execution. The full private release packet and reviewer/independent-verifier
results remain separate work.
