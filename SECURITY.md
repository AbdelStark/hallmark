# Security and research limits

This is pre-production research in a public repository, not a security product or safety certification. There is no genuine TEE or ZK integration. Do not use baseline replay as a proof, or the marker classifier to make safety decisions.

Report concerns privately to the repository owner through an existing approved private channel. Do not open a public issue or upload transcripts, model weights, secrets or exploit evidence to an external service. No new contact address or disclosure program is established here.

The local threat boundary assumes a trusted operator/filesystem and reviewed Python dependencies. Hashes detect changes relative to an independently retained identity; they do not authenticate the original source. Input bounds and symlink checks are defensive validation, not a sandbox against concurrent filesystem attacks. Agent instructions and CODEOWNERS are workflow guidance, not enforced process isolation or branch protection.

Real proof or hardware integration requires separate security review, enrolled identities, negative tests and explicit residual-risk acceptance. Policy incompleteness, distribution shift, adaptive attacks and unobserved compute remain even when execution is genuinely verified.

Specification/link checks and issue closure do not establish security. Review the
[implemented and proposed API](docs/spec/02-public-api.md) before relying on a
capability; hashes, schemas and reported acceptance fields do not replace real
verification. Changes to a trust boundary need its negative tests and exact
[requirement mapping](docs/SPEC-CHECK.md).
