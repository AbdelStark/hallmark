# Paper: Proofs, Attestation and Logs

*What a Verifier Must Trust to Know a Safety Classifier Ran.* Abdelhamid Bakhta,
Lucid Computing. A systematization of evidence that a safety classifier ran,
with Hallmark as a worked illustration. Preprint draft, not peer reviewed.

| File | What it is |
|---|---|
| [proofs-attestation-logs.pdf](proofs-attestation-logs.pdf) | The paper, 38 pages |
| [proofs-attestation-logs.md](proofs-attestation-logs.md) | Markdown edition, the text the LaTeX is generated from |
| [main.tex](main.tex) | LaTeX source (pdflatex-compatible, numeric citations) |
| [trust-boundary.png](trust-boundary.png) | Figure 2, rendered from `docs/assets/figures/trust-boundary.svg` |
| [md2tex.py](md2tex.py), [figure1.tex](figure1.tex), [figure2.tex](figure2.tex) | Generator for `main.tex` and its two figure templates |

`main.tex` is generated: edit the Markdown, then run `python3 md2tex.py` here,
which writes `main.tex` from it and the two figure files `figure1.tex`
(TikZ) and `figure2.tex`. Build the PDF from this folder with
`tectonic main.tex` or `pdflatex main.tex` (run twice).

The paper's experiments read the frozen records under `research/evidence/`;
its Data and Artifact Availability section maps each one. The records of its
final simulated review are in
[`research/paper-review/2026-11-02/`](../../research/paper-review/2026-11-02/README.md).
The code, research record and manuscript were produced with AI assistance; the paper's AI-Use
Disclosure says how.
