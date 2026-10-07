import asyncio
import json
import os
import stat
import textwrap
from types import SimpleNamespace

import pytest

from ai_diplomacy.cli_clients import ClaudeCliClient, CodexCliClient
from ai_diplomacy.clients import load_model_client
from ai_diplomacy.game_logic import deserialize_agent, serialize_agent


@pytest.fixture
def fake_cli(tmp_path):
    executable = tmp_path / "fake-model-cli"
    executable.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import fcntl
            import json
            import os
            import signal
            import sys
            import time

            prompt = sys.stdin.read()
            record_path = os.environ.get("FAKE_CLI_RECORD")
            if record_path:
                credentials = [
                    name for name in (
                        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                        "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "CLAUDECODE",
                        "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX",
                        "CLAUDE_CODE_USE_FOUNDRY",
                    ) if name in os.environ
                ]
                with open(record_path, "w", encoding="utf-8") as handle:
                    json.dump({"argv": sys.argv[1:], "prompt": prompt, "credentials": credentials}, handle)

            marker_path = os.environ.get("FAKE_CLI_SIGNAL_MARKER")
            def stopped(signum, frame):
                if marker_path:
                    with open(marker_path, "w", encoding="utf-8") as handle:
                        handle.write(str(signum))
                raise SystemExit(128 + signum)
            signal.signal(signal.SIGTERM, stopped)

            mode = os.environ.get("FAKE_CLI_MODE", "success")
            if mode == "sleep":
                time.sleep(30)
            if mode == "concurrency":
                state_path = os.environ["FAKE_CLI_STATE"]
                with open(state_path, "r+", encoding="utf-8") as handle:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                    state = json.load(handle)
                    state["active"] += 1
                    state["maximum"] = max(state["maximum"], state["active"])
                    handle.seek(0)
                    json.dump(state, handle)
                    handle.truncate()
                    fcntl.flock(handle, fcntl.LOCK_UN)
                time.sleep(0.2)
                with open(state_path, "r+", encoding="utf-8") as handle:
                    fcntl.flock(handle, fcntl.LOCK_EX)
                    state = json.load(handle)
                    state["active"] -= 1
                    handle.seek(0)
                    json.dump(state, handle)
                    handle.truncate()
                    fcntl.flock(handle, fcntl.LOCK_UN)
            if mode == "failure":
                print("deliberate diagnostic", file=sys.stderr)
                raise SystemExit(7)

            custom = os.environ.get("FAKE_CLI_OUTPUT")
            if custom is not None:
                print(custom)
            elif sys.argv[1:2] == ["exec"]:
                print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": " codex answer "}}))
                print(json.dumps({"type": "turn.completed"}))
            else:
                print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": " claude answer "}))
            """
        ),
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


@pytest.mark.parametrize(
    ("client_class", "binary_env", "model", "expected", "model_flag"),
    [
        (ClaudeCliClient, "AI_DIPLOMACY_CLAUDE_BIN", "sonnet", "claude answer", "--model"),
        (CodexCliClient, "AI_DIPLOMACY_CODEX_BIN", "gpt-5", "codex answer", "--model"),
    ],
)
def test_real_subprocess_preserves_prompt_arguments_and_removes_api_credentials(
    tmp_path, monkeypatch, fake_cli, client_class, binary_env, model, expected, model_flag
):
    record = tmp_path / "record.json"
    monkeypatch.setenv(binary_env, str(fake_cli))
    monkeypatch.setenv("FAKE_CLI_RECORD", str(record))
    for name in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
        "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "CLAUDECODE",
        "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
    ):
        monkeypatch.setenv(name, "must-not-leak")

    client = client_class(model)
    client.set_system_prompt("private system instructions")
    prompt = "Line one\nUnicode and shell text: 外交 $HOME `whoami`\nLine three"
    result = asyncio.run(client.generate_response(prompt, inject_random_seed=False))

    invocation = json.loads(record.read_text(encoding="utf-8"))
    assert result == expected
    assert invocation["prompt"] == prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"
    assert invocation["credentials"] == []
    assert invocation["argv"][invocation["argv"].index(model_flag) + 1] == model
    assert "private system instructions" in " ".join(invocation["argv"])


@pytest.mark.parametrize(
    ("client", "output", "message"),
    [
        (ClaudeCliClient("default"), "not-json", "malformed JSON"),
        (ClaudeCliClient("default"), json.dumps({"type": "assistant"}), "unexpected response envelope"),
        (ClaudeCliClient("default"), json.dumps({"type": "result", "subtype": "error", "is_error": True, "result": "bad turn"}), "bad turn"),
        (ClaudeCliClient("default"), json.dumps({"type": "result", "subtype": "success", "result": "  "}), "empty response"),
        (CodexCliClient("default"), "not-jsonl", "malformed JSONL"),
        (CodexCliClient("default"), json.dumps({"type": "turn.failed", "error": "bad turn"}), "bad turn"),
        (CodexCliClient("default"), json.dumps({"type": "turn.completed"}), "no completed text response"),
        (CodexCliClient("default"), json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "orphan"}}), "no completed text response"),
    ],
)
def test_response_parsing_rejects_malformed_empty_and_failed_turns(client, output, message):
    with pytest.raises(RuntimeError, match=message):
        client._parse(output)


def test_failed_cli_reports_exit_code_and_stderr(monkeypatch, fake_cli):
    monkeypatch.setenv("AI_DIPLOMACY_CLAUDE_BIN", str(fake_cli))
    monkeypatch.setenv("FAKE_CLI_MODE", "failure")

    with pytest.raises(RuntimeError, match="exited with code 7: deliberate diagnostic"):
        asyncio.run(ClaudeCliClient("default").generate_response("prompt", inject_random_seed=False))


def test_timeout_terminates_cli_process(tmp_path, monkeypatch, fake_cli):
    marker = tmp_path / "terminated"
    monkeypatch.setenv("AI_DIPLOMACY_CLAUDE_BIN", str(fake_cli))
    monkeypatch.setenv("AI_DIPLOMACY_CLI_TIMEOUT_SECONDS", "0.1")
    monkeypatch.setenv("FAKE_CLI_MODE", "sleep")
    monkeypatch.setenv("FAKE_CLI_SIGNAL_MARKER", str(marker))

    with pytest.raises(RuntimeError, match="timed out after 0.1 seconds"):
        asyncio.run(ClaudeCliClient("default").generate_response("prompt", inject_random_seed=False))
    assert marker.read_text(encoding="utf-8") == str(signal_number("SIGTERM"))


def signal_number(name):
    import signal
    return int(getattr(signal, name))


def test_cancellation_terminates_cli_process(tmp_path, monkeypatch, fake_cli):
    marker = tmp_path / "cancelled"
    monkeypatch.setenv("AI_DIPLOMACY_CODEX_BIN", str(fake_cli))
    monkeypatch.setenv("AI_DIPLOMACY_CLI_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("FAKE_CLI_MODE", "sleep")
    monkeypatch.setenv("FAKE_CLI_SIGNAL_MARKER", str(marker))

    async def cancel_running_call():
        task = asyncio.create_task(CodexCliClient("default").generate_response("prompt", inject_random_seed=False))
        await asyncio.sleep(0.1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_running_call())
    assert marker.exists()


def test_concurrency_limit_is_shared_across_cli_providers(tmp_path, monkeypatch, fake_cli):
    state_path = tmp_path / "state.json"
    state_path.write_text('{"active": 0, "maximum": 0}', encoding="utf-8")
    monkeypatch.setenv("AI_DIPLOMACY_CLAUDE_BIN", str(fake_cli))
    monkeypatch.setenv("AI_DIPLOMACY_CODEX_BIN", str(fake_cli))
    monkeypatch.setenv("AI_DIPLOMACY_CLI_MAX_CONCURRENCY", "2")
    monkeypatch.setenv("FAKE_CLI_MODE", "concurrency")
    monkeypatch.setenv("FAKE_CLI_STATE", str(state_path))

    async def run_calls():
        clients = [ClaudeCliClient("default"), CodexCliClient("default"), ClaudeCliClient("default"), CodexCliClient("default")]
        return await asyncio.gather(*(client.generate_response("prompt", inject_random_seed=False) for client in clients))

    assert asyncio.run(run_calls()) == ["claude answer", "codex answer", "claude answer", "codex answer"]
    assert json.loads(state_path.read_text(encoding="utf-8")) == {"active": 0, "maximum": 2}


@pytest.mark.parametrize(
    ("model_id", "client_class", "cli_model"),
    [
        ("claude-cli:default", ClaudeCliClient, "default"),
        ("claude-cli:sonnet", ClaudeCliClient, "sonnet"),
        ("codex-cli:default", CodexCliClient, "default"),
        ("codex-cli:gpt-5", CodexCliClient, "gpt-5"),
    ],
)
def test_factory_loads_cli_provider_and_preserves_qualified_identity(model_id, client_class, cli_model):
    client = load_model_client(model_id)
    assert isinstance(client, client_class)
    assert client.cli_model == cli_model
    assert client.model_name == model_id


@pytest.mark.parametrize("model_id", ["claude-cli:", "codex-cli:", "claude-cli:sonnet@host", "codex-cli:gpt-5#secret"])
def test_factory_rejects_missing_model_and_api_configuration(model_id):
    with pytest.raises(ValueError):
        load_model_client(model_id)


@pytest.mark.parametrize("model_id", ["claude-cli:sonnet", "codex-cli:gpt-5"])
def test_agent_serialize_deserialize_round_trip_preserves_cli_provider(model_id):
    original = SimpleNamespace(
        power_name="FRANCE",
        client=load_model_client(model_id),
        goals=["Secure Belgium"],
        relationships={"ENGLAND": "Friendly"},
        full_private_diary=["full entry"],
        private_diary=["summary"],
    )
    original.client.max_tokens = 1234

    restored = deserialize_agent(serialize_agent(original))

    assert restored.client.model_name == model_id
    assert type(restored.client) is type(original.client)
    assert restored.client.max_tokens == 1234
    assert restored.goals == original.goals
    assert restored.full_private_diary == original.full_private_diary
    assert restored.private_diary == original.private_diary


@pytest.mark.parametrize("name,value", [("AI_DIPLOMACY_CLI_TIMEOUT_SECONDS", "nan"), ("AI_DIPLOMACY_CLI_TIMEOUT_SECONDS", "0"), ("AI_DIPLOMACY_CLI_MAX_CONCURRENCY", "0")])
def test_invalid_cli_runtime_limits_are_rejected(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError, match="positive finite"):
        ClaudeCliClient("default")
