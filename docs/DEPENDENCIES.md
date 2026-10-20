# Dependency licences and restrictions

This is an engineering inventory, not a legal opinion or release approval.
The repository is public, but Hallmark remains `LicenseRef-Proprietary` and no
open-source licence or package publication is authorized by this inventory.
No model, dataset, checkpoint or operational key is included in the packages.

## Reviewed upstream metadata

On 2026-10-20, the [metadata review](../research/evidence/w37-dependencies-2026-10-20.json)
matched all **518 locked distribution hashes** for **32 packages** against each
exact version's PyPI JSON response. It covers build, core, train and development
packages, including platform-conditional lock entries. The JSON records source
URLs, metadata hashes, licence fields, Python requirements and dependency declarations.
The table preserves upstream expressions or classifier labels; a broad classifier
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

No new model-runtime, tokenizer, proof or hardware dependency is admitted here.
Those still require their task-specific version, licence, security, host and owner
review. Metadata and archive hashes do not establish absence of vulnerabilities.
