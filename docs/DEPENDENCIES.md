# Dependency licences and restrictions

This is an engineering inventory, not a legal opinion or release approval.
Hallmark adopted the [MIT licence](../LICENSE.md) at the owner's explicit request
on 2026-10-22. That grant covers original project material; third-party software,
models and datasets retain their own terms. Package publication remains a separate
release action. Source distributions include authored synthetic fixtures, but no
external model checkpoints, private datasets or operational keys. Historical
licence labels in frozen records describe their original admission; see
[decision 0063](decisions/0063-mit-license.md).

## Reviewed upstream metadata

The documentation site has a separate [locked project](../website/pyproject.toml)
and [dependency review](../website/dependencies.json). It pins **Zensical 0.0.73**
without changing the inference lockfile or native verifier identity. All locked
docs artifacts match exact-version PyPI metadata; licence metadata and installed
notice-file hashes are retained. This is an engineering review, not a security
qualification.

Self-hosted **Newsreader 5.3.0** and **Public Sans 5.3.0** font distributions use
OFL-1.1; their notices are bundled. **KaTeX 0.19.1** is distributed under MIT with
its notice. [Asset provenance](../website/assets/vendor/sources.json) records
source release URLs, archive SHA-256/SHA-512 integrity and per-file hashes.
These optional site dependencies are separate from the historical inference
reviews below. See [documentation maintenance](DOCUMENTATION.md).

On 2026-10-20, the [guard metadata review](../research/evidence/w15-guard-dependencies-2026-10-20.json)
matches all **684 locked distribution hashes** for **52 packages** against each
exact version's PyPI JSON response. It extends the preserved
[W37 review](../research/evidence/w37-dependencies-2026-10-20.json) of 32 packages
without changing their versions. Coverage includes build, core, train, guard and
development packages, including platform-conditional lock entries. The JSON records source
URLs, metadata hashes, licence fields, Python requirements and dependency declarations.
The table below preserves the original entries; the current JSON also inventories
the 20 added guard dependencies. A broad classifier
such as “BSD License” is not a substitute for the full notice.

| Package | Locked version | Published licence expression or label |
|---|---|---|
| [annotated-types](https://pypi.org/project/annotated-types/0.8.0/) | 0.8.0 | MIT |
| [cbor2](https://pypi.org/project/cbor2/5.9.0/) | 5.9.0 | MIT |
| [cffi](https://pypi.org/project/cffi/2.1.1/) | 2.1.1 | MIT-0 |
| [cloudpickle](https://pypi.org/project/cloudpickle/3.1.2/) | 3.1.2 | BSD-3-Clause |
| [colorama](https://pypi.org/project/colorama/0.4.6/) | 0.4.6 | BSD License |
| [coverage](https://pypi.org/project/coverage/7.16.2/) | 7.16.2 | Apache-2.0 |
| [cryptography](https://pypi.org/project/cryptography/50.0.2/) | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| [hatchling](https://pypi.org/project/hatchling/1.32.4/) | 1.32.4 | MIT |
| [iniconfig](https://pypi.org/project/iniconfig/2.3.1/) | 2.3.1 | MIT |
| [joblib](https://pypi.org/project/joblib/1.6.0/) | 1.6.0 | BSD-3-Clause |
| [librt](https://pypi.org/project/librt/0.16.0/) | 0.16.0 | MIT |
| [mypy](https://pypi.org/project/mypy/1.20.2/) | 1.20.2 | MIT |
| [mypy-extensions](https://pypi.org/project/mypy-extensions/1.1.0/) | 1.1.0 | MIT notice in the hash-verified wheel; metadata fields absent |
| [narwhals](https://pypi.org/project/narwhals/2.27.1/) | 2.27.1 | MIT |
| [numpy](https://pypi.org/project/numpy/2.5.4/) | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| [packaging](https://pypi.org/project/packaging/26.3/) | 26.3 | Apache-2.0 OR BSD-2-Clause |
| [pathspec](https://pypi.org/project/pathspec/1.1.1/) | 1.1.1 | Mozilla Public License 2.0 (MPL 2.0) |
| [pluggy](https://pypi.org/project/pluggy/1.7.0/) | 1.7.0 | MIT |
| [pycparser](https://pypi.org/project/pycparser/3.11/) | 3.11 | BSD-3-Clause |
| [pydantic](https://pypi.org/project/pydantic/2.14.1/) | 2.14.1 | MIT |
| [pydantic-core](https://pypi.org/project/pydantic-core/2.50.1/) | 2.50.1 | MIT |
| [pygments](https://pypi.org/project/pygments/2.21.0/) | 2.21.0 | BSD-2-Clause |
| [pytest](https://pypi.org/project/pytest/9.1.1/) | 9.1.1 | MIT |
| [pytest-cov](https://pypi.org/project/pytest-cov/7.1.0/) | 7.1.0 | MIT |
| [ruff](https://pypi.org/project/ruff/0.17.1/) | 0.17.1 | MIT |
| [scikit-learn](https://pypi.org/project/scikit-learn/1.9.1/) | 1.9.1 | BSD-3-Clause |
| [scipy](https://pypi.org/project/scipy/1.18.1/) | 1.18.1 | BSD License |
| [threadpoolctl](https://pypi.org/project/threadpoolctl/3.7.0/) | 3.7.0 | BSD-3-Clause |
| [tomlkit](https://pypi.org/project/tomlkit/0.15.2/) | 0.15.2 | MIT |
| [trove-classifiers](https://pypi.org/project/trove-classifiers/2026.9.21.13/) | 2026.9.21.13 | Apache Software License |
| [typing-extensions](https://pypi.org/project/typing-extensions/4.16.0/) | 4.16.0 | PSF-2.0 |
| [typing-inspection](https://pypi.org/project/typing-inspection/0.4.4/) | 0.4.4 | MIT |

`mypy-extensions` has no licence expression, text or classifier in its published
JSON metadata. The review therefore downloaded its locked universal wheel,
verified the SHA-256 and recorded the MIT notice's path and hash. No package code
was executed for this metadata review.

## Installed-platform inventories

Each package gate records the exact installed name/version, wheel tags, unique
matching locked archive filename/URL/SHA-256, METADATA hash, declared dependencies
and licence/notice-file hashes. Installations require hashes, refuse source builds
and check dependency consistency. The project wheel is hashed separately and
imports must resolve to the new environment, not an editable checkout.

The selected binary archive and bundled-library notices can differ by Python,
platform and architecture. Retain the full upstream notices alongside any approved
redistribution; do not replace them with this table. NumPy, SciPy and cryptography
wheel notices need review as complete artifacts, including their bundled components.
No claim is made that permissive Python metadata covers every bundled library.

Python and uv are host tools, not vendored runtime dependencies. The package report
records interpreter version/ABI/binary hash, OS/architecture, zlib runtime and the
uv version/binary hash. Retain their own upstream notices and installation provenance.
Build equality is checked within that recorded environment, not asserted across
all machines. The build matrix and limits are in [PACKAGING](PACKAGING.md).

The optional guard uses ONNX 1.23.2 (Apache-2.0), ONNX Runtime 1.31.0 (MIT package
licence plus its full third-party notices), and tokenizers 0.23.3 (Apache-2.0).
All new selected Mac CPython 3.12 wheels were hash-checked before installation.
The flatbuffers/tokenizers wheels omit full licence files; pinned upstream Apache
notices are retained separately. The runtime's complete notices include MPL and
component-specific terms, not just MIT. No third-party binary redistribution is
part of this work. This bounded local-use review is not an independent security
audit, legal warranty, proof/hardware admission or package-release approval.

The optional `llm` extra exposes the already locked `huggingface-hub==2.2.0`
dependency for the foreground Jobs controller. The [2026-10-23 lock review](../research/evidence/llm-extra-dependencies-2026-10-23.json)
checks that all 52 third-party package entries are unchanged and carries forward
their earlier metadata and licence evidence; it does not claim a new upstream
metadata observation. The [LLM workflow](LLM-PROOF.md)
downloads the separately pinned SASH source, its locked Python witness environment
and the Apache-2.0 TinyLlama checkpoint. The [source review](../research/real-llm-proof-plan.md)
records their revisions and licence scope. These model files, the CUDA build image
and the resulting prover binary are not part of Hallmark's wheel or source archive.
