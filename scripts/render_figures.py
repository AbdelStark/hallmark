"""Render the documentation figures from frozen evidence; stdlib only, no network.

Every number drawn in a chart is read from `research/evidence/`. Diagrams use the
fixed case definitions. `--check` fails when a committed figure is stale.
"""

import argparse
import json
import statistics
import sys
from collections.abc import Callable, Iterable, Sequence
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets/figures"
EVIDENCE = ROOT / "research/evidence"

SANS = 'ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif'
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# Chart slots s1-s4 pass the dataviz validator (lightness band, chroma floor, CVD
# separation, normal-vision floor) against each surface; cpu is a de-emphasis gray.
LIGHT = dict(
    bg="#f7f4ec",
    panel="#fffdf8",
    ink="#203c35",
    text="#2b3d36",
    muted="#5b6860",
    faint="#8d988f",
    line="#d4d9cc",
    grid="#e4e6dc",
    soft="#ebede2",
    soft2="#dde3d4",
    layer="#c9d8cb",
    accent="#b5532f",
    accent_soft="#f4e0d6",
    proved="#2e6b52",
    proved_soft="#e2ece3",
    caller="#94680f",
    caller_soft="#f5ebcf",
    out="#8d988f",
    out_soft="#efeee7",
    s1="#3a6fb0",
    s2="#c8602f",
    s3="#249c70",
    s4="#d9a01c",
    cpu="#a3aba4",
)
DARK = dict(
    bg="#172822",
    panel="#1c3029",
    ink="#e6ebdc",
    text="#d9e2d4",
    muted="#a7b6a9",
    faint="#7d8c80",
    line="#3a4d41",
    grid="#26392f",
    soft="#22372d",
    soft2="#2b4337",
    layer="#33503f",
    accent="#f0b398",
    accent_soft="#4a2e24",
    proved="#86c9a6",
    proved_soft="#1f3d2e",
    caller="#e2b85c",
    caller_soft="#3a3320",
    out="#7d8c80",
    out_soft="#203029",
    s1="#4f86c9",
    s2="#d26a3a",
    s3="#2aa577",
    s4="#b98c18",
    cpu="#66756a",
)
ON_FILL = {"s1": "#ffffff", "s2": "#ffffff", "s3": "#ffffff", "s4": "#1d1a10"}


def num(value: float, digits: int = 2) -> str:
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def width(text: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Conservative advance-width estimate; layouts leave slack for font variation."""
    return len(text) * size * (0.61 if mono else 0.58 if bold else 0.54)


def fx(value: float, digits: int = 2) -> str:
    """Display value with fixed decimals, so 3.40 never prints as 3.4."""
    return f"{value:,.{digits}f}"


def seconds(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f} s"


class Fig:
    def __init__(self, w: int, h: int, title: str, desc: str) -> None:
        self.w, self.h, self.title, self.desc = w, h, title, desc
        self.items: list[str] = []

    def add(self, markup: str) -> None:
        self.items.append(markup)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        cls: str,
        rx: float = 0,
        sw: float = 1,
        dash: bool = False,
    ) -> None:
        extra = f' rx="{num(rx)}"' if rx else ""
        if " k-" in f" {cls}":
            extra += f' stroke-width="{num(sw)}"'
        if dash:
            extra += ' stroke-dasharray="5 4"'
        self.add(
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"'
            f' class="{cls}"{extra}/>'
        )

    def text(
        self,
        x: float,
        y: float,
        content: str | Sequence[str],
        cls: str = "b",
        anchor: str = "start",
        leading: float = 17,
        rotate: float | None = None,
        fill: str | None = None,
    ) -> None:
        lines = [content] if isinstance(content, str) else list(content)
        attrs = f'x="{num(x)}" y="{num(y)}" class="{cls}"'
        if fill:
            attrs += f' style="fill:var(--{fill})"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if rotate is not None:
            attrs += f' transform="rotate({num(rotate)} {num(x)} {num(y)})"'
        if len(lines) == 1:
            self.add(f"<text {attrs}>{escape(lines[0])}</text>")
            return
        spans = "".join(
            f'<tspan x="{num(x)}" dy="{0 if i == 0 else num(leading)}">{escape(line)}</tspan>'
            for i, line in enumerate(lines)
        )
        self.add(f"<text {attrs}>{spans}</text>")

    def spans(
        self,
        x: float,
        y: float,
        parts: Iterable[str | tuple[str, str]],
        cls: str = "b",
        anchor: str = "start",
    ) -> None:
        inner = "".join(
            escape(p) if isinstance(p, str) else f'<tspan class="{p[1]}">{escape(p[0])}</tspan>'
            for p in parts
        )
        attr = f' text-anchor="{anchor}"' if anchor != "start" else ""
        self.add(f'<text x="{num(x)}" y="{num(y)}" class="{cls}"{attr}>{inner}</text>')

    def path(
        self,
        d: str,
        cls: str = "k-faint",
        sw: float = 1.5,
        arrow: str | None = None,
        dash: bool = False,
        fill: bool = False,
    ) -> None:
        extra = "" if fill else ' fill="none"'
        extra += f' stroke-width="{num(sw)}"' if " k-" in f" {cls}" else ""
        if arrow:
            extra += f' marker-end="url(#{arrow})"'
        if dash:
            extra += ' stroke-dasharray="4 4"'
        self.add(f'<path d="{d}" class="{cls}"{extra} stroke-linecap="round"/>')

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        cls: str = "k-line",
        sw: float = 1,
        arrow: str | None = None,
        dash: bool = False,
    ) -> None:
        self.path(f"M{num(x1)} {num(y1)}L{num(x2)} {num(y2)}", cls, sw, arrow, dash)

    def circle(self, cx: float, cy: float, r: float, cls: str, ring: bool = False) -> None:
        extra = ' stroke-width="2" class="' + cls + ' k-bg"' if ring else f' class="{cls}"'
        self.add(f'<circle cx="{num(cx)}" cy="{num(cy)}" r="{num(r)}"{extra}/>')

    def svg(self) -> str:
        def variables(palette: dict[str, str]) -> str:
            return ";".join(f"--{k.replace('_', '-')}:{v}" for k, v in palette.items())

        classes = "".join(
            f".f-{k}{{fill:var(--{k.replace('_', '-')})}}"
            f".k-{k}{{stroke:var(--{k.replace('_', '-')})}}"
            for k in LIGHT
        )
        style = (
            f"svg{{{variables(LIGHT)}}}"
            f"@media (prefers-color-scheme:dark){{svg{{{variables(DARK)}}}}}"
            f"text{{font-family:{SANS};fill:var(--text);font-size:14px}}"
            ".e{font-size:11px;font-weight:700;letter-spacing:.13em;fill:var(--muted)}"
            ".h{font-size:20px;font-weight:600;fill:var(--ink);letter-spacing:-.01em}"
            ".b{font-size:14px}.bs{font-size:13px}.s{font-size:12px;fill:var(--muted)}"
            ".bb{font-size:14px;font-weight:650;fill:var(--ink)}"
            ".hb{font-size:16px;font-weight:650;fill:var(--ink)}"
            f".m{{font-family:{MONO};font-size:12.5px}}"
            f".mb{{font-family:{MONO};font-size:13px;font-weight:700;fill:var(--ink)}}"
            f".mbig{{font-family:{MONO};font-size:18px;font-weight:600;fill:var(--ink)}}"
            ".big{font-size:24px;font-weight:600;fill:var(--ink)}"
            ".acc{fill:var(--accent)}.ink{fill:var(--ink)}.mut{fill:var(--muted)}"
            ".prv{fill:var(--proved)}.cal{fill:var(--caller)}.w{font-weight:650}"
            ".onw{fill:#ffffff}.ond{fill:#1d1a10}"
            f"{classes}"
        )
        defs = (
            '<marker id="a" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7"'
            ' markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"'
            ' class="f-faint"/></marker>'
            '<marker id="ai" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="7"'
            ' markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z"'
            ' class="f-ink"/></marker>'
        )
        body = "\n".join(self.items)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}"'
            f' width="{self.w}" height="{self.h}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{escape(self.title)}</title>\n<desc id="d">{escape(self.desc)}</desc>\n'
            f"<style>{style}</style>\n<defs>{defs}</defs>\n"
            f'<rect width="{self.w}" height="{self.h}" rx="10" class="f-bg"/>\n'
            f"{body}\n</svg>\n"
        )


def load(name: str) -> Any:
    return json.loads((EVIDENCE / name).read_text())


def header(f: Fig, eyebrow: str, title: str) -> None:
    f.text(40, 44, eyebrow.upper(), "e")
    f.text(40, 72, title, "h")


def note(f: Fig, y: float, text: str, x: float = 40, limit: float = 880) -> float:
    """Wrapped 12 px footnote; returns the baseline after the last line."""
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and width(trial, 12) > limit:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    f.text(x, y, lines, "s", leading=16)
    return y + 16 * len(lines)


def box(
    f: Fig,
    x: float,
    y: float,
    w: float,
    h: float,
    lines: Sequence[str],
    cls: str = "f-panel k-line",
    text_cls: str = "bs",
    first_cls: str = "bb",
) -> None:
    f.rect(x, y, w, h, cls, rx=6)
    top = y + h / 2 - (len(lines) - 1) * 8.5 + 5
    for i, line in enumerate(lines):
        f.text(x + w / 2, top + i * 17, line, first_cls if i == 0 else text_cls, "middle")


def check(f: Fig, x: float, y: float, cls: str = "k-proved") -> None:
    f.path(f"M{num(x)} {num(y)}l3.5 3.5l6.5-7", cls, sw=2)


def cross(f: Fig, x: float, y: float) -> None:
    f.path(f"M{num(x)} {num(y - 4)}l7 7M{num(x + 7)} {num(y - 4)}l-7 7", "k-out", sw=1.8)


def diamond(f: Fig, x: float, y: float) -> None:
    f.path(f"M{num(x + 4)} {num(y - 5)}l4 4.5l-4 4.5l-4-4.5z", "f-caller k-caller", sw=1, fill=True)


def hbar(f: Fig, x: float, y: float, w: float, h: float, cls: str, r: float = 4) -> None:
    """Horizontal bar: square at the baseline, rounded data end."""
    r = max(0.0, min(r, w / 2, h / 2))
    f.add(
        f'<path d="M{num(x)} {num(y)}H{num(x + w - r)}A{num(r)} {num(r)} 0 0 1 {num(x + w)}'
        f" {num(y + r)}V{num(y + h - r)}A{num(r)} {num(r)} 0 0 1 {num(x + w - r)} {num(y + h)}"
        f'H{num(x)}Z" class="{cls}"/>'
    )


def legend(
    f: Fig, x: float, y: float, entries: Sequence[tuple[str, str]], dot: bool = False
) -> float:
    for cls, label in entries:
        if dot:
            f.circle(x + 5, y - 4.5, 5, cls)
        else:
            f.rect(x, y - 10, 12, 12, cls, rx=2)
        f.text(x + 18, y, label, "bs")
        x += 18 + width(label, 13) + 22
    return x


# --- Diagrams ---------------------------------------------------------------------------


def overview() -> Fig:
    f = Fig(
        960,
        452,
        "How Hallmark works",
        "The caller pins the model, programs and request. SASH proves the TinyLlama "
        "response as 23 linked Circle STARK segments; STWO proves the rule, MLP and CNN "
        "verdicts. The verifier checks every proof against the caller's expectations and "
        "checks that both refer to the same request.",
    )
    header(
        f,
        "Hallmark · one request, two proved computations",
        "Pin the expectation first. Prove. Then check everything against one request.",
    )
    f.text(40, 116, "1 · CALLER", "e")
    f.text(280, 116, "2 · PROVERS", "e")
    f.text(730, 116, "3 · VERIFIER", "e")

    f.rect(40, 128, 200, 272, "f-caller_soft k-caller", rx=8)
    items = [
        ("Model, shape and", "calibration roots"),
        ("Classifier programs and", "preprocessing roots"),
        ("Prompt, response", "and token IDs"),
        ("Concrete proof", "parameters"),
    ]
    for i, (a, b) in enumerate(items):
        y = 162 + i * 52
        diamond(f, 54, y - 4)
        f.text(72, y, [a, b], "bs", leading=16)
    f.text(56, 382, "Pinned before any proof exists", "s")

    f.rect(280, 128, 410, 128, "f-panel k-line", rx=8)
    f.text(296, 152, "TINYLLAMA-1.1B · SASH CIRCLE STARK", "e")
    box(f, 296, 166, 112, 46, ["25 prompt", "tokens"], "f-soft k-line")
    box(f, 430, 166, 120, 46, ["22 layers", "+ norm + head"], "f-layer k-line")
    box(f, 572, 166, 104, 46, ["8 tokens", "through EOS"], "f-accent_soft k-line")
    f.line(408, 189, 428, 189, "k-faint", 1.5, "a")
    f.line(550, 189, 570, 189, "k-faint", 1.5, "a")
    f.text(296, 238, "23 linked segment proofs · 737.86 MB of proof JSON", "s")

    f.rect(280, 272, 410, 128, "f-panel k-line", rx=8)
    f.text(296, 296, "RULE · MLP · CNN · STWO CIRCLE STARK", "e")
    box(f, 296, 310, 112, 46, ["Prompt bytes", "≤ 96, UTF-8"], "f-soft k-line")
    box(f, 430, 310, 120, 46, ["SHA-256 +", "integer model"], "f-layer k-line")
    box(f, 572, 310, 104, 46, ["Verdict", "pass or block"], "f-accent_soft k-line")
    f.line(408, 333, 428, 333, "k-faint", 1.5, "a")
    f.line(550, 333, 570, 333, "k-faint", 1.5, "a")
    f.text(296, 382, "One proof per classifier per request · about 2 MB each", "s")

    f.rect(730, 128, 190, 272, "f-proved_soft k-proved", rx=8)
    checks = [
        ("Every proof against", "the enrolled roots"),
        ("Residual, token and", "roster links"),
        ("Both proofs name", "the same request"),
    ]
    for i, (a, b) in enumerate(checks):
        y = 162 + i * 52
        check(f, 746, y - 6)
        f.text(764, y, [a, b], "bs", leading=16)
    f.rect(744, 328, 162, 56, "f-ink", rx=6)
    f.text(825, 351, "Verified response", "bb", "middle", fill="bg")
    f.text(825, 369, "+ three verdicts", "bs", "middle", fill="bg")

    for y in (192, 336):
        f.line(242, y, 277, y, "k-faint", 1.5, "a")
        f.line(692, y, 727, y, "k-faint", 1.5, "a")
    f.path("M140 402V424H825V402", "k-caller", 1.5, "a", dash=True)
    f.rect(372, 414, 220, 20, "f-bg")
    f.text(482, 428, "the same expectations, unchanged", "s", "middle")
    return f


def _columns() -> list[tuple[float, float]]:
    """x and width of the 32 token positions: 24 narrow prompt cells, 8 wide answer cells."""
    out, x = [], 168.0
    for i in range(32):
        w = 10.0 if i < 24 else 54.0
        out.append((x, w))
        x += w + 2
    return out


def llm_statement() -> Fig:
    case = json.loads((ROOT / "research/probes/sash/response-case.json").read_text())
    prompt, answer = case["prompt_ids"], case["answer_ids"]
    assert len(prompt) == 25 and len(answer) == 8 and answer[-1] == 2
    words = ["The", "capital", "of", "France", "is", "Paris", ".", "</s>"]
    f = Fig(
        960,
        680,
        "What the TinyLlama proof covers",
        "One 32-position block holds the 25 prompt tokens and the first seven answer tokens. "
        "Twenty-two layer segments and one final-norm/output-head segment are proved, joined "
        "by 22 residual links. The head's argmax at positions 24 to 31 yields the eight answer "
        "tokens through EOS; seven of them must equal the next input token.",
    )
    header(
        f,
        "What the TinyLlama proof covers",
        "Eight answer tokens, 23 segment proofs, every link checked",
    )
    cols = _columns()
    y_in, y_s, pitch, y_out = 150, 214, 12, 528
    left, right = cols[0][0], cols[-1][0] + cols[-1][1]

    def bracket(a: int, b: int, y: float, label: str) -> None:
        x1, x2 = cols[a][0], cols[b][0] + cols[b][1]
        f.path(f"M{num(x1)} {num(y + 6)}V{num(y)}H{num(x2)}V{num(y + 6)}", "k-faint", 1)
        f.text((x1 + x2) / 2, y - 7, label, "s", "middle")

    bracket(0, 24, 128, "prompt · 25 tokens after the chat template")
    bracket(25, 31, 128, "answer tokens fed back · 7")
    for i, (x, w) in enumerate(cols):
        cls = "f-accent_soft k-accent" if i >= 25 else "f-soft k-line"
        f.rect(x, y_in, w, 34, cls, rx=3)
        if i == 24:
            f.text(x + w / 2, y_in + 22, "\\n", "m", "middle")
        elif i >= 25:
            f.text(x + w / 2, y_in + 22, words[i - 25], "bs", "middle")
    f.text(left - 14, y_in + 22, "input", "s", "end")

    mid = (cols[24][0] + right) / 2
    f.line(mid, y_in + 38, mid, y_s - 6, "k-faint", 1.5, "a")
    labels = {0: "layer 0", 21: "layer 21", 22: "norm + head"}
    for r in range(23):
        y = y_s + r * pitch
        head = r == 22
        f.rect(left, y, right - left, 8, "f-accent" if head else "f-layer", rx=2)
        if r in labels:
            f.text(left - 22, y + 8, labels[r], "s acc w" if head else "s", "end")
        if r < 22:
            f.circle(left - 10, y + 10, 2.4, "f-ink")
    f.text(left - 22, y_s + 11 * pitch + 8, "⋮", "s", "end")
    f.text(58, y_s + 138, "23 segment proofs", "e", "middle", rotate=-90)
    f.path(f"M70 {y_s}H74V{y_s + 22 * pitch + 8}H70", "k-faint", 1)
    stack_end = y_s + 22 * pitch + 8
    f.line(mid, stack_end + 6, mid, y_out - 6, "k-faint", 1.5, "a")
    f.text(cols[23][0] + 10, stack_end + 32, "argmax at positions 24–31", "s", "end")

    for i in range(24, 32):
        x, w = cols[i]
        eos = i == 31
        f.rect(x, y_out, w, 34, "f-accent" if eos else "f-proved_soft k-proved", rx=3)
        word = words[i - 24]
        f.text(
            x + w / 2,
            y_out + 22,
            word,
            "bs w" if eos else "bs",
            "middle",
            fill="bg" if eos else None,
        )
    f.text(left - 14, y_out + 22, "output", "s", "end")
    fed = cols[30][0] + cols[30][1]
    f.path(f"M{num(cols[24][0])} {y_out + 40}V{y_out + 46}H{num(fed)}V{y_out + 40}", "k-accent", 1)
    loop = right + 26
    f.path(
        f"M{num((cols[24][0] + fed) / 2)} {y_out + 46}V{y_out + 58}H{num(loop)}"
        f"V{y_in + 17}H{num(right + 6)}",
        "k-accent",
        1.6,
        "a",
    )
    f.text(loop + 16, (y_in + y_out) / 2 + 17, "7 generated-input links", "s", "middle", rotate=-90)
    f.text(cols[31][0] + cols[31][1] / 2, y_out + 52, "EOS", "s", "middle")

    y = 618
    f.rect(40, y - 10, 12, 12, "f-layer", rx=2)
    f.text(58, y, "proved layer segment (embedding bound in the first)", "bs")
    f.rect(404, y - 10, 12, 12, "f-accent", rx=2)
    f.text(422, y, "proved final norm + output head", "bs")
    f.circle(651, y - 4, 2.6, "f-ink")
    f.text(660, y, "residual link (22)", "bs")
    note(
        f,
        y + 24,
        "Each output equals the next input, one position to the right. The caller checks the "
        "tokenizer and chat template, the exact token IDs, and that the last output is EOS (ID 2).",
    )
    return f


def llm_pipeline() -> Fig:
    rep = load("llm-e2e-reproduction-2026-10-23.json")
    jobs, ver = rep["jobs"], rep["verification"]["cases"]
    honest = [c["seconds"] for c in ver if c["name"].startswith("honest")]
    cases = load("circle-reference-2026-10-28.json")["metrics"]["native_gpu_cases"]
    checks = sorted(c["seconds"] for c in cases if c["name"].startswith("honest"))
    total = rep["command_process"]["seconds"]
    f = Fig(
        960,
        462,
        "The TinyLlama workflow, stage by stage",
        "Local preparation on a Mac, then three sequential Hugging Face CPU jobs build the "
        "prover, prove 23 segments and verify them in fresh processes; an optional native "
        "verifier rechecks the bundle on the Mac.",
    )
    header(
        f,
        "make e2e-llm · stage by stage",
        "Prepare locally, build, prove and verify in three cloud jobs",
    )
    cards = [
        (
            "YOUR MAC",
            "Prepare",
            [
                "Fetch the pinned",
                "2.2 GB checkpoint",
                "Quantize, decode,",
                "extract witnesses",
            ],
            fx(rep["native"]["seconds"]) + " s",
            "preparation only",
        ),
        (
            "HF CPU · 8 vCPU",
            "Build",
            [
                "Pinned SASH prover,",
                "unchanged source",
                "6 upstream tests",
                "Binary feeds 2 and 3",
            ],
            fx(jobs["build"]["running_seconds"]) + " s",
            "job running time",
        ),
        (
            "HF CPU · 32 vCPU",
            "Prove",
            [
                "Derive model roots,",
                "match enrollment",
                "Prove 23 segments",
                "and serialize",
            ],
            fx(jobs["prove"]["running_seconds"]) + " s",
            f"{fx(rep['proving']['summed_prove_seconds'])} s proving inside",
        ),
        (
            "HF CPU · 8 vCPU",
            "Verify",
            ["Two fresh verifier", "processes, whole", "bundle; reject 14", "changed claims"],
            " / ".join(fx(s, 1) for s in honest) + " s",
            "per honest check",
        ),
        (
            "MAC · OPTIONAL",
            "Verify natively",
            ["Roots compiled in", "2 honest checks", "36 rejections"],
            " / ".join(fx(s, 2) for s in checks) + " s",
            "per check, L1 postflight",
        ),
    ]
    for i, (where, title, lines, dur, sub) in enumerate(cards):
        x = 40 + i * 180
        mac = "MAC" in where
        f.rect(x, 104, 160, 218, "f-caller_soft k-caller" if mac else "f-panel k-line", rx=8)
        f.text(x + 14, 126, where, "e")
        f.text(x + 14, 154, title, "hb")
        f.text(x + 14, 178, lines, "bs", leading=17)
        f.line(x + 14, 258, x + 146, 258, "k-line")
        f.text(x + 14, 284, dur, "mbig")
        f.text(x + 14, 304, sub, "s")
        if i < 4:
            f.line(x + 162, 213, x + 177, 213, "k-faint", 1.5, "a")
    f.path("M120 324V344H480V326", "k-faint", 1.2, "a")
    f.text(300, 360, "witnesses + public case", "s", "middle")
    f.path("M480 324V380H660V326M660 380H840V326", "k-proved", 1.2, "a")
    f.text(660, 396, "proofs + statements + claims only — no weights, no witness", "s", "middle")
    minutes, secs = divmod(round(total), 60)
    cost = rep["cost"]["actual_compute_bound_micro_usd"] / 1e6
    note(
        f,
        424,
        f"Stages 1–4: the fresh one-command reproduction of 2026-10-23, {minutes} min {secs} s "
        f"end to end, compute bound ${cost:.2f} (not an invoice). All 69 proof, statement and "
        "claim files are byte-identical to the accepted bundle. Stage 5 timings are from the L1 "
        "postflight.",
    )
    return f


def classifier_statement() -> Fig:
    f = Fig(
        960,
        488,
        "What one classifier proof states",
        "The witness holds the prompt bytes, salt and intermediate values. The circuit "
        "constrains complete input coverage, a salted SHA-256 commitment, the exact integer "
        "classifier and the threshold decision. The public statement has 100 fields: context, "
        "classifier and input digests of 32 bytes each, plus counts, threshold and verdict.",
    )
    header(
        f,
        "What one classifier proof states",
        "Exact integer inference on the complete prompt, bound to a commitment",
    )
    f.rect(40, 108, 196, 316, "f-out_soft k-out", rx=8, dash=True)
    f.text(56, 132, "WITNESS", "e")
    f.text(56, 156, ["Prompt bytes x", "(0–96 UTF-8 bytes)"], "bs", leading=17)
    f.text(56, 206, "Opening salt", "bs")
    f.text(56, 236, "Padding and masks", "bs")
    f.text(56, 266, ["Every intermediate", "value"], "bs", leading=17)
    f.text(
        56,
        352,
        ["Not in the public", "statement. Not hidden", "either: no ZK claim."],
        "s",
        leading=16,
    )

    f.text(268, 132, "CONSTRAINED BY THE CIRCUIT", "e")
    steps = [
        ("Complete input", ["96 byte slots, exact length, zero padding.", "Nothing is truncated."]),
        (
            "Commitment",
            ["SHA-256 over salt + canonical CBOR(x)", "equals the public input digest."],
        ),
        (
            "Classifier",
            [
                "rule: no “BAD” at any offset · MLP: byte",
                "counts → 4 ReLU · CNN: conv → masked max",
            ],
        ),
        ("Decision", ["verdict = 1 if score < threshold, else 0.", "Equality blocks."]),
    ]
    for i, (title, lines) in enumerate(steps):
        y = 146 + i * 70
        f.rect(268, y, 372, 62, "f-panel k-line", rx=6)
        f.circle(290, y + 20, 11, "f-ink")
        f.text(290, y + 25, str(i + 1), "bs w", "middle", fill="bg")
        f.text(310, y + 25, title, "bb")
        f.text(310, y + 44, lines[0], "s")
        f.text(310, y + 58, lines[1], "s")
    f.line(238, 266, 264, 266, "k-faint", 1.5, "a")
    f.line(642, 266, 668, 266, "k-faint", 1.5, "a")

    f.text(680, 132, "PUBLIC STATEMENT · 100 FIELDS", "e")
    kinds = ["s1"] * 32 + ["s2"] * 32 + ["s3"] * 32 + ["s4"] * 4
    for i, k in enumerate(kinds):
        f.rect(680 + (i % 10) * 22, 146 + (i // 10) * 22, 19, 19, f"f-{k}", rx=3)
    rows = [
        ("s1", "context digest · caller rebuilds"),
        ("s2", "classifier identity · caller rebuilds"),
        ("s3", "input digest · recomputed in circuit"),
        ("s4", "counts, threshold, verdict"),
    ]
    for i, (k, label) in enumerate(rows):
        y = 382 + i * 19
        f.rect(680, y - 10, 11, 11, f"f-{k}", rx=2)
        f.text(697, y, label, "s")
    note(
        f,
        452,
        "Weights are constants compiled into the circuit and pinned at enrollment; training is not "
        "proved. The score is not public. Circle carries the 100 fields as 103 M31 values.",
    )
    return f


def classifier_pipeline() -> Fig:
    c = load("circle-reference-2026-10-28.json")["metrics"]
    cl, events = c["classifiers"], {e["stage"]: e["seconds"] for e in c["timing"]["events"]}
    f = Fig(
        960,
        452,
        "The classifier workflow",
        "Train and export the MLP and CNN, compile gates and build the prover and verifier, "
        "enroll the programs before proving; then for each of nine request/classifier pairs "
        "build the witness, prove with STWO, verify in a fresh process and bind the result.",
    )
    header(
        f,
        "make e2e · the classifier workflow",
        "Train once, enroll before proving, then prove and check nine decisions",
    )
    f.text(40, 110, "ONCE PER RUN", "e")
    a = [
        (
            "Train",
            [
                f"MLP {fx(events['mlp-training'])} s",
                f"CNN {fx(events['cnn-training'])} s",
                "synthetic data, seed 17",
            ],
        ),
        ("Export", ["exact integer graphs", "weights become", "circuit constants"]),
        (
            "Compile and build",
            [
                "SHA-256 + integer gates",
                f"prover {fx(events['circle-prove-build'])} s",
                f"verifier {fx(events['circle-verify-build'])} s",
            ],
        ),
        (
            "Enroll",
            [
                "program hash and",
                "preprocessing root",
                f"3 programs · {fx(cl['enroll_commands_seconds'])} s",
            ],
        ),
    ]
    b = [
        (
            "Witness",
            [
                "complete trace and",
                "native parity check",
                f"{fx(cl['witness_seconds'])} s for nine",
            ],
        ),
        (
            "Prove · STWO",
            [
                "commit, LogUp, FRI",
                f"{fx(cl['prover_commands_seconds'])} s for nine",
                f"{fx(cl['engine_stages_seconds']['stark_proving'])} s final proving",
            ],
        ),
        (
            "Verify · fresh process",
            [
                "proof + enrollment +",
                "public inputs only",
                f"{fx(cl['verify_commands_seconds'], 3)} s for nine",
            ],
        ),
        ("Bind and decide", ["rebuild public inputs", "exact roster", "all-pass → release"]),
    ]
    for row, (cards, y) in enumerate(((a, 122), (b, 268))):
        for i, (title, lines) in enumerate(cards):
            x = 40 + i * 226
            caller = (row, i) in {(0, 3), (1, 3)}
            f.rect(x, y, 200, 100, "f-caller_soft k-caller" if caller else "f-panel k-line", rx=8)
            f.text(x + 14, y + 26, title, "bb")
            f.text(x + 14, y + 50, lines, "s", leading=16)
            if i < 3:
                f.line(x + 202, y + 50, x + 223, y + 50, "k-faint", 1.5, "a")
    f.path("M818 224V240H140V264", "k-faint", 1.5, "a")
    f.text(160, 258, "PER PROOF · 3 REQUESTS × 3 CLASSIFIERS", "e")
    f.rect(40, 384, 880, 34, "f-proved_soft k-proved", rx=6)
    check(f, 56, 400)
    f.spans(
        76,
        406,
        [
            ("Must reject, and did: ", "bb"),
            f"{cl['direct_public_rejections']} changed public inputs · "
            f"{cl['cross_request_rejections']} cross-request swaps · "
            f"{cl['roster_rejections']} invalid rosters",
        ],
        "bs",
    )
    f.text(
        40,
        440,
        "Timings: C1, one fresh run on an Apple M4 Max with four prover threads, 2026-10-28. "
        f"Nine proof files total {cl['proof_bytes'] / 1e6:.2f} MB. Amber cards are caller steps.",
        "s",
    )
    return f


def verdict_matrix() -> Fig:
    cases = [
        ("allow", "benign synthetic prompt", [1, 1, 1]),
        ("cnn-block", "contextual case", [1, 1, 0]),
        ("rule-block", "prompt starts with “BAD;”", [0, 1, 1]),
    ]
    f = Fig(
        960,
        356,
        "Nine proofs, nine verdicts",
        "Three requests times three classifiers. All nine proofs verify. The allow request "
        "passes all three classifiers; the CNN blocks the contextual case; the rule blocks the "
        "BAD-prefixed case. A blocking verdict is a proved outcome, not a failed proof.",
    )
    header(f, "make e2e · nine proofs, nine verdicts", "A valid proof can say “block”")
    for j, name in enumerate(("Rule", "MLP", "CNN")):
        f.text(300 + j * 160, 118, name, "bb", "middle")
    f.text(820, 118, "All-pass policy", "bb", "middle")
    for i, (case, note, verdicts) in enumerate(cases):
        y = 132 + i * 64
        f.text(40, y + 26, case, "mb")
        f.text(40, y + 44, note, "s")
        for j, v in enumerate(verdicts):
            x = 228 + j * 160
            f.rect(x, y, 144, 54, "f-proved_soft k-proved" if v else "f-accent_soft k-accent", rx=6)
            f.text(x + 72, y + 25, "pass" if v else "block", "hb" if v else "hb acc", "middle")
            check(f, x + 36, y + 38, "k-proved")
            f.text(x + 52, y + 43, "proof verified", "s")
        release = all(verdicts)
        f.rect(748, y, 144, 54, "f-ink" if release else "f-panel k-line", rx=6)
        ink = "bg" if release else None
        f.text(820, y + 25, "release", "bs", "middle", fill=ink)
        f.text(820, y + 43, "true" if release else "false", "mb", "middle", fill=ink)
    f.text(
        40,
        336,
        "The frozen MLP allows every admitted input: its integer score stays in [−5600, −2338], "
        "below threshold 0. The rule and CNN provide the blocks.",
        "s",
    )
    return f


def trust_boundary() -> Fig:
    f = Fig(
        960,
        474,
        "Where the proof ends",
        "Three columns. Proved by the STARK: the quantized TinyLlama computation and links, and "
        "each classifier's input coverage, commitment, arithmetic and verdict. Checked by the "
        "caller: enrollment, tokenization, request binding, rosters and the all-pass policy. "
        "Not claimed: float equivalence, hiding, hardware provenance, input authenticity, "
        "training history, policy quality, independent review and arbitrary models.",
    )
    header(f, "Where the proof ends", "What is proved, what the caller checks, what is not claimed")
    cols: list[tuple[str, str, str, list[str]]] = [
        (
            "PROVED BY THE STARK",
            "f-proved_soft k-proved",
            "check",
            [
                "#TinyLlama, quantized",
                "Embedding, 22 layers, final norm",
                "Output argmax at positions 24–31",
                "22 residual links between segments",
                "7 outputs equal the next inputs",
                "#Each classifier",
                "Every byte of the ≤ 96-byte prompt",
                "Salted SHA-256 input commitment",
                "Every integer operation",
                "Verdict from the threshold",
            ],
        ),
        (
            "CHECKED BY THE CALLER",
            "f-caller_soft k-caller",
            "diamond",
            [
                "Enroll roots, programs and",
                "  parameters before proving",
                "Tokenizer and chat template",
                "Last output token is EOS",
                "Rebuild context, salts, classifier IDs",
                "Exactly one proof per classifier",
                "Both proofs name one request",
                "Combine verdicts with all-pass",
            ],
        ),
        (
            "NOT CLAIMED",
            "f-out_soft k-out",
            "cross",
            [
                "Equality with the float model",
                "Witness hiding (no ZK claim)",
                "Hardware provenance",
                "Authentic input capture",
                "Training history",
                "Policy or classifier quality",
                "Independent security review",
                "Arbitrary prompts or models",
            ],
        ),
    ]
    for i, (title, cls, mark, lines) in enumerate(cols):
        x = 40 + i * 300
        f.rect(x, 104, 280, 324, cls, rx=8, dash=mark == "cross")
        f.text(x + 18, 130, title, "e")
        y = 160
        for line in lines:
            if line.startswith("#"):
                f.text(x + 18, y, line[1:], "bb")
                y += 24
                continue
            if line.startswith("  "):
                y -= 8
            else:
                {"check": check, "diamond": diamond, "cross": cross}[mark](f, x + 18, y - 5)
            f.text(x + 38, y, line.strip(), "bs")
            y += 26 if mark != "check" else 24
    f.text(
        40,
        454,
        "A proof never authenticates its own enrollment: roots or keys supplied only by the prover "
        "establish nothing.",
        "s",
    )
    return f


def composition() -> Fig:
    comp = load("circle-reference-2026-10-28.json")["metrics"]["composition"]
    verdicts = comp["classifier_verdicts"]
    f = Fig(
        960,
        440,
        "Two proved computations, one opened request",
        "The opened request carries the prompt, response, model and context. The 23-segment LLM "
        "bundle is verified freshly; three new classifier proofs are made on the prompt and "
        "verified. A host join checks that both refer to the same request and rejects 16 "
        "changed bindings. Integrity passes; the CNN blocks, so policy release is false.",
    )
    header(f, "make e2e-composed", "Two proved computations, one opened request")
    f.rect(40, 108, 250, 222, "f-caller_soft k-caller", rx=8)
    f.text(56, 132, "OPENED REQUEST", "e")
    f.text(56, 160, "Prompt", "s")
    f.text(56, 180, ["Name the capital of France", "in one short sentence."], "bs", leading=17)
    f.text(56, 234, "Response", "s")
    f.text(56, 254, "The capital of France is Paris.", "bs")
    f.text(
        56, 290, ["Model ID · nonce · context", "salts derive from this request"], "s", leading=16
    )

    f.rect(330, 108, 290, 100, "f-panel k-line", rx=8)
    f.text(346, 136, "LLM bundle, verified freshly", "bb")
    f.text(
        346,
        160,
        f"{comp['llm_proofs_verified']} SASH proofs · {comp['residual_links']} residual links",
        "bs",
    )
    f.text(346, 184, "retained proof bytes, checked again", "s")
    f.rect(330, 230, 290, 100, "f-panel k-line", rx=8)
    f.text(346, 258, "Three new classifier proofs", "bb")
    f.text(346, 280, "rule, MLP and CNN read the prompt", "bs")
    for j, (name, v) in enumerate(zip(("rule", "MLP", "CNN"), verdicts, strict=True)):
        x = 346 + j * 88
        f.rect(x, 294, 80, 24, "f-proved_soft k-proved" if v else "f-accent_soft k-accent", rx=12)
        f.text(x + 40, 311, f"{name} · {'pass' if v else 'block'}", "s", "middle")

    f.rect(660, 108, 260, 222, "f-proved_soft k-proved", rx=8)
    f.text(676, 132, "HOST JOIN", "e")
    for i, line in enumerate(
        [
            "Same prompt, response, model",
            "and context in both proofs",
            "Exactly one proof per classifier",
            f"{len(comp['binding_rejections'])} changed bindings, all rejected",
        ]
    ):
        y = 162 + i * 26
        if i != 1:
            check(f, 676, y - 5)
        f.text(696, y, line, "bs")
    f.text(
        676,
        292,
        ["No recursion: the join is", "host code over two verified results"],
        "s",
        leading=16,
    )

    for y in (158, 280):
        f.line(292, 219 if y == 158 else 219, 326, y, "k-faint", 1.5, "a")
        f.line(622, y, 656, 219, "k-faint", 1.5, "a")
    f.rect(660, 350, 125, 40, "f-ink", rx=6)
    f.text(722, 375, "integrity · pass", "bs w", "middle", fill="bg")
    f.rect(795, 350, 125, 40, "f-accent_soft k-accent", rx=6)
    f.text(857, 375, "release · false", "bs w acc", "middle")
    f.line(790, 332, 790, 346, "k-faint", 1.5, "a")
    f.text(
        40,
        420,
        "Classifiers read the prompt; the response is bound into their context, not classified. "
        "Verdicts [1, 1, 0]: every proof is valid and the CNN blocks.",
        "s",
    )
    return f


# --- Charts -----------------------------------------------------------------------------


def axis(
    f: Fig,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    vmax: float,
    step: float,
    unit: str = " s",
) -> Callable[[float], float]:
    scale = (x1 - x0) / vmax
    v = 0.0
    while v <= vmax + 1e-9:
        x = x0 + v * scale
        f.line(x, y0, x, y1, "k-grid")
        f.text(x, y1 + 18, f"{v:g}{unit if v == 0 else ''}", "s", "middle")
        v += step
    return lambda value: value * scale


def perf_llm_gpu() -> Fig:
    llm = load("circle-reference-2026-10-28.json")["metrics"]["llm"]["backends"]
    cpu, gpu = llm["simd"], llm["cuda"]
    rows = [
        ("Trace generation", "host witness, before the session", "trace_seconds"),
        ("Proving session", "commitments, interaction, FRI", "prove_seconds"),
        ("Complete segment commands", "load, prove, verify, write", "command_seconds"),
    ]
    ratio = cpu["prove_seconds"] / gpu["prove_seconds"]
    f = Fig(
        960,
        424,
        "TinyLlama proving on one H200, CPU versus CUDA",
        "Paired bars summed over 23 segments. Trace generation: "
        f"{seconds(cpu['trace_seconds'])} CPU, {seconds(gpu['trace_seconds'])} GPU. Proving "
        f"session: {seconds(cpu['prove_seconds'])} versus {seconds(gpu['prove_seconds'])}. "
        f"Complete commands: {seconds(cpu['command_seconds'])} versus "
        f"{seconds(gpu['command_seconds'])}.",
    )
    header(
        f,
        "L1 · TinyLlama-1.1B on one NVIDIA H200 · sums over 23 segments",
        f"CUDA cuts the proving session {ratio:.2f}×; trace generation stays on the CPU",
    )
    legend(f, 290, 108, [("f-cpu", "CPU · SIMD"), ("f-s2", "GPU · CUDA")])
    x0, x1, top = 290, 800, 134
    sx = axis(f, x0, x1, top - 8, top + 3 * 72 - 12, 800, 100)
    f.text(880, 118, "CPU ÷ GPU", "s", "middle")
    for i, (label, sub, key) in enumerate(rows):
        y = top + i * 72
        f.text(40, y + 16, label, "bb")
        f.text(40, y + 34, sub, "s")
        for j, (series, cls) in enumerate(((cpu, "f-cpu"), (gpu, "f-s2"))):
            v = series[key]
            by = y + j * 22
            hbar(f, x0, by, sx(v), 18, cls)
            f.text(x0 + sx(v) + 8, by + 14, seconds(v), "m")
        f.text(880, y + 26, f"{cpu[key] / gpu[key]:.2f}×", "mb", "middle")
    note(
        f,
        386,
        "One CPU-then-GPU pair on the same host, inputs and parameters, 2026-10-26. "
        f"Interaction work ({fx(cpu['interaction_seconds'])} s / "
        f"{fx(gpu['interaction_seconds'])} s) is inside the "
        "session timer; do not add it. All 69 proof, statement and claim files are byte-identical "
        "across backends.",
    )
    return f


def perf_llm_timers() -> Fig:
    llm = load("circle-reference-2026-10-28.json")["metrics"]["llm"]["backends"]
    f = Fig(
        960,
        364,
        "What a complete LLM segment command contains",
        "Stacked bars for CPU and GPU complete segment commands, summed over 23 segments: "
        "trace generation, proving session, inline verification and the remainder by "
        "subtraction.",
    )
    gpu = llm["cuda"]
    header(
        f,
        "L1 · what a complete segment command contains",
        f"The {fx(gpu['prove_seconds'])} s session is one part of "
        f"{fx(gpu['command_seconds'])} s of GPU segment commands",
    )
    parts = [
        ("Trace generation", "trace", "s3"),
        ("Proving session", "session", "s1"),
        ("Inline verification", "inline verification", "s4"),
        ("Remainder", "remainder", "cpu"),
    ]
    legend(f, 40, 108, [(f"f-{c}", name) for name, _, c in parts])
    x0, x1 = 150, 800
    scale = (x1 - x0) / 700
    for i, (label, key) in enumerate((("CPU · SIMD", "simd"), ("GPU · CUDA", "cuda"))):
        b = llm[key]
        y = 146 + i * 84
        f.text(40, y + 19, label, "bb")
        known = b["trace_seconds"] + b["prove_seconds"] + b["inline_verify_seconds"]
        values = [
            b["trace_seconds"],
            b["prove_seconds"],
            b["inline_verify_seconds"],
            b["command_seconds"] - known,
        ]
        x = x0
        for j, ((_, _, c), v) in enumerate(zip(parts, values, strict=True)):
            w = v * scale
            if j == len(values) - 1:
                hbar(f, x + 1, y, w - 1, 28, f"f-{c}")
            else:
                f.rect(x + (1 if j else 0), y, w - (2 if j else 1), 28, f"f-{c}")
            if width(fx(v), 12.5, mono=True) + 10 < w:
                color = "ond" if c in ("s4", "cpu") else "onw"
                f.text(x + w / 2, y + 19, fx(v), f"m {color}", "middle")
            x += w
        f.text(x + 10, y + 19, f"{seconds(b['command_seconds'])} total", "mb")
        detail: list[str | tuple[str, str]] = []
        for j, ((_, short, _), v) in enumerate(zip(parts, values, strict=True)):
            detail += [" · " if j else "", (fx(v), "m"), f" {short}"]
            if j == 1:
                detail.append(f" (incl. {fx(b['interaction_seconds'])} interaction)")
        f.spans(x0, y + 48, detail, "s")
    note(
        f,
        326,
        "Seconds, summed over 23 segments. Remainder = complete command − (trace + session + "
        "inline verification): loading, serialization and unattributed time, by subtraction.",
    )
    return f


def perf_llm_segments() -> Fig:
    llm = load("circle-reference-2026-10-28.json")["metrics"]["llm"]["backends"]
    cpu = {r["tag"]: r["prove_seconds"] for r in llm["simd"]["rows"]}
    gpu = {r["tag"]: r["prove_seconds"] for r in llm["cuda"]["rows"]}
    tags = [r["tag"] for r in llm["simd"]["rows"]]
    ratios = [cpu[t] / gpu[t] for t in tags]
    early = sum(cpu[t] for t in tags[:3])
    rest = (llm["simd"]["prove_seconds"] - early) / (
        llm["cuda"]["prove_seconds"] - sum(gpu[t] for t in tags[:3])
    )
    f = Fig(
        960,
        380,
        "Proving-session time per segment",
        "Dumbbell chart on a logarithmic axis, one column per segment, CPU and GPU "
        f"proving-session seconds. Per-segment ratios range from {min(ratios):.1f}× to "
        f"{max(ratios):.1f}×.",
    )
    header(
        f,
        "L1 · proving-session time per segment, log scale",
        f"Per-segment speedup ranges from {min(ratios):.1f}× to {max(ratios):.1f}×; "
        "three early CPU segments dominate",
    )
    legend(f, 640, 104, [("f-cpu", "CPU · SIMD"), ("f-s2", "GPU · CUDA")], dot=True)
    x0, x1, ytop, ybot = 90, 920, 128, 300
    lo, hi = 1.0, 200.0

    def ly(v: float) -> float:
        import math

        return ybot - (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (
            ybot - ytop
        )

    for t in (1, 2, 5, 10, 20, 50, 100, 200):
        f.line(x0, ly(t), x1, ly(t), "k-grid")
        f.text(x0 - 10, ly(t) + 4, f"{t} s" if t in (1, 200) else str(t), "s", "end")
    slot = (x1 - x0) / len(tags)
    for i, t in enumerate(tags):
        cx = x0 + slot * (i + 0.5)
        f.line(cx, ly(gpu[t]), cx, ly(cpu[t]), "k-line", 2)
        f.circle(cx, ly(cpu[t]), 4.5, "f-cpu", ring=True)
        f.circle(cx, ly(gpu[t]), 4.5, "f-s2", ring=True)
        f.text(cx, ybot + 20, "head" if t == "head" else t.replace("B0", ""), "s", "middle")
    f.text(x0 + slot * 0.5 + 10, ly(cpu[tags[0]]) + 4, seconds(cpu[tags[0]]), "m")
    f.text(x0 + slot * 0.5 + 10, ly(gpu[tags[0]]) + 4, seconds(gpu[tags[0]]), "m")
    note(
        f,
        346,
        f"Segments L0–L2 take {fx(early)} s of the {fx(llm['simd']['prove_seconds'])} s SIMD "
        f"session total. Excluding them, the summed ratio would be {rest:.2f}× rather than "
        f"{llm['simd']['prove_seconds'] / llm['cuda']['prove_seconds']:.2f}×. This is a "
        "sensitivity check, not a replacement headline; the record does not isolate why the early "
        "SIMD segments are slower.",
    )
    return f


def zoom_level(
    f: Fig,
    y: float,
    title: str,
    parts: Sequence[tuple[str, float]],
    focus: int,
    x0: float = 40,
    x1: float = 920,
) -> tuple[float, float]:
    total = sum(v for _, v in parts)
    scale = (x1 - x0) / total
    f.text(x0, y - 10, title, "bb")
    x, hidden, span = x0, [], (x0, x1)
    for i, (name, v) in enumerate(parts):
        w = v * scale
        cls = "f-accent" if i == focus else ("f-soft2" if i % 2 else "f-layer")
        f.rect(x + (1 if i else 0), y, max(w - 2, 0.6), 30, cls)
        full, short = f"{name} · {fx(v)} s", f"{fx(v)} s"
        on = "onw" if i == focus else "ink"
        if width(full, 12.5, bold=True) + 12 < w:
            f.text(x + w / 2, y + 20, full, f"bs w {on}", "middle")
        elif width(short, 12.5, mono=True) + 8 < w:
            f.text(x + w / 2, y + 20, short, f"m {on}", "middle")
            f.text(x + w / 2, y + 46, name, "s", "middle")
        else:
            hidden.append(f"{name} {fx(v)} s")
        if i == focus:
            span = (x, x + w)
        x += w
    if hidden:
        f.text(x1, y - 10, "also: " + " · ".join(hidden), "s", "end")
    return span


def perf_classifier_c1() -> Fig:
    m = load("circle-reference-2026-10-28.json")["metrics"]
    cl, timing = m["classifiers"], m["timing"]
    ev = {e["stage"]: e["seconds"] for e in timing["events"]}
    eng = cl["engine_stages_seconds"]
    level1 = [
        ("MLP training", ev["mlp-training"]),
        ("CNN training", ev["cnn-training"]),
        ("Rust builds", ev["circle-prove-build"] + ev["circle-verify-build"]),
        ("Proof campaign", ev["classifier-proof-campaign"]),
    ]
    level1.append(("other", timing["seconds"] - sum(v for _, v in level1)))
    campaign = ev["classifier-proof-campaign"]
    level2 = [
        ("Enrollment", cl["enroll_commands_seconds"]),
        ("Host witnesses", cl["witness_seconds"]),
        ("Prover commands", cl["prover_commands_seconds"]),
        ("Verifiers", cl["verify_commands_seconds"]),
        ("Rejections", cl["rejection_commands_seconds"]),
    ]
    level2.append(("Host checks and bookkeeping", campaign - sum(v for _, v in level2)))
    traces = sum(
        eng[k]
        for k in (
            "admission_twiddles_and_transcript",
            "base_trace_generation",
            "base_trace_commitment",
            "interaction_generation",
            "interaction_commitment",
        )
    )
    level3 = [
        ("Parse", cl["input_parse_seconds"]),
        ("Preprocessing", eng["preprocessing_and_model_commitment"]),
        ("Traces and commitments", traces),
        ("Final STWO proving", eng["stark_proving"]),
    ]
    level3.append(("write + overhead", cl["prover_commands_seconds"] - sum(v for _, v in level3)))
    f = Fig(
        960,
        466,
        "One fresh classifier run, zoomed in",
        f"Three nested stacked bars. Complete controller {seconds(timing['seconds'])}; proof "
        f"campaign {seconds(campaign)}; prover commands {seconds(cl['prover_commands_seconds'])}, "
        f"of which final STWO proving is {seconds(eng['stark_proving'])}.",
    )
    header(
        f,
        "C1 · one fresh classifier run · Apple M4 Max · 2026-10-28",
        f"Training dominates the {fx(timing['seconds'])} s run; "
        f"final STWO proving is {fx(eng['stark_proving'])} s",
    )
    ys = (130, 238, 346)
    mark = len(f.items)
    spans = [
        zoom_level(f, ys[0], f"Complete controller · {fx(timing['seconds'])} s", level1, 3),
        zoom_level(f, ys[1], f"Proof campaign · {fx(campaign)} s", level2, 2),
        zoom_level(
            f, ys[2], f"Nine prover commands · {fx(cl['prover_commands_seconds'])} s", level3, 3
        ),
    ]
    for (a, b), y, y2 in reversed(list(zip(spans[:2], ys[:2], ys[1:], strict=True))):
        f.path(f"M{num(a)} {y + 31}L40 {y2 - 28}H920L{num(b)} {y + 31}Z", "f-soft", fill=True)
        f.items.insert(mark, f.items.pop())
    note(
        f,
        424,
        "Levels nest; never add them across rows. “Host checks and bookkeeping” and “write + "
        "overhead” are remainders by subtraction. Outside the prover: fresh proof-only "
        f"verification {fx(cl['verify_commands_seconds'], 3)} s for nine proofs · proof files "
        f"{cl['proof_bytes']:,} bytes.",
    )
    return f


def perf_classifier_gpu() -> Fig:
    g = load("classifier-gpu-benchmark-2026-10-28.json")
    s = g["summary"]
    names = (("Rule", "rule"), ("MLP", "mlp"), ("CNN", "encoder"))
    cpu, gpu = s["cpu"], s["cuda"]
    nine = (cpu["median_nine_proof_command_seconds"], gpu["median_nine_proof_command_seconds"])
    f = Fig(
        960,
        418,
        "Circle classifier proving on one A100",
        "Paired bars per classifier for median complete prover command, CPU versus CUDA, with "
        f"suite-level medians beside them: {seconds(nine[0])} CPU versus {seconds(nine[1])} CUDA.",
    )
    header(
        f,
        "A100 · nine Circle classifier proofs · three CPU/CUDA pairs",
        f"CUDA runs the nine prover commands {g['command_ratio_of_medians']:.2f}× faster: "
        f"{fx(nine[0])} s → {fx(nine[1])} s",
    )
    legend(f, 120, 108, [("f-cpu", "CPU · SIMD"), ("f-s2", "GPU · CUDA")])
    x0, x1, top = 120, 520, 136
    sx = axis(f, x0, x1, top - 8, top + 3 * 62 - 12, 16, 4)
    for i, (label, key) in enumerate(names):
        y = top + i * 62
        f.text(40, y + 24, label, "bb")
        for j, (series, cls) in enumerate(((cpu, "f-cpu"), (gpu, "f-s2"))):
            v = series["per_classifier"][key]["median_command_seconds"]
            hbar(f, x0, y + j * 22, sx(v), 18, cls)
            f.text(x0 + sx(v) + 8, y + j * 22 + 14, seconds(v, 3), "m")
    f.text(x0, top + 3 * 62 + 28, "median complete prover command, one proof", "s")
    tiles = [
        (
            "Nine prover commands",
            f"{fx(nine[0])} → {fx(nine[1])} s",
            f"{g['command_ratio_of_medians']:.2f}× ratio of medians",
        ),
        (
            "Nine final STWO calls, inside the commands",
            f"{fx(cpu['median_nine_final_stark_seconds'])} → "
            f"{fx(gpu['median_nine_final_stark_seconds'])} s",
            f"{g['final_stark_ratio_of_medians']:.2f}× ratio of medians",
        ),
        (
            "Peak sampled prover RSS",
            f"{cpu['maximum_sampled_prover_rss_bytes'] / 1e9:.2f} → "
            f"{gpu['maximum_sampled_prover_rss_bytes'] / 1e9:.2f} GB",
            f"plus {g['telemetry']['peak_used_mib'] / 1024:.2f} GiB of device memory",
        ),
    ]
    for i, (label, value, sub) in enumerate(tiles):
        y = 104 + i * 82
        f.rect(600, y, 320, 72, "f-panel k-line", rx=6)
        f.text(616, y + 21, label, "s")
        f.text(616, y + 45, value, "mbig")
        f.text(616, y + 63, sub, "s")
    acc = g["acceptance"]
    note(
        f,
        380,
        f"All {acc['proofs']} proofs verify on Linux and on a stock Mac verifier; all "
        f"{acc['linux_public_mutation_rejections']} public-input mutations reject. Training, "
        "Python witness preparation and verification are excluded. Per-classifier medians pool "
        "three requests × three repetitions.",
    )
    return f


FIGURES: dict[str, Callable[[], Fig]] = {
    "overview": overview,
    "llm-statement": llm_statement,
    "llm-pipeline": llm_pipeline,
    "classifier-statement": classifier_statement,
    "classifier-pipeline": classifier_pipeline,
    "verdict-matrix": verdict_matrix,
    "trust-boundary": trust_boundary,
    "composition": composition,
    "perf-llm-gpu": perf_llm_gpu,
    "perf-llm-timers": perf_llm_timers,
    "perf-llm-segments": perf_llm_segments,
    "perf-classifier-c1": perf_classifier_c1,
    "perf-classifier-gpu": perf_classifier_gpu,
}


def render() -> dict[str, str]:
    return {f"{name}.svg": build().svg() for name, build in FIGURES.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed figures are stale")
    args = parser.parse_args()
    figures = render()
    if args.check:
        stale = [
            n for n, s in figures.items() if not (OUT / n).is_file() or (OUT / n).read_text() != s
        ]
        if stale:
            sys.exit("stale figures (run scripts/render_figures.py): " + ", ".join(stale))
        print(f"{len(figures)} figures match the evidence.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for name, svg in figures.items():
        (OUT / name).write_text(svg)
    print(f"wrote {len(figures)} figures to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
