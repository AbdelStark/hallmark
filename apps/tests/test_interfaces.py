import asyncio
import os
import shutil
import sys
import threading
from pathlib import Path

import pytest

from hallmark_demo import engine
from hallmark_demo.client import Client
from hallmark_demo.server import DemoServer
from hallmark_demo.tui import Workbench


@pytest.fixture
def interface_server(root, monkeypatch):
    repo = Path(__file__).resolve().parents[2]
    target = root / "website/assets/fonts"
    target.mkdir(parents=True)
    for name in ("public-sans.woff2", "newsreader.woff2"):
        shutil.copyfile(repo / "website/assets/fonts" / name, target / name)
    shutil.copyfile(repo / "website/assets/mark.svg", target.parent / "mark.svg")
    fixture = root / "software.py"
    fixture.write_text(
        """import json,time
print('Checking fixture contracts',flush=True)
time.sleep(.3)
report=dict(schema_id='hallmark/conformance-report/1',scope='software-components',
            matched=156,mismatched=0,software_passed=True,all_required_executed=False)
print(json.dumps(report),flush=True)
"""
    )
    monkeypatch.setattr(
        engine,
        "plan",
        lambda *a: dict(command=[sys.executable, str(fixture)], paid=False, ceiling="0"),
    )
    monkeypatch.setattr(
        engine,
        "preflight",
        lambda *a: [dict(label="Fixture prerequisites", ok=True, detail="No proof claim")],
    )
    server = DemoServer(root, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()
    thread.join(2)


def test_terminal_keyboard_runs_workflow_and_reads_same_api(interface_server):
    async def exercise():
        app = Workbench(Client(interface_server.origin))
        async with app.run_test(size=(120, 42)) as pilot:
            await pilot.pause()
            app.query_one("#workflows").focus()
            await pilot.press("end", "enter")
            await pilot.pause()
            assert app.workflow["id"] == "conformance"
            app.query_one("#start").focus()
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause(0.1)
                await app.refresh_runs()
                if app.run_snapshot and app.run_snapshot["status"] == "succeeded":
                    break
            assert app.run_snapshot["status"] == "succeeded"
            assert app.run_snapshot["result"]["matched"] == 156
            assert (
                "no cryptographic proof" in str(app.query_one("#result-summary").render()).lower()
            )
            assert Client(interface_server.origin).get("/api/runs")[0]["id"] == app.selected
            await app.action_export()
            assert list((interface_server.manager.directory / app.selected).glob("receipt-*.json"))
            await pilot.press("n")
            await pilot.pause()
            assert app.query_one("#setup").display
            await pilot.press("q")

    asyncio.run(exercise())


def test_browser_launch_reconnect_results_and_mobile(interface_server):
    from playwright.sync_api import expect, sync_playwright

    chrome = Path(
        os.environ.get("HALLMARK_BROWSER")
        or shutil.which("google-chrome")
        or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )
    if not chrome.is_file():
        if os.environ.get("HALLMARK_REQUIRE_BROWSER") == "1":
            pytest.fail("HALLMARK_REQUIRE_BROWSER is set but no browser executable was found")
        pytest.skip("Set HALLMARK_BROWSER to an isolated QA browser executable")
    errors = []
    with sync_playwright() as driver:
        browser = driver.chromium.launch(executable_path=str(chrome), headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(interface_server.origin)
        for workflow in interface_server.manager.workflows:
            page.locator(f'button[data-workflow="{workflow}"]').click()
        page.locator('button[data-workflow="llm"]').click()
        expect(page.locator("#case-note")).to_contain_text("TinyLlama-1.1B")
        expect(page.locator("#param-max_cost")).to_have_value("2.50")
        page.locator('button[data-workflow="conformance"]').click()
        page.locator("#start").click()
        expect(page.locator("#run-status")).to_have_text("succeeded", timeout=10000)
        page.get_by_role("tab", name="Results").click()
        page.get_by_role("tab", name="Results").press("ArrowRight")
        expect(page.get_by_role("tab", name="Artifacts")).to_be_focused()
        page.get_by_role("tab", name="Artifacts").press("Home")
        expect(page.get_by_role("tab", name="Activity")).to_have_attribute("aria-selected", "true")
        page.get_by_role("tab", name="Results").click()
        assert page.get_by_text("Software checks passed", exact=True).is_visible()
        assert page.get_by_text("No cryptographic proof was generated.", exact=True).is_visible()
        key = interface_server.manager.list()[0]["id"]
        page.reload()
        page.locator(".history-item").first.click()
        assert interface_server.manager.list()[0]["id"] == key
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert page.locator("#new-run").is_visible()
        page.get_by_role("tab", name="Artifacts").click()
        with page.expect_download() as receipt:
            page.locator("#download").click()
        assert receipt.value.suggested_filename == f"hallmark-{key}.json"
        assert not errors
        browser.close()


def test_custom_workflow_fields_render_without_client_changes(interface_server):
    from dataclasses import replace

    from hallmark_demo.catalog import Parameter

    interface_server.manager.workflows = dict(interface_server.manager.workflows)
    current = interface_server.manager.workflows["conformance"]
    interface_server.manager.workflows["conformance"] = replace(
        current, fields=(Parameter("note", "Operator note", default="example"),)
    )

    async def exercise():
        app = Workbench(Client(interface_server.origin))
        async with app.run_test(size=(80, 24)) as pilot:
            await app.show_setup("conformance")
            assert app.query_one("#param-note").value == "example"
            app.query_one("#start").focus()
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause(0.1)
                await app.refresh_runs()
                if app.run_snapshot and app.run_snapshot["status"] == "succeeded":
                    break
            assert app.run_snapshot["parameters"]["note"] == "example"
            assert app.query_one("#details").region.bottom <= app.size.height

    asyncio.run(exercise())
