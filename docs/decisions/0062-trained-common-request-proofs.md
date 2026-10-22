# 0062: Compose trained classifiers over one opened request

Status: bounded research protocol, 2026-10-22. Implements part of issue #29 under
standing owner approval; no operational policy adoption or backend qualification.

## Frozen hypothesis and baseline

Actual rule, trained MLP and contextual CNN proofs must verify over the same
caller-enrolled context and policy. One fixed benign example must pass all three;
the paired contextual example must block in the CNN and a literal `BAD; ` prefix
must block in the rule. Every cross-request proof substitution must reject.
The old eight-byte rule/MLP/pass-all encoder composition stays unchanged.

The MLP is seed 17 from decision 0058, threshold zero. The CNN is the seed 17
preselected in decision 0060, threshold -3733, proved in 0061. No training,
calibration or quality scoring occurs. Cases are the lexically first test pair
in the frozen contextual-v2 dataset plus `BAD; ` prepended to its benign member.
Reusing these prompts tests composition only; this is not new held-out evidence.

## Complete statement and enrollment

Admit zero to 96 UTF-8 bytes, rejecting excess rather than truncating. The rule
gets a new input-profile/program identity with maximum 96 and unchanged four-byte
chunks and literal matcher. Its dedicated circuit scans every byte position,
including matches across chunk boundaries. Its first native fixture failed by
retaining the old eight-byte profile; that failure is retained and the new profile
is explicitly pinned in the circuit. The MLP gets a 96-capacity command using its
unchanged native 512-byte chunks; the CNN uses its existing 96-capacity circuit.

Setup precedes classifier/policy enrollment. The controller records each actual
circuit, key, native program and model before proving. The external enrollment
hash, exact exports and circuit roster feed the opened-bundle checker. That
checker reconstructs all three input digests and public-input vectors from the
caller's opening and expectations, checks the ordered classifier roster and
all-pass decision, then produces jobs for the separately pinned py-ecc verifier.
Binding checks alone never report cryptographic acceptance.

The controller/compiler mapping and setup ceremony remain trusted research
plumbing, not authenticated compilation or operational key custody. Model weights
are public circuit constants. The authored response has no inference provenance.
The result reports `qualified_backend=false` and `hardware_claim=not-accepted`;
its `release` field means only all classifier verdicts passed. No B2, production
ZK/hiding qualification, safety conclusion or hardware claim follows.

## Pass/fail and resources

Run smallest native/circuit fixtures first, including empty input, UTF-8, the
96-byte tail, padding, chunk count, threshold equality and changed binding fields.
Then run two fresh setups: nine real proofs per campaign, three independently
checked proof sets, 18 cross-request substitutions and the separate arithmetic
mutation corpus for every classifier. Models, circuits and decision rosters must
reproduce; all six setup keys must differ. Preserve failed attempts.

Mac arm64 only: one foreground research worker, four proof threads, 7,200 seconds,
8 GiB worker RSS and 8 GiB output per campaign, retained checkout below 256 GiB.
No new cloud compute or dependency, no private material and no scheduler.
Store source/environment hashes and numeric results before a prose conclusion.
