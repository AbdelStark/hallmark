# Security

## Trust boundaries

The provider may choose malicious bundles, proofs, weights, inputs and timing. The relying party supplies trusted registry keys, accepted measurements/backends, required claims, request expectation and clock outside the bundle. An authenticated enrollment record is not replaceable with a manifest carried by the provider.

Claim A assumes genuine hardware evidence, correct collateral/TCB validation, protected epoch keys, a reviewed measured loader and exclusive control of the response path. Hardware physical/side-channel assumptions and accelerator linkage must be stated by the selected platform qualification. No general physical-attack resistance is asserted.

B1 claim B assumes proof-system soundness, correct circuits, enrolled keys and exact independent byte-to-input reconstruction. It does not need a trusted receipt signer to establish the classifier computation. B2 additionally trusts the hardware-attested bytes-to-input binding. Both retain classifier errors, policy gaps, adaptive evasion and unobserved traffic.

## Threat responses

| Threat | Mandatory control | Residual |
|---|---|---|
| Response/role/salt substitution | Byte-exact opening and length-delimited roles | Opened transcript is disclosed in B1 |
| Model substitution or bypass | Hash actual loaded files; bind runtime/generation and I/O path to measurement | Measured-code/hardware compromise |
| Classifier/threshold/key substitution | External enrollment, signed registry, exact manifest/public-input identity | Registry governance compromise |
| Replay/downgrade | Caller nonce/audience/interaction; expiry; monotonic registry state | A stateless historical verifier cannot prove no newer revocation exists |
| Tail/mask/token evasion | Complete input reconstruction and constrained chunk coverage | Policy blind spots across chunks |
| Overflow/field aliases | Integer range constraints and unambiguous field packing | Undetected circuit/compiler bug |
| Forged native pass | Real proof of every enrolled classifier; release/proof comparison | Pending proofs are unverified |
| CPU/accelerator evidence transplant | Same epoch-key challenge and platform/device association | Platform-specific evidence gaps block A |
| Witness/key leakage | Encrypted local spool, sealed keys, no telemetry, per-receipt key deletion | Host privilege/side-channel threats in platform model |
| Malformed bundle/resource abuse | Fixed limits, strict parsing, process budgets, no embedded URL fetch | Denial of service within approved caps |
| Training/test contamination | Source lineage, grouped splits, separate calibration, frozen test access | Unknown pretraining overlap |
| Compromised dependency | Locked reviewed distributions, no remote model code, independent verifier | Supply-chain and shared backend flaws |

**INV-NETWORK:** offline verification makes no network requests. Collateral is supplied locally and checked for validity at the caller's time. Stale collateral fails closed.

**INV-KEYS:** no signing keys, credentials or raw private data in git or bundle logs. Secrets are injected by the owner on an approved host. Do not invent a new secret service. Rotation/revocation tests are required before enrollment.

## Review and incident handling

Report security concerns only through an existing approved private owner channel. Freeze the affected artifact version, preserve evidence privately, revoke enrollment through signed history, and issue a new version after review. Do not silently repair stored runs. Explicitly record impact on historical versus current verification.

Review covers schema/parser boundaries, proof constraints, hardware path, trusted-state persistence and evidence claims. Two independent reviewer reproductions require separate sharing authority. Repository visibility and source distribution are release gates. The current private visibility does not prove absence of prior copies.

RISK: proof and hardware adapters remain unselected. Resolve at [RFC-0005 qualification](../rfcs/RFC-0005-proofs.md#open-questions) and [RFC-0006 host admission](../rfcs/RFC-0006-hardware.md#open-questions), before assigning their security properties to a result.
