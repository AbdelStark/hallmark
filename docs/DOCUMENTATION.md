# Maintain the documentation site

The public site is deployed at
[abdelstark.github.io/hallmark](https://abdelstark.github.io/hallmark/).
It uses **Zensical 0.0.73**, pinned in a separate `website/` project and lockfile.

Canonical guides and research records stay in their existing Markdown files.
The site stages tracked documentation, public evidence and explicit assets;
it does not publish ignored runs or untracked files.

## Build and preview

From a Git checkout, using uv 0.9.18:

```sh
make docs
make docs-serve
```

The preview is at `http://127.0.0.1:8000/`. The second command rebuilds first,
then serves the generated site. After editing source files, run `make docs`
and refresh the browser. No custom watch daemon is used.

New source/asset files must be staged with `git add <exact-paths>` before a
local build. Modified tracked files use their working-tree contents.
This intentional boundary prevents an untracked research note from appearing
in the published site.

## Where to edit

| Surface | Source |
|---|---|
| Homepage content | [index.md](../index.md) |
| Homepage layout | [home.html](../website/overrides/home.html) |
| Navigation and extensions | [mkdocs.yml](../mkdocs.yml) |
| Visual system | [styles.css](../website/assets/styles.css) |
| Math and proof explorer | [site.js](../website/assets/site.js) |
| Figures | [render_figures.py](../scripts/render_figures.py) writes `docs/assets/figures/` |
| Educational path | [Learn](learn/index.md) |
| Evidence entry point | [Research evidence map](research/index.md) |
| Staging and validation | [build script](../scripts/build_docs.py), [site checker](../scripts/check_site.py) |
| Deployment | [Pages workflow](../.github/workflows/pages.yml) |

Python environments and model/proof pipelines are unchanged by a docs build.
The separate docs environment is optional; ordinary users do not install it.
The inference `uv.lock` and enrolled verifier identity remain unchanged.

## Publishing

The Pages workflow builds and validates pull requests. Deployment runs only from
`main` or a manual dispatch targeting `main`, using the `github-pages`
environment. It uses the locked environment, pinned action commits and the
standard Pages artifact/OIDC deployment flow; no personal deployment token or
scheduled job is needed.

Keep the repository and site public. No custom domain, analytics, comments,
external search account or research compute scheduler is configured.

## Validation

`make docs` runs a strict site build and checks generated local links/assets
and anchors. It also checks that the homepage, search index, equations, diagrams
and model links are present. Unit tests exercise tracked-file selection,
link rewriting and rejection of unsafe staging inputs.

Before publishing, review a desktop and narrow viewport, navigation/search,
code copying, theme switching and the educational proof selector.
Verify the hosted deployment and live paths after merging.

## Figures

The diagrams and charts in `docs/assets/figures/` are generated, never drawn by
hand. [render_figures.py](../scripts/render_figures.py) reads the frozen records
in `research/evidence/` and the fixed LLM case, and writes self-contained SVGs
that switch to a dark palette with the reader's system theme. Chart colours
pass a colour-vision-deficiency check against both backgrounds.

```sh
python scripts/render_figures.py          # regenerate
python scripts/render_figures.py --check  # fail if a figure is stale
```

`tests/test_figures.py` fails when a committed figure differs from what the
evidence produces, so a changed record cannot leave an old chart behind. To
change a figure, edit the script and regenerate; do not edit the SVG. Every
figure needs alt text that states its numbers, and a table or prose nearby
that carries the same values.

## Asset provenance and claims

Fonts and KaTeX are self-hosted. Their licences, original release URLs,
package-integrity values and per-file SHA-256 hashes are in
[asset provenance](../website/assets/vendor/sources.json). Zensical provides
the search/navigation and Mermaid integration.

Keep every performance number linked to a recorded measurement and state its
boundary. Do not turn a software check, model download, native rerun or hash
receipt into a proof or hardware claim. Older protocols/decisions remain dated
research records; never rewrite numeric evidence to make the site look cleaner.
