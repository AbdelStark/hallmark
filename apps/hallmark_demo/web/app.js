"use strict";
const $ = (id) => document.getElementById(id);
const active = new Set(["starting", "running", "cancelling", "detached"]);
const state = {
  info: null,
  workflow: null,
  selected: null,
  run: null,
  lastSequence: 0,
  busy: false,
  polling: false,
};
function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function error(message) {
  if ($("error").textContent !== (message || ""))
    $("error").textContent = message || "";
  $("error").hidden = !message;
}
function bytes(n) {
  if (n === null || n === undefined) return "—";
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(0)} KiB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} MiB`;
  return `${(n / 1024 ** 3).toFixed(2)} GiB`;
}
function duration(n) {
  const s = Math.max(0, Math.floor(n));
  return s < 60
    ? `${s}s`
    : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}
function status(s) {
  return s === "detached" ? "running · reattached" : s.replaceAll("_", " ");
}
async function api(path, payload, refreshed = false) {
  const options =
    payload === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Hallmark-Token": state.info.token,
          },
          body: JSON.stringify(payload),
        };
  const response = await fetch(path, options);
  const data = await response.json();
  if (response.status === 403 && payload !== undefined && !refreshed) {
    const updated = await api("/api/info");
    if (updated.root !== state.info.root)
      throw new Error("The controller checkout changed. Reload the workbench.");
    if (updated.token !== state.info.token) {
      state.info = updated;
      return api(path, payload, true);
    }
  }
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function connected(ok) {
  $("connection-dot").className = `dot ${ok ? "connected" : "offline"}`;
  $("connection").textContent = ok
    ? "Local server connected"
    : "Disconnected · retrying";
}
function field(name, label, hint, kind, required = false) {
  const wrapper = el("label", label, "field");
  let input;
  if (kind) {
    input = el("input");
    input.type = "text";
    input.placeholder = "runs/…";
    const list = el("datalist");
    list.id = `retained-${name}`;
    for (const item of state.info.retained.filter((r) => r.kind === kind)) {
      const option = el("option", item.name);
      option.value = item.path;
      list.append(option);
    }
    input.setAttribute("list", list.id);
    wrapper.append(list);
  } else {
    input = el("input");
    input.type = "text";
    input.inputMode = "decimal";
    input.autocomplete = "off";
  }
  input.name = name;
  input.id = `param-${name}`;
  input.required = required;
  wrapper.append(input, el("small", hint));
  $("parameters").append(wrapper);
  return input;
}
async function choose(workflow) {
  state.workflow = workflow;
  state.selected = null;
  state.run = null;
  error("");
  $("setup").hidden = false;
  $("monitor").hidden = true;
  document.querySelectorAll(".workflow").forEach((b) => {
    const on = b.dataset.workflow === workflow.id;
    b.classList.toggle("selected", on);
    b.setAttribute("aria-pressed", String(on));
  });
  $("workflow-title").textContent = workflow.title;
  $("workflow-summary").textContent = workflow.summary;
  $("scheme").textContent = workflow.scheme;
  $("claim").textContent = workflow.claim;
  $("planned-stages").replaceChildren(
    ...workflow.stages.map((s) => el("li", s.title)),
  );
  $("case").hidden = !workflow.example;
  if (workflow.example) {
    $("case-heading").textContent = workflow.example.title;
    $("case-prompt").textContent = workflow.example.prompt;
    $("case-response").textContent = workflow.example.response;
    $("case-note").textContent = workflow.example.note;
  }
  $("parameters").replaceChildren();
  for (const spec of workflow.fields) {
    const input = field(
      spec.name,
      spec.label,
      spec.hint,
      spec.suggestions,
      spec.required,
    );
    input.value = spec.default;
    input.readOnly = spec.read_only;
    input.inputMode = spec.kind === "money" ? "decimal" : "text";
  }
  $("duration").textContent = workflow.duration;
  const updateCost = () => {
    const paid =
      workflow.paid_ceiling &&
      !(workflow.local_when && $(`param-${workflow.local_when}`)?.value);
    $("cost").textContent = paid
      ? `Paid HF execution · $${$("param-max_cost")?.value || workflow.paid_ceiling} ceiling`
      : "Local execution · no cloud charge";
    $("start").textContent = paid
      ? "Start paid workflow →"
      : "Start workflow →";
    $("launch-note").textContent = paid
      ? "The driver checks live prices and existing jobs. HF_TOKEN stays in the server environment or ignored .env."
      : "The controller retains logs, reports and failed attempts in runs/.";
  };
  $("parameters").oninput = updateCost;
  updateCost();
  $("workflow-docs").href =
    `https://abdelstark.github.io/hallmark/${workflow.docs.replace(/\.md(?=#|$)/, "/").replace(/\.md$/, "/")}`;
  $("checks").textContent = "Checking prerequisites…";
  $("start").disabled = true;
  try {
    const checks = await api(`/api/checks/${workflow.id}`);
    if (state.workflow.id !== workflow.id || state.selected) return;
    $("checks").replaceChildren(
      ...checks.map((c) => {
        const row = el("div", undefined, "check");
        row.append(
          el("span", c.ok ? "✓" : "×", c.ok ? "good" : "bad"),
          el("span", c.label),
          el("small", c.detail),
        );
        return row;
      }),
    );
    $("start").disabled = checks.some((c) => !c.ok);
  } catch (e) {
    error(e.message);
  }
}
function history(runs) {
  $("history").replaceChildren();
  if (!runs.length) {
    $("history").append(
      el(
        "p",
        "Your runs will appear here. Start a workflow to retain its progress and evidence.",
        "fine",
      ),
    );
    return;
  }
  for (const run of runs.slice(0, 30)) {
    const button = el(
      "button",
      undefined,
      `history-item${run.id === state.selected ? " selected" : ""}`,
    );
    button.type = "button";
    button.append(
      el("strong", run.title),
      el(
        "span",
        `${status(run.status)} · ${new Date(run.started_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`,
      ),
    );
    button.addEventListener("click", () => openRun(run.id));
    $("history").append(button);
  }
}
async function openRun(key) {
  error("");
  state.selected = key;
  state.lastSequence = 0;
  $("setup").hidden = true;
  $("monitor").hidden = false;
  try {
    render(await api(`/api/runs/${key}`));
  } catch (e) {
    error(e.message);
  }
}
function chart(samples) {
  const svg = $("resource-chart");
  const width = Math.max(svg.clientWidth, 320),
    right = width - 15;
  svg.setAttribute("viewBox", `0 0 ${width} 110`);
  svg.replaceChildren();
  const node = (tag, attrs, text) => {
    const n = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v));
    if (text) n.textContent = text;
    svg.append(n);
    return n;
  };
  if (samples.length < 2) {
    node(
      "text",
      { x: 18, y: 60, class: "chart-empty" },
      "Waiting for two resource samples",
    );
    return;
  }
  const first = samples[0].seconds;
  const last = samples.at(-1).seconds;
  const max = Math.max(...samples.map((s) => s.rss_bytes), 1);
  node("line", { x1: 55, y1: 85, x2: right, y2: 85, class: "chart-grid" });
  node("line", { x1: 55, y1: 15, x2: right, y2: 15, class: "chart-grid" });
  const points = samples
    .map(
      (s) =>
        `${55 + ((s.seconds - first) / Math.max(last - first, 0.1)) * (right - 55)},${85 - (s.rss_bytes / max) * 70}`,
    )
    .join(" ");
  node("polygon", {
    points: `55,85 ${points} ${right},85`,
    class: "chart-area",
  });
  node("polyline", { points, class: "chart-line" });
  node("text", { x: 4, y: 19, class: "chart-label" }, bytes(max));
  node("text", { x: 20, y: 88, class: "chart-label" }, "0");
  node(
    "text",
    { x: 55, y: 104, class: "chart-label" },
    last - first < 5 ? `${first.toFixed(1)}s` : duration(first),
  );
  node(
    "text",
    { x: right, y: 104, "text-anchor": "end", class: "chart-label" },
    last - first < 5 ? `${last.toFixed(1)}s` : duration(last),
  );
}
function resultTable(headers, rows) {
  const table = el("table", undefined, "results-table");
  const head = el("thead"),
    header = el("tr");
  for (const title of headers) header.append(el("th", title));
  head.append(header);
  table.append(head);
  const body = el("tbody");
  for (const values of rows) {
    const row = el("tr");
    for (const value of values)
      row.append(
        typeof value === "object"
          ? el("td", value.text, value.cls)
          : el("td", String(value)),
      );
    body.append(row);
  }
  table.append(body);
  const container = el("div", undefined, "table-scroll");
  container.append(table);
  return container;
}
function results(run) {
  const root = $("result-content");
  root.replaceChildren();
  if (!run.result || !run.summary) {
    const box = el("div", undefined, "result-banner");
    box.append(
      el(
        "h2",
        active.has(run.status)
          ? "Waiting for verification"
          : status(run.status),
      ),
      el(
        "p",
        run.error ||
          "Results appear after the driver finishes its verification and binding checks.",
      ),
    );
    root.append(box);
    return;
  }
  const summary = run.summary;
  const banner = el("div", undefined, "result-banner");
  banner.append(el("h2", summary.title), el("p", summary.note));
  root.append(banner);
  const facts = el("div", undefined, "result-facts");
  for (const metric of summary.metrics) {
    const row = el("div", undefined, "fact");
    row.append(
      el("span", metric.label),
      el(
        "strong",
        metric.unit === "USD"
          ? `$${metric.value.toFixed(4)}`
          : String(metric.value),
      ),
    );
    facts.append(row);
  }
  root.append(facts);
  if (summary.response) {
    const quote = el("div", undefined, "case");
    quote.append(
      el("p", "PROVED RESPONSE", "section-label"),
      el("p", summary.response),
    );
    root.append(quote);
  }
  if (summary.cases.length)
    root.append(
      resultTable(
        ["Request", "Rule", "MLP", "CNN", "All-pass policy"],
        summary.cases.map((item) => [
          item.name,
          ...item.verdicts.map((v) => ({
            text: v ? "Pass" : "Block",
            cls: v ? "pass" : "block",
          })),
          {
            text: item.release ? "Release" : "Block",
            cls: item.release ? "pass" : "block",
          },
        ]),
      ),
    );
  if (summary.measurements.length) {
    root.append(
      resultTable(
        [
          "Backend",
          "Proving stages",
          "Full commands",
          "Host peak RSS",
          "GPU peak memory",
          "Proof bytes",
        ],
        summary.measurements.map((m) => [
          m.backend.toUpperCase(),
          `${m.prove_seconds.toFixed(2)} s`,
          `${m.commands_seconds.toFixed(2)} s`,
          bytes(m.sampled_peak_rss_bytes),
          bytes(m.gpu_peak_memory_mib * 1024 ** 2),
          bytes(m.serialized_proof_bytes),
        ]),
      ),
    );
    root.append(
      el(
        "p",
        "One matched pair. Proving-stage timings exclude preparation, transfers and verification.",
        "fine",
      ),
    );
  }
  if (run.result_sha256)
    root.append(el("p", `Result SHA-256: ${run.result_sha256}`, "fine"));
  const details = el("details");
  details.append(
    el("summary", "Full driver result"),
    el("pre", JSON.stringify(run.result, null, 2)),
  );
  root.append(details);
}
function render(run) {
  if (state.selected !== run.id) return;
  const previous = state.run;
  state.run = run;
  state.workflow = state.info.workflows.find((w) => w.id === run.workflow);
  document.querySelectorAll(".workflow").forEach((b) => {
    const selected = b.dataset.workflow === run.workflow;
    b.classList.toggle("selected", selected);
    b.setAttribute("aria-pressed", String(selected));
  });
  $("run-title").textContent = run.title;
  $("run-scheme").textContent = run.scheme;
  $("run-identity").textContent =
    `${run.id} · ${new Date(run.started_at).toLocaleString()} · source ${run.source_commit.slice(0, 12)}`;
  $("run-status").textContent = status(run.status);
  $("run-status").className = `status-tag ${run.status}`;
  const current = run.stages.find((s) => s.status === "running");
  $("current-stage").textContent =
    current?.title ||
    (run.cleanup_required
      ? "Cloud cleanup needs attention"
      : run.status === "succeeded"
        ? "All checks complete"
        : "Retained evidence available");
  $("elapsed").textContent = duration(run.elapsed_seconds);
  $("cancel").hidden = !active.has(run.status);
  $("cancel").disabled = run.status === "cancelling";
  $("cancel").textContent =
    run.status === "cancelling" ? "Stopping · retaining outputs" : "Stop run";
  $("stages").replaceChildren(
    ...run.stages.map((s) =>
      el("li", `${s.status === "succeeded" ? "✓ " : ""}${s.title}`, s.status),
    ),
  );
  const last = run.samples.at(-1);
  $("rss-label").textContent = active.has(run.status)
    ? "CURRENT RSS"
    : "LAST OBSERVED RSS";
  $("cpu-label").textContent = active.has(run.status)
    ? "CPU · 100% = ONE CORE"
    : "LAST CPU SAMPLE";
  $("rss").textContent = last ? bytes(last.rss_bytes) : "—";
  $("peak").textContent = run.samples.length ? bytes(run.local_peak_rss) : "—";
  $("cpu").textContent =
    last?.cpu_percent === null || !last
      ? "—"
      : `${last.cpu_percent.toFixed(0)}%`;
  $("processes").textContent = last
    ? `${last.processes} observed processes`
    : "Waiting for process samples";
  chart(run.samples);
  $("jobs").hidden = !run.jobs.length;
  $("jobs").replaceChildren(
    ...run.jobs.map((job) => {
      const row = el("div", undefined, "job");
      const link = el("a", `${job.phase} · ${job.id} ↗`);
      link.href = job.url;
      link.target = "_blank";
      link.rel = "noreferrer";
      row.append(
        link,
        el(
          "span",
          `${job.status}${job.cleanup_complete ? " · outputs retained / bucket deleted" : ""}`,
        ),
      );
      return row;
    }),
  );
  const sequence = run.next_seq;
  if (sequence !== state.lastSequence) {
    const logs = $("logs");
    const nearBottom =
      logs.scrollTop + logs.clientHeight >= logs.scrollHeight - 40;
    logs.textContent = run.events
      .map((e) => `${new Date(e.time).toLocaleTimeString()}  ${e.message}`)
      .join("\n");
    if ($("follow").checked && (nearBottom || state.lastSequence === 0))
      logs.scrollTop = logs.scrollHeight;
    state.lastSequence = sequence;
  }
  if (
    !previous ||
    previous.status !== run.status ||
    previous.result_sha256 !== run.result_sha256
  )
    results(run);
  $("output-path").textContent =
    run.output || "Waiting for the driver to create its evidence directory.";
  $("artifacts").replaceChildren(
    ...run.artifacts.map((item) => {
      const row = el("div", undefined, "artifact");
      const meta = el("div", undefined, "artifact-meta");
      meta.append(
        el("span", `${item.name} · ${bytes(item.bytes)}`),
        el("code", item.sha256),
      );
      const link = el("a", "Download ↓");
      link.href = `/api/runs/${run.id}/artifacts/${item.id}`;
      link.download = "";
      row.append(meta, link);
      return row;
    }),
  );
  if (!run.artifacts.length)
    $("artifacts").append(
      el(
        "p",
        "Reports will appear as the driver writes them. Logs and failed outputs are retained locally.",
        "fine",
      ),
    );
  if (
    !previous ||
    previous.status !== run.status ||
    previous.stages.find((s) => s.status === "running")?.id !== current?.id
  )
    $("announce").textContent =
      `${status(run.status)}. ${current?.title || ""}`;
  if (run.error) error(run.error);
}
async function poll() {
  if (state.polling) return;
  state.polling = true;
  try {
    history(await api("/api/runs"));
    if (state.selected) render(await api(`/api/runs/${state.selected}`));
    connected(true);
  } catch (_) {
    connected(false);
  } finally {
    state.polling = false;
  }
}
$("launch-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (state.busy) return;
  state.busy = true;
  $("start").disabled = true;
  error("");
  try {
    const parameters = {};
    for (const [k, v] of new FormData(e.target))
      if (String(v)) parameters[k] = String(v);
    const run = await api("/api/runs", {
      workflow: state.workflow.id,
      parameters,
    });
    await openRun(run.id);
    await poll();
  } catch (e) {
    error(e.message);
  } finally {
    state.busy = false;
    $("start").disabled = false;
  }
});
$("cancel").addEventListener("click", async () => {
  if (!state.selected) return;
  $("cancel").disabled = true;
  try {
    render(await api(`/api/runs/${state.selected}/cancel`, {}));
  } catch (e) {
    error(e.message);
    $("cancel").disabled = false;
  }
});
$("new-run").addEventListener("click", () =>
  choose(state.workflow || state.info.workflows[0]),
);
$("refresh").addEventListener("click", poll);
const tabs = ["activity", "result", "artifacts"];
function selectTab(name) {
  for (const other of tabs) {
    const selected = other === name;
    $(other + "-tab").setAttribute("aria-selected", String(selected));
    $(other + "-tab").tabIndex = selected ? 0 : -1;
    $(other + "-panel").hidden = !selected;
    $(other + "-panel").tabIndex = 0;
  }
}
selectTab("activity");
for (const [index, name] of tabs.entries()) {
  $(name + "-tab").addEventListener("click", () => selectTab(name));
  $(name + "-tab").addEventListener("keydown", (event) => {
    const targets = {
      ArrowLeft: (index + tabs.length - 1) % tabs.length,
      ArrowRight: (index + 1) % tabs.length,
      Home: 0,
      End: tabs.length - 1,
    };
    if (!(event.key in targets)) return;
    event.preventDefault();
    const next = tabs[targets[event.key]];
    selectTab(next);
    $(next + "-tab").focus();
  });
}
$("download").addEventListener("click", () => {
  if (!state.run) return;
  const a = el("a");
  a.href = `/api/runs/${state.run.id}/receipt`;
  a.download = `hallmark-${state.run.id}.json`;
  a.click();
});
async function initialize() {
  try {
    state.info = await api("/api/info");
    connected(true);
    $("checkout").textContent = state.info.root;
    $("workflows").replaceChildren(
      ...state.info.workflows.map((w) => {
        const button = el("button", undefined, "workflow");
        button.type = "button";
        button.dataset.workflow = w.id;
        button.append(el("strong", w.title), el("small", w.scheme));
        button.addEventListener("click", () => choose(w));
        return button;
      }),
    );
    await choose(state.info.workflows[0]);
    await poll();
    setInterval(poll, 1000);
  } catch (e) {
    connected(false);
    error(
      `Cannot connect to the local controller: ${e.message}. Keep the server terminal open and reload this page.`,
    );
  }
}
initialize();

window.addEventListener("resize", () => {
  if (state.run) chart(state.run.samples);
});
