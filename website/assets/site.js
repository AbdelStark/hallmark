"use strict";

function enhanceHallmark() {
  document.querySelectorAll(".arithmatex:not([data-rendered])").forEach((element) => {
    if (!window.katex) return;
    const input = element.textContent.trim();
    const display = input.startsWith("\\[");
    const expression = input.replace(/^\\[\[(]/, "").replace(/\\[\])]$/, "");
    window.katex.render(expression, element, {
      displayMode: display, throwOnError: false, trust: false, output: "htmlAndMathml"
    });
    element.dataset.rendered = "true";
  });
  document.querySelectorAll("[data-proof-explorer]:not([data-enhanced])").forEach((explorer) => {
    const buttons = explorer.querySelectorAll("[data-proof-choice]");
    const panels = explorer.querySelectorAll("[data-proof-panel]");
    function select(choice) {
      buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.proofChoice === choice)));
      panels.forEach((panel) => { panel.hidden = panel.dataset.proofPanel !== choice; });
    }
    buttons.forEach((button) => button.addEventListener("click", () => select(button.dataset.proofChoice)));
    select("llm");
    function selectAnchor() {
      const target = document.getElementById(location.hash.slice(1));
      const panel = target?.closest("[data-proof-panel]");
      if (panel) select(panel.dataset.proofPanel);
    }
    selectAnchor();
    window.addEventListener("hashchange", selectAnchor);
    explorer.dataset.enhanced = "true";
  });
}

if (typeof document$ !== "undefined") document$.subscribe(enhanceHallmark);
else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", enhanceHallmark);
else enhanceHallmark();
