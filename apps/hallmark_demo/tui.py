"""Terminal client for the same local API used by the web app."""

import asyncio
import json
import time
import webbrowser
from pathlib import Path

from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Input,
    Label,
    OptionList,
    RichLog,
    Sparkline,
    Static,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

ACTIVE = {"starting", "running", "cancelling", "detached"}


def status_label(value):
    return ("running · reattached" if value == "detached" else value).upper()


def elapsed(seconds):
    return f"{int(seconds) // 60}m {int(seconds) % 60:02d}s"


def memory(value):
    return f"{value / 1024**3:.2f} GiB" if value >= 1024**3 else f"{value / 1024**2:.1f} MiB"


class QuitRun(ModalScreen[bool]):
    def compose(self):
        with Vertical(id="quit-dialog"):
            yield Label("Stop the active run and quit?")
            yield Static("The driver will be asked to clean up workers and retain its evidence.")
            with Horizontal():
                yield Button("Keep running", id="keep", variant="primary")
                yield Button("Stop and quit", id="quit-run", variant="error")

    @on(Button.Pressed)
    def pressed(self, event):
        self.dismiss(event.button.id == "quit-run")


class Workbench(App):
    TITLE = "Hallmark · Proof workbench"
    BINDINGS = [
        Binding("r", "start", "Run"),
        Binding("s", "stop", "Stop"),
        Binding("n", "setup", "New run"),
        Binding("w", "web", "Open web"),
        Binding("e", "export", "Export"),
        Binding("q", "quit_safely", "Quit"),
    ]
    CSS = """
    Screen { background: #f6f4ed; color: #203c35; }
    #masthead { width: 100%; height: 3; background: #203c35; color: #f6f4ed;
                padding: 1 2; text-style: bold; }
    #body { height: 1fr; }
    #sidebar { width: 28; border-right: solid #c9d0bf; padding: 1; }
    .section-label { color: #5c6b5a; text-style: bold; height: 2; margin-top: 1; }
    OptionList { background: #f6f4ed; color: #203c35; border: none; padding: 0;
                 height: auto; max-height: 13; }
    OptionList > .option-list--highlighted { background: #203c35; color: #f6f4ed; }
    #history { height: 1fr; max-height: 100%; }
    #content { width: 1fr; padding: 1 2; }
    #heading { text-style: bold; height: auto; margin-bottom: 1; }
    #overview { height: auto; margin-bottom: 1; }
    #prerequisites { height: auto; margin-bottom: 1; }
    #fields { height: auto; }
    #fields Label { height: 1; margin-top: 1; }
    Input, Select { margin-bottom: 1; background: #eeeee3; color: #203c35; border: solid #8b9b83; }
    SelectCurrent { background: #eeeee3; color: #203c35; }
    #setup-actions { height: 3; margin-top: 1; }
    Button { margin-right: 1; border: none; background: #203c35; color: #f6f4ed; }
    Button.-error { background: #a0442c; }
    #status { height: auto; min-height: 2; padding: 0 0 1 0; text-style: bold; }
    #stages { height: auto; max-height: 10; margin-bottom: 1; }
    DataTable { background: #f6f4ed; color: #203c35; }
    DataTable > .datatable--header { background: #e1e7d8; color: #203c35; text-style: bold; }
    #resources { height: 2; color: #5c6b5a; }
    #memory { height: 3; color: #32633f; background: #eeeee3; margin-bottom: 1; }
    #details { height: 1fr; min-height: 9; }
    TabPane { padding: 1 0; }
    ContentSwitcher { height: 1fr; }
    RichLog { background: #eeeee3; color: #203c35; padding: 0 1; height: 1fr; }
    #result { height: auto; }
    #artifact-list { height: auto; }
    #notice { height: auto; color: #973e2a; }
    Footer { background: #203c35; color: #f6f4ed; }
    #quit-dialog { width: 64; height: auto; padding: 2; border: solid #a0442c;
                   background: #f6f4ed; }
    QuitRun { align: center middle; background: #203c3580; }
    #quit-dialog Label { text-style: bold; margin-bottom: 1; }
    #quit-dialog Horizontal { height: 3; margin-top: 1; }
    """

    def __init__(self, client, *, owns_server=False):
        super().__init__()
        self.client = client
        self.owns_server = owns_server
        self.workflows = {w["id"]: w for w in client.info["workflows"]}
        self.workflow = next(iter(self.workflows.values()))
        self.selected = None
        self.run_snapshot = None
        self.runs = []
        self.last_seq = 0
        self.polling = False
        self.starting = False
        self.history_keys = []
        self.theme = "textual-light"

    def compose(self) -> ComposeResult:
        yield Label("H  HALLMARK   /   PROOF WORKBENCH", id="masthead")
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield Label("WORKFLOWS", classes="section-label")
                yield OptionList(
                    *(Option(w["title"], id=w["id"]) for w in self.workflows.values()),
                    id="workflows",
                )
                yield Label("RUN HISTORY", classes="section-label")
                yield OptionList(id="history")
            with Vertical(id="content"):
                yield Label("", id="heading")
                yield Static("", id="notice", markup=False)
                with VerticalScroll(id="setup"):
                    yield Static("", id="overview", markup=False)
                    yield Static("", id="prerequisites", markup=False)
                    yield Vertical(id="fields")
                    with Horizontal(id="setup-actions"):
                        yield Button("Start workflow", id="start")
                        yield Button("Workflow guide ↗", id="guide")
                with Vertical(id="monitor"):
                    yield Static("", id="status", markup=False)
                    with TabbedContent(id="details"):
                        with TabPane("Progress", id="progress-tab"):
                            with VerticalScroll():
                                yield DataTable(id="stages", cursor_type="none")
                                yield Static("", id="resources", markup=False)
                                yield Sparkline([], id="memory", summary_function=max)
                        with TabPane("Activity", id="activity-tab"):
                            yield RichLog(
                                id="activity",
                                wrap=True,
                                markup=False,
                                highlight=False,
                                max_lines=500,
                            )
                        with TabPane("Results", id="results-tab"):
                            with VerticalScroll():
                                yield Static("", id="result-summary", markup=False)
                                yield Static("", id="case-verdicts")
                                yield Collapsible(
                                    Static("", id="result", markup=False),
                                    title="Full driver result",
                                    collapsed=True,
                                )
                        with TabPane("Artifacts", id="artifacts-tab"):
                            with VerticalScroll():
                                yield Static("", id="artifact-list", markup=False)
        yield Footer()

    async def on_mount(self):
        self.query_one("#monitor").display = False
        self.query_one("#stages", DataTable).add_columns("Stage", "Observed status")
        await self.show_setup(self.workflow["id"])
        await self.refresh_runs()
        self.set_interval(1, self.refresh_runs)

    async def show_setup(self, workflow_id):
        self.workflow = self.workflows[workflow_id]
        self.selected = None
        self.run_snapshot = None
        self.query_one("#setup").display = True
        self.query_one("#monitor").display = False
        self.query_one("#heading", Label).update(self.workflow["title"])
        self.query_one("#notice", Static).update("")
        w = self.workflow
        cost = (
            f"Paid HF execution: ${w['paid_ceiling']} ceiling"
            if w["paid_ceiling"]
            else "Local execution · no cloud charge"
        )
        self.query_one("#overview", Static).update(
            f"{w['summary']}\n\n{w['scheme']}\n{w['claim']}\n\n{cost} · {w['duration']}"
            + (
                f"\n\n{w['example']['title']}\nPrompt: {w['example']['prompt']}\n"
                f"Response: {w['example']['response']}\n{w['example']['note']}"
                if w.get("example")
                else ""
            )
        )
        fields = self.query_one("#fields", Vertical)
        await fields.remove_children()
        for spec in w["fields"]:
            await fields.mount(Label(spec["label"]))
            await fields.mount(
                Input(
                    value=spec["default"],
                    placeholder="runs/…" if spec["kind"] == "retained" else "",
                    id="param-" + spec["name"],
                    disabled=spec["read_only"],
                )
            )
            if spec["hint"]:
                await fields.mount(Static(spec["hint"], markup=False))
        self.query_one("#start", Button).disabled = True
        try:
            checks = await asyncio.to_thread(self.client.get, "/api/checks/" + workflow_id)
            if self.workflow["id"] != workflow_id or self.selected:
                return
            self.query_one("#prerequisites", Static).update(
                "\n".join(
                    ("✓ " if c["ok"] else "× ") + c["label"] + " · " + c["detail"] for c in checks
                )
            )
            self.query_one("#start", Button).disabled = any(not c["ok"] for c in checks)
        except (OSError, ValueError) as error:
            self.query_one("#notice", Static).update(str(error))

    @on(OptionList.OptionSelected, "#workflows")
    async def selected_workflow(self, event):
        await self.show_setup(event.option.id)

    @on(OptionList.OptionSelected, "#history")
    async def selected_history(self, event):
        self.selected = event.option.id
        self.last_seq = 0
        self.query_one("#activity", RichLog).clear()
        await self.refresh_runs()

    @on(Button.Pressed, "#start")
    async def start_button(self):
        await self.action_start()

    async def action_start(self):
        if self.starting or self.selected:
            return
        self.starting = True
        parameters = {}
        for spec in self.workflow["fields"]:
            name = spec["name"]
            widget = self.query_one("#param-" + name)
            value = widget.value
            if value:
                parameters[name] = str(value)
        try:
            run = await asyncio.to_thread(self.client.start, self.workflow["id"], parameters)
            self.selected = run["id"]
            self.last_seq = 0
            self.query_one("#activity", RichLog).clear()
            self.render_run(run)
            await self.refresh_runs()
        except (OSError, ValueError) as error:
            self.query_one("#notice", Static).update(str(error))
        finally:
            self.starting = False

    async def action_stop(self):
        if self.selected and self.run_snapshot and self.run_snapshot["status"] in ACTIVE:
            try:
                self.render_run(await asyncio.to_thread(self.client.cancel, self.selected))
            except (OSError, ValueError) as error:
                self.query_one("#notice", Static).update(str(error))

    async def action_setup(self):
        await self.show_setup(self.workflow["id"])

    async def action_export(self):
        if not self.selected:
            self.notify("Select a run first")
            return
        try:
            receipt = await asyncio.to_thread(self.client.get, f"/api/runs/{self.selected}/receipt")
            directory = Path(self.client.info["root"]) / "runs/workbench" / self.selected
            if directory.is_symlink():
                raise ValueError("Unsafe export directory")
            destination = directory / f"receipt-{time.time_ns()}.json"
            with destination.open("x") as stream:
                json.dump(receipt, stream, indent=2)
            destination.chmod(0o600)
            self.notify("Saved " + str(destination), timeout=10)
        except (OSError, ValueError) as error:
            self.query_one("#notice", Static).update(str(error))

    def action_web(self):
        webbrowser.open(self.client.origin)

    @on(Button.Pressed, "#guide")
    def guide(self):
        webbrowser.open("https://github.com/AbdelStark/hallmark/blob/main/" + self.workflow["docs"])

    def action_quit_safely(self):
        if self.owns_server and any(r["status"] in ACTIVE for r in self.runs):
            self.push_screen(QuitRun(), lambda confirmed: self.exit() if confirmed else None)
        else:
            self.exit()

    async def refresh_runs(self):
        if self.polling:
            return
        self.polling = True
        try:
            self.runs = await asyncio.to_thread(self.client.get, "/api/runs")
            keys = [(r["id"], r["status"]) for r in self.runs]
            if keys != self.history_keys:
                history = self.query_one("#history", OptionList)
                history.clear_options()
                history.add_options(
                    Option(f"{r['title']}\n{r['status'].replace('_', ' ')} · {r['id']}", id=r["id"])
                    for r in self.runs
                )
                self.history_keys = keys
            if self.selected:
                run = await asyncio.to_thread(self.client.get, "/api/runs/" + self.selected)
                self.render_run(run)
        except (OSError, ValueError) as error:
            self.query_one("#notice", Static).update(
                "Disconnected; retrying the same controller. " + str(error)
            )
        finally:
            self.polling = False

    def render_run(self, run):
        if self.selected != run["id"]:
            return
        self.run_snapshot = run
        self.workflow = self.workflows[run["workflow"]]
        self.query_one("#setup").display = False
        self.query_one("#monitor").display = True
        self.query_one("#heading", Label).update(run["title"] + " · " + run["id"])
        self.query_one("#notice", Static).update(run["error"] or "")
        current = next((s["title"] for s in run["stages"] if s["status"] == "running"), "")
        self.query_one("#status", Static).update(
            f"{status_label(run['status'])}   {elapsed(run['elapsed_seconds'])}   {current}"
        )
        stages = self.query_one("#stages", DataTable)
        stages.clear()
        for stage in run["stages"]:
            stages.add_row(stage["title"], stage["status"])
        samples = run["samples"]
        if samples:
            last = samples[-1]
            cpu = f"{last['cpu_percent']:.0f}%" if last["cpu_percent"] is not None else "—"
            self.query_one("#resources", Static).update(
                f"LOCAL {'RSS' if run['status'] in ACTIVE else 'LAST RSS'} "
                f"{memory(last['rss_bytes'])}   "
                f"PEAK {memory(run['local_peak_rss'])}   CPU {cpu}   "
                f"{last['processes']} processes"
            )
            self.query_one("#memory", Sparkline).data = [s["rss_bytes"] for s in samples]
        log = self.query_one("#activity", RichLog)
        for event in run["events"]:
            if event["seq"] > self.last_seq:
                log.write(Text(event["time"][11:19] + " UTC  " + event["message"]))
        self.last_seq = run["next_seq"] - 1
        if run.get("summary"):
            summary = run["summary"]
            facts = []
            for metric in summary["metrics"]:
                value = (
                    f"${metric['value']:.4f}" if metric["unit"] == "USD" else str(metric["value"])
                )
                facts.append(metric["label"] + ": " + value)
            headline = summary["title"].upper() + "\n" + summary["note"]
            self.query_one("#result-summary", Static).update(headline + "\n\n" + "\n".join(facts))
            table = Table(box=None, expand=True)
            if summary["cases"]:
                for title in ("Request", "Rule", "MLP", "CNN", "All-pass policy"):
                    table.add_column(title)
                for case in summary["cases"]:
                    table.add_row(
                        case["name"],
                        *(
                            Text("PASS" if v else "BLOCK", style="green" if v else "red")
                            for v in case["verdicts"]
                        ),
                        "RELEASE" if case["release"] else "BLOCK",
                    )
            elif summary["measurements"]:
                for title in ("Backend", "Proving", "Commands", "Host RSS", "GPU peak"):
                    table.add_column(title)
                for row in summary["measurements"]:
                    table.add_row(
                        row["backend"].upper(),
                        f"{row['prove_seconds']:.2f}s",
                        f"{row['commands_seconds']:.2f}s",
                        memory(row["sampled_peak_rss_bytes"]),
                        memory(row["gpu_peak_memory_mib"] * 1024**2),
                    )
            self.query_one("#case-verdicts", Static).update(table if table.columns else "")
            self.query_one("#result", Static).update(json.dumps(run["result"], indent=2))
        else:
            self.query_one("#result-summary", Static).update(
                run["error"] or "Waiting for the driver’s final verification and binding checks."
            )
            self.query_one("#case-verdicts", Static).update("")
            self.query_one("#result", Static).update("")
        self.query_one("#artifact-list", Static).update(
            (run["output"] or "Evidence directory not yet created")
            + "\n\n"
            + "\n\n".join(
                f"{a['name']} · {memory(a['bytes'])}\nSHA-256 {a['sha256']}\n"
                f"{self.client.origin}/api/runs/{run['id']}/artifacts/{a['id']}"
                for a in run["artifacts"]
            )
        )
