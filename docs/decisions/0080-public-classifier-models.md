# 0080 — Publish the frozen trained classifiers on Hugging Face

Date: 2026-10-27. Status: owner-approved publication scope.

The owner explicitly requested publication of the trained models, model cards
and README references. Publish the preselected seed-17 MLP and contextual CNN
from the completed synthetic classifier demo in public model repositories
`abdelstark/hallmark-byte-mlp` and `abdelstark/hallmark-contextual-byte-cnn`.
This specifically authorizes those original trained artifacts; it does not
authorize private checkpoints, transcripts, credentials or unrelated uploads.

Preserve original JSON checkpoint and quantization bytes. Hash-check the exact
quantizations already enrolled by `make e2e`, regenerate native exports and
compare them to the retained proof inputs. Check full/resumed checkpoint
agreement and replay recorded CNN test scores before publication. Publish only
an enumerated artifact set with provenance, native contracts, file hashes,
training configuration, evaluation and model cards. Keep setup keys out.

Use MIT for original models, code and authored fixtures under decision 0063;
retain historical data labels/hashes with an explanatory notice. Model cards
must distinguish synthetic task evidence from real-world safety claims, float
checkpoints from integer decisions, 96-byte demo bounds from larger native MLP
limits, and native inference from cryptographic proof verification.

The release adds no training, evaluator, threshold or model change. No new
dataset, test selection, paid compute or upstream TinyLlama redistribution is
needed. Verify the public revisions through unauthenticated downloads, compare
all file hashes and execute the documented inference examples before recording
the immutable Hub revision and manifest hashes in the repository.
