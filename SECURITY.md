# Security and research limits

This is pre-production research in a public repository, not a security product or safety certification. The [classifier demo](docs/DEMO.md) generates real dedicated-circuit proofs and checks them with a separate arithmetic verifier. It has no accepted hardware evidence, operational hybrid integration or independent security qualification. Do not use baseline replay as a proof, or synthetic classifiers to make safety decisions.

Report concerns privately to the repository owner through an existing approved private channel. Do not open a public issue or upload transcripts, model weights, secrets or exploit evidence to an external service. No new contact address or disclosure program is established here.

The local threat boundary assumes a trusted operator/filesystem and reviewed Python dependencies. Hashes detect changes relative to an independently retained identity; they do not authenticate the original source. Input bounds and symlink checks are defensive validation, not a sandbox against concurrent filesystem attacks. Agent instructions and CODEOWNERS are workflow guidance, not enforced process isolation or branch protection.

Operational proof or hardware acceptance requires separate security review, authenticated enrollment, setup/key custody, negative tests and explicit residual-risk acceptance. The demo trusts its local controller to map the native program to the compiled circuit and fresh setup key. Its verifier sees the opened input and the model constants are public; no hiding qualification is claimed. Policy incompleteness, distribution shift, adaptive attacks and unobserved compute remain even when execution is genuinely verified.

Specification/link checks and issue closure do not establish security. Review the
[implemented and proposed API](docs/spec/02-public-api.md) before relying on a
capability; hashes, schemas and reported acceptance fields do not replace real
verification. Changes to a trust boundary need its negative tests and exact
[requirement mapping](docs/SPEC-CHECK.md).
