"""Generate main.tex from proofs-attestation-logs.md (numeric citations by first use).

Run from this folder: python3 md2tex.py. Figure 1 (TikZ) and Figure 2 come from
figure1.tex and figure2.tex; build the PDF with tectonic main.tex.
"""

import re
from pathlib import Path

CITE = re.compile(r"\[([A-F]\d+|SASH)\]")

PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage[a4paper,margin=2.5cm]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{newunicodechar}
\usepackage{graphicx}
\usepackage{xltabular}
\usepackage{booktabs}
\usepackage{array}
\usepackage{enumitem}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning}
\usepackage[hidelinks]{hyperref}
\usepackage{xurl}
\setlist{nosep,leftmargin=*}
\renewcommand\tabularxcolumn[1]{>{\raggedright\arraybackslash}p{#1}}
\newunicodechar{′}{\ensuremath{'}}
\newunicodechar{∧}{\ensuremath{\wedge}}
\newunicodechar{τ}{\ensuremath{\tau}}
\newunicodechar{σ}{\ensuremath{\sigma}}
\newunicodechar{β}{\ensuremath{\beta}}
\newunicodechar{ρ}{\ensuremath{\rho}}
\newunicodechar{λ}{\ensuremath{\lambda}}
\newunicodechar{κ}{\ensuremath{\kappa}}
\newunicodechar{ε}{\ensuremath{\varepsilon}}
\newunicodechar{×}{\ensuremath{\times}}
\newunicodechar{−}{\ensuremath{-}}
\newunicodechar{⪯}{\ensuremath{\preceq}}
\newunicodechar{⊆}{\ensuremath{\subseteq}}
\newunicodechar{⊂}{\ensuremath{\subset}}
\newunicodechar{→}{\ensuremath{\to}}
\newunicodechar{≥}{\ensuremath{\geq}}
\newunicodechar{≤}{\ensuremath{\leq}}
\newunicodechar{≠}{\ensuremath{\neq}}
\newunicodechar{≈}{\ensuremath{\approx}}
\newunicodechar{·}{\ensuremath{\cdot}}
\newunicodechar{…}{\ldots}
\newunicodechar{₀}{\textsubscript{0}}
\newunicodechar{₁}{\textsubscript{1}}
\newunicodechar{₂}{\textsubscript{2}}
\newunicodechar{₃}{\textsubscript{3}}
\newunicodechar{₇}{\textsubscript{7}}
\newunicodechar{ᵥ}{\textsubscript{v}}
\newunicodechar{ᵢ}{\textsubscript{i}}
\newunicodechar{ⱼ}{\textsubscript{j}}
\newunicodechar{ₖ}{\textsubscript{k}}
\newunicodechar{꜀}{\textsubscript{c}}
"""


def escape(text):
    out = []
    for ch in text:
        out.append(
            {
                "\\": r"\textbackslash{}",
                "&": r"\&",
                "%": r"\%",
                "$": r"\$",
                "#": r"\#",
                "_": r"\_",
                "{": r"\{",
                "}": r"\}",
                "~": r"\textasciitilde{}",
                "^": r"\textasciicircum{}",
            }.get(ch, ch)
        )
    return "".join(out)


def inline(text, order):
    keep = []

    def stash(value):
        keep.append(value)
        return f"\x00{len(keep) - 1}\x00"

    text = re.sub(r"`([^`]+)`", lambda m: stash(r"\texttt{" + escape(m.group(1)) + "}"), text)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        lambda m: stash(
            r"\href{"
            + m.group(2).replace("%", r"\%").replace("#", r"\#")
            + "}{"
            + escape(m.group(1))
            + "}"
        ),
        text,
    )
    text = re.sub(
        r"(?<![\w(])https?://[^\s)<>\]]+[^\s)<>\].,;:]",
        lambda m: stash(r"\url{" + m.group(0).replace("%", r"\%").replace("#", r"\#") + "}"),
        text,
    )

    def cite(m):
        key = m.group(1)
        order.setdefault(key, len(order) + 1)
        return stash(r"\cite{" + key + "}")

    text = CITE.sub(cite, text)
    text = escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\\emph{\1}", text)
    text = text.replace('"', "''").replace(" -- ", " -- ")
    text = re.sub(r"(^|[\s(\[])''", r"\1``", text)
    while "\x00" in text:
        text = re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], text)
    return text


def table(rows, order):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    header, body = cells[0], [r for r in cells[2:]]
    n = len(header)
    spec = "|".join(["X"] * n)
    lines = [
        r"{\small",
        r"\begin{xltabular}{\linewidth}{" + spec.replace("|", "") + "}",
        r"\toprule",
    ]
    lines.append(" & ".join(r"\textbf{" + inline(h, order) + "}" for h in header) + r" \\ \midrule")
    lines.append(r"\endhead")
    for r in body:
        r = (r + [""] * n)[:n]
        lines.append(" & ".join(inline(c, order) for c in r) + r" \\")
    lines += [r"\bottomrule", r"\end{xltabular}}"]
    return "\n".join(lines)


def convert(md, figure1, figure2):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.split("\n")
    order, body, refs = {}, [], {}
    title = lines[0].lstrip("# ").strip()
    author = lines[2].strip()
    i, n = 3, len(lines)
    in_refs = False
    stack = []  # open list environments: (indent, env)

    def close_lists(to_indent=-1):
        while stack and stack[-1][0] > to_indent:
            body.append(r"\end{" + stack.pop()[1] + "}")

    while i < n:
        line = lines[i]
        if in_refs:
            m = re.match(r"^- \[([A-F]\d+|SASH)\]\s*(.*)$", line)
            if m:
                refs[m.group(1)] = m.group(2)
            i += 1
            continue
        if line.startswith("```"):
            close_lists()
            j = i + 1
            while not lines[j].startswith("```"):
                j += 1
            if "figure1-spec" in line:
                body.append(figure1)
            i = j + 1
            continue
        if re.match(r"^\*\*Figure 1\.\*\*", line):
            i += 1
            continue
        if re.match(r"^\*\*Figure 2\.\*\*", line) or re.match(r"^!\[", line):
            if re.match(r"^\*\*Figure 2\.\*\*", line):
                cap = re.sub(r"^\*\*Figure 2\.\*\*\s*", "", line)
                body.append(figure2.replace("CAPTION", inline(cap, order)))
            i += 1
            continue
        h = re.match(r"^(#{2,4})\s+(.*)$", line)
        if h:
            close_lists()
            level, text = len(h.group(1)), h.group(2).strip()
            if text == "Abstract":
                j = i + 1
                para = []
                while (
                    j < n and not lines[j].startswith("#") and not lines[j].startswith("**Keywords")
                ):
                    para.append(lines[j])
                    j += 1
                body.append(
                    r"\begin{abstract}"
                    + "\n"
                    + inline(" ".join(p.strip() for p in para if p.strip()), order)
                )
                if j < n and lines[j].startswith("**Keywords"):
                    body.append("\n\\medskip\\noindent " + inline(lines[j], order))
                    j += 1
                body.append(r"\end{abstract}")
                i = j
                continue
            if text == "References":
                in_refs = True
                i += 1
                continue
            numbered = re.match(r"^(\d+(?:\.\d+)*)\s+(.*)$", text)
            cmd = {2: "section", 3: "subsection", 4: "subsubsection"}[level]
            if numbered:
                body.append("\\" + cmd + "{" + inline(numbered.group(2), order) + "}")
            else:
                body.append("\\" + cmd + "*{" + inline(text, order) + "}")
            i += 1
            continue
        if line.startswith("|"):
            close_lists()
            rows = []
            while i < n and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            body.append(table(rows, order))
            continue
        li = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if li:
            indent = len(li.group(1))
            env = "enumerate" if li.group(2)[0].isdigit() else "itemize"
            if not stack or indent > stack[-1][0]:
                stack.append((indent, env))
                body.append(r"\begin{" + env + "}")
            else:
                close_lists(indent)
                if not stack or stack[-1][0] < indent or stack[-1][1] != env:
                    if stack and stack[-1][0] == indent:
                        body.append(r"\end{" + stack.pop()[1] + "}")
                    stack.append((indent, env))
                    body.append(r"\begin{" + env + "}")
            body.append(r"\item " + inline(li.group(3), order))
            i += 1
            continue
        if not line.strip():
            if stack and i + 1 < n and re.match(r"^(\s*)([-*]|\d+\.)\s+", lines[i + 1]):
                i += 1
                continue
            close_lists()
            body.append("")
            i += 1
            continue
        if stack and line.startswith("  "):
            body[-1] += " " + inline(line.strip(), order)
            i += 1
            continue
        close_lists()
        para = [line]
        i += 1
        while (
            i < n
            and lines[i].strip()
            and not re.match(r"^(#|\||```|\s*([-*]|\d+\.)\s|\*\*Figure)", lines[i])
        ):
            para.append(lines[i])
            i += 1
        body.append(inline(" ".join(p.strip() for p in para), order))
    close_lists()
    missing = [k for k in order if k not in refs]
    if missing:
        raise SystemExit(f"cited but not in reference list: {missing}")
    bib = [r"\begin{thebibliography}{99}"]
    for key in sorted(order, key=order.get):
        dummy = {}
        bib.append(r"\bibitem{" + key + "} " + inline(refs[key], dummy))
    bib.append(r"\end{thebibliography}")
    unused = sorted(set(refs) - set(order))
    doc = [
        PREAMBLE,
        r"\title{" + inline(title, {}) + "}",
        r"\author{" + inline(author, {}) + "}",
        r"\date{}",
        r"\begin{document}",
        r"\maketitle",
        *body,
        *bib,
        r"\end{document}",
    ]
    return "\n".join(doc) + "\n", unused


ACCENTS = {
    "Æ": r"\AE{}",
    "č": r"\v{c}",
    "š": r"\v{s}",
    "ö": r"\"{o}",
    "ü": r"\"{u}",
    "è": r"\`{e}",
    "ć": r"\'{c}",
    "–": "--",
    "§": r"\S{}",
}


def breaks(m):
    s = m.group(1)
    if re.fullmatch(r"[0-9a-f]{32,}", s):
        return r"\texttt{" + r"\allowbreak{}".join(s[i : i + 8] for i in range(0, len(s), 8)) + "}"
    s = re.sub(r"(::|[/.\-:])", r"\1\\allowbreak{}", s)
    s = re.sub(r"\\_(?=[A-Za-z]{5,})", r"\\_\\allowbreak{}", s)
    return r"\texttt{" + s + "}"


def post(t):
    t = t.replace(
        r"\renewcommand\tabularxcolumn[1]{>{\raggedright\arraybackslash}p{#1}}",
        "\\setlength{\\emergencystretch}{2em}\n\\renewcommand\\tabularxcolumn[1]{>{\\raggedright\\arraybackslash\\hspace{0pt}}p{#1}}",
    )
    t = t.replace("{\\small", "{\\footnotesize\\setlength\\tabcolsep{2.5pt}", 1)
    t = re.sub(r"\\texttt\{([^{}]*)\}", breaks, t)
    t = re.sub(
        r"^> (.*)$",
        r"\\begin{center}\\fbox{\\parbox{0.94\\linewidth}{\\small \1}}\\end{center}",
        t,
        flags=re.M,
    )
    t = re.sub(r"(?<![{(]\\url\{)(?<!\\url\{)\((https?://[^\s)]+)\)", r"(\\url{\1})", t)
    t = re.sub(r"(\d+)\\textasciicircum\{\}(\d+)", r"\\ensuremath{\1^{\2}}", t)
    t = re.sub(r"(?:\\emph\{W\}|\bW)\\_([vgc])\b", r"$W_\1$", t)
    for k, v in ACCENTS.items():
        t = t.replace(k, v)
    return t


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    tex, unused = convert(
        (here / "proofs-attestation-logs.md").read_text(),
        (here / "figure1.tex").read_text(),
        (here / "figure2.tex").read_text(),
    )
    (here / "main.tex").write_text(post(tex))
    print("wrote main.tex; listed but uncited references:", unused or "none")
