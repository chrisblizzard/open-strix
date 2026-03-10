"""Tests for the run_in_background tool and helpers."""

from __future__ import annotations

import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from typing import Any

import pytest

import open_strix.app as app_mod
from open_strix.tools import (
    _background_shell_command,
    _notify_event_queue,
)


class DummyAgent:
    async def ainvoke(self, _: dict[str, Any]) -> dict[str, Any]:
        return {"messages": []}


def _stub_agent_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(app_mod, "create_deep_agent", lambda **_: DummyAgent())


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name == "nt", reason="bash-specific test")
def test_background_shell_command_bash() -> None:
    argv = _background_shell_command("cargo build", "/tmp/out.log")
    assert argv[0] == "bash"
    assert "-lc" in argv
    script = argv[-1]
    assert "cargo build" in script
    assert '| tee "/tmp/out.log"' in script
    assert "PIPESTATUS" in script
    assert "EXIT_CODE=" in script


@pytest.mark.skipif(os.name != "nt", reason="powershell-specific test")
def test_background_shell_command_powershell() -> None:
    argv = _background_shell_command("cargo build", "C:\\tmp\\out.log")
    assert argv[0] == "powershell"
    assert "Tee-Object" in " ".join(argv)
    assert "EXIT_CODE=" in " ".join(argv)


def test_notify_event_queue_posts_json() -> None:
    """Verify _notify_event_queue sends a valid POST with expected payload."""
    received: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            received.append(body)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"queued"}')

        def log_message(self, *_: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    _notify_event_queue(port, "test prompt", "test-source")
    t.join(timeout=5)
    server.server_close()

    assert len(received) == 1
    assert received[0]["prompt"] == "test prompt"
    assert received[0]["source"] == "test-source"


def test_notify_event_queue_silences_errors() -> None:
    """Calling with a bogus port should not raise."""
    _notify_event_queue(1, "nope", "bad")  # port 1 will fail to connect


# ---------------------------------------------------------------------------
# Integration tests for the run_in_background tool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_returns_immediately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    tools = {tool.name: tool for tool in app._build_tools()}

    result = await tools["run_in_background"].ainvoke({
        "command": "echo hello-bg",
        "label": "echo-test",
    })

    assert "Background job launched" in result
    assert "pid=" in result
    assert "bg-" in result
    assert "echo-test" in result
    assert "output_file" in result.lower() or "Output file" in result

    # Give the background process a moment to finish and write
    await asyncio.sleep(1)

    # Verify the output file was created and contains our output
    log_dir = tmp_path / "logs"
    bg_logs = list(log_dir.glob("bg-*-echo-test.log"))
    assert len(bg_logs) == 1

    content = bg_logs[0].read_text()
    assert "hello-bg" in content
    assert "EXIT_CODE=0" in content


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_captures_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    tools = {tool.name: tool for tool in app._build_tools()}

    await tools["run_in_background"].ainvoke({
        "command": "exit 42",
        "label": "exit-test",
    })

    await asyncio.sleep(1)

    log_dir = tmp_path / "logs"
    bg_logs = list(log_dir.glob("bg-*-exit-test.log"))
    assert len(bg_logs) == 1

    content = bg_logs[0].read_text()
    assert "EXIT_CODE=42" in content


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_captures_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    tools = {tool.name: tool for tool in app._build_tools()}

    await tools["run_in_background"].ainvoke({
        "command": "echo out-msg && echo err-msg >&2",
        "label": "stderr-test",
    })

    await asyncio.sleep(1)

    log_dir = tmp_path / "logs"
    bg_logs = list(log_dir.glob("bg-*-stderr-test.log"))
    assert len(bg_logs) == 1

    content = bg_logs[0].read_text()
    # Both stdout and stderr should be captured (2>&1 in the wrapper)
    assert "out-msg" in content
    assert "err-msg" in content


@pytest.mark.asyncio
async def test_run_in_background_empty_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    tools = {tool.name: tool for tool in app._build_tools()}

    result = await tools["run_in_background"].ainvoke({"command": "  "})
    assert "command is required" in result


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_notifies_event_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When api_port > 0, completion should POST to the event queue."""
    received: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            received.append(body)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"queued"}')

        def log_message(self, *_: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    # Run server in background to accept one request
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    app.config.api_port = port  # type: ignore[misc]
    tools = {tool.name: tool for tool in app._build_tools()}

    await tools["run_in_background"].ainvoke({
        "command": "echo notify-test",
        "label": "notify-test",
    })

    # Wait for background process + notification
    await asyncio.sleep(2)
    t.join(timeout=5)
    server.server_close()

    assert len(received) == 1
    assert "notify-test" in received[0]["prompt"]
    assert received[0]["source"] == "background-job:notify-test"


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_no_notification_without_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When api_port=0, the tool should say no callback will fire."""
    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    # Default api_port is 0
    tools = {tool.name: tool for tool in app._build_tools()}

    result = await tools["run_in_background"].ainvoke({
        "command": "echo no-api",
        "label": "no-api",
    })

    assert "api_port=0" in result or "no callback" in result.lower() or "No loopback API" in result


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_custom_notify_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Custom notify_prompt should be forwarded to the event queue."""
    received: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            received.append(body)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"status":"queued"}')

        def log_message(self, *_: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    t = threading.Thread(target=server.handle_request, daemon=True)
    t.start()

    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    app.config.api_port = port  # type: ignore[misc]
    tools = {tool.name: tool for tool in app._build_tools()}

    await tools["run_in_background"].ainvoke({
        "command": "echo custom",
        "label": "custom-prompt",
        "notify_prompt": "Build succeeded! Deploy to staging.",
    })

    await asyncio.sleep(2)
    t.join(timeout=5)
    server.server_close()

    assert len(received) == 1
    assert received[0]["prompt"] == "Build succeeded! Deploy to staging."


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="bash execution test is Unix-only")
async def test_run_in_background_tool_is_registered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_in_background should appear in the tool list."""
    _stub_agent_factory(monkeypatch)
    app = app_mod.OpenStrixApp(tmp_path)
    tools = {tool.name: tool for tool in app._build_tools()}
    assert "run_in_background" in tools
