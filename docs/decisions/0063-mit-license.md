# 0063 — Adopt MIT for original project material

Date: 2026-10-22. Status: owner-approved licence decision.

The owner explicitly requested “Adopt MIT” while reviewing the public README and
demo documentation. Replace the repository's no-open-source-licence notice with
the standard MIT licence and declare `MIT` in Python package metadata. Keep the
repository public.

The grant covers original project code, documentation and authored fixtures.
Third-party code, referenced datasets and model weights retain their own terms.
This decision does not authorize a package upload or publication of private
transcripts, checkpoints or credentials.

Frozen datasets, admission records, protocols, prior decisions and evidence retain
their original licence labels and exact bytes. Those labels record the historical
state; they do not undo the owner's new grant for original project material.
Changing them in place would break prior artifact identities and reproducibility.
No dataset, evaluator, threshold, arithmetic, circuit or model identity changes.

Current-facing README, contribution, dependency and release documentation must
agree with the new licence. Verify the wheel's `License-Expression: MIT` and
bundled licence text, the sdist licence, unchanged dependency lock and ordinary
package/spec gates. Package publication and operational qualification remain
separate actions.
