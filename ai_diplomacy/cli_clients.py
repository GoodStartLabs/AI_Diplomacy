"""Model providers that invoke the user's logged-in Claude Code or Codex CLI.

Each invocation is independent: game prompts already contain the appropriate
history and private diary. No CLI transcript reconstruction is required.
"""

import asyncio
import json
import math
import os
import shutil
import signal
import tempfile
import weakref
from typing import Dict, List, Tuple

from .clients import BaseModelClient
from .utils import generate_random_seed


_LIMITERS: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, Dict[int, asyncio.Semaphore]]" = weakref.WeakKeyDictionary()


class CliModelClient(BaseModelClient):
    provider = ""
    executable = ""
    login_command = ""

    def __init__(self, model_name, prompts_dir=None):
        # Preserve provider identity in logs and saved agent state.
        super().__init__(f"{self.provider}:{model_name}", prompts_dir=prompts_dir)
        self.cli_model = model_name
        self.binary = os.environ.get(f"AI_DIPLOMACY_{self.executable.upper()}_BIN", self.executable)
        self.timeout = float(os.environ.get("AI_DIPLOMACY_CLI_TIMEOUT_SECONDS", "300"))
        self.concurrency = int(os.environ.get("AI_DIPLOMACY_CLI_MAX_CONCURRENCY", "2"))
        if not math.isfinite(self.timeout) or self.timeout <= 0 or self.concurrency <= 0:
            raise ValueError("CLI timeout and maximum concurrency must be positive finite values.")

    def _environment(self) -> Dict[str, str]:
        env = os.environ.copy()
        # Do not let API credentials in the game's .env override CLI login.
        for name in (
            "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
            "OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "CLAUDECODE",
            "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY",
        ):
            env.pop(name, None)
        return env

    def _limiter(self):
        loop = asyncio.get_running_loop()
        limits = _LIMITERS.setdefault(loop, {})
        # Shared by both providers and all countries in this process.
        return limits.setdefault(self.concurrency, asyncio.Semaphore(self.concurrency))

    async def _stop(self, process: asyncio.subprocess.Process) -> None:
        def send(sig):
            try:
                if os.name == "posix":
                    os.killpg(process.pid, sig)
                elif process.returncode is None:
                    process.kill()
            except ProcessLookupError:
                pass

        send(signal.SIGTERM)
        if process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), 2)
            except asyncio.TimeoutError:
                send(signal.SIGKILL)
                await process.wait()
        if os.name == "posix":
            # A descendant may still own stdout/stderr after its direct parent
            # exits. Give the process group a short grace period, then ensure
            # the timeout/cancellation does not leave that descendant running.
            await asyncio.sleep(0.1)
            send(signal.SIGKILL)
        elif process.returncode is None:
            await process.wait()

    async def generate_response(self, prompt: str, temperature: float = 0.0, inject_random_seed: bool = True) -> str:
        binary = shutil.which(self.binary)
        if not binary:
            raise RuntimeError(
                f"{self.executable} CLI not found: {self.binary!r}. Install it and sign in before running the game."
            )
        system = self.system_prompt
        if inject_random_seed:
            system = f"{generate_random_seed()}\n\n{system}"
        async with self._limiter():
            # Avoid discovering the game's or another project's instructions.
            with tempfile.TemporaryDirectory(prefix="ai-diplomacy-cli-") as cwd:
                args, stdin = self._invocation(system, prompt)
                try:
                    process = await asyncio.create_subprocess_exec(
                        binary, *args, cwd=cwd, env=self._environment(),
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        start_new_session=(os.name == "posix"),
                    )
                except OSError as exc:
                    raise RuntimeError(f"Could not start {self.provider} ({binary}): {exc}") from exc
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(stdin.encode("utf-8")), self.timeout,
                    )
                except asyncio.TimeoutError as exc:
                    await self._stop(process)
                    raise RuntimeError(f"{self.provider} timed out after {self.timeout:g} seconds.") from exc
                except BaseException:
                    await self._stop(process)
                    raise
                output = stdout.decode("utf-8", errors="replace")
                if process.returncode:
                    diagnostic = stderr.decode("utf-8", errors="replace").strip() or output.strip()
                    lower_diagnostic = diagnostic.lower()
                    if any(marker in lower_diagnostic for marker in ("not logged in", "login required", "authentication", "unauthorized")):
                        diagnostic += f"\nSign in with `{self.login_command}` and retry."
                    raise RuntimeError(
                        f"{self.provider} exited with code {process.returncode}: {diagnostic[-2000:]}"
                    )
                return self._parse(output)


class ClaudeCliClient(CliModelClient):
    provider = "claude-cli"
    executable = "claude"
    login_command = "claude auth login"

    def _invocation(self, system: str, prompt: str) -> Tuple[List[str], str]:
        args = [
            "-p", "--output-format", "json", "--tools", "",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--safe-mode", "--no-session-persistence",
            "--permission-prompts", "none", "--system-prompt", system,
        ]
        if self.cli_model != "default":
            args += ["--model", self.cli_model]
        return args, prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"

    def _parse(self, output: str) -> str:
        try:
            result = json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError("claude-cli returned malformed JSON.") from exc
        if not isinstance(result, dict) or result.get("type") != "result":
            raise RuntimeError("claude-cli returned an unexpected response envelope.")
        if result.get("is_error") or result.get("subtype") != "success":
            raise RuntimeError(f"claude-cli failed: {result.get('result') or result.get('errors') or result.get('subtype')}")
        text = result.get("result")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("claude-cli returned an empty response.")
        return text.strip()


class CodexCliClient(CliModelClient):
    provider = "codex-cli"
    executable = "codex"
    login_command = "codex login"

    def _invocation(self, system: str, prompt: str) -> Tuple[List[str], str]:
        args = [
            "exec", "--json", "--ephemeral", "--skip-git-repo-check",
            "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only",
            "--color", "never",
            "-c", 'approval_policy="never"',
            "-c", "features.shell_tool=false", "-c", 'web_search="disabled"',
            "-c", "developer_instructions=" + json.dumps(system + "\n\nAnswer only the supplied Diplomacy task. Do not use tools."),
        ]
        if self.cli_model != "default":
            args += ["--model", self.cli_model]
        return args + ["-"], prompt + "\n\nPROVIDE YOUR RESPONSE BELOW:"

    def _parse(self, output: str) -> str:
        answer = None
        completed = False
        for line in output.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("codex-cli returned malformed JSONL.") from exc
            if not isinstance(event, dict):
                raise RuntimeError("codex-cli returned an unexpected event.")
            if event.get("type") in ("error", "turn.failed"):
                detail = event.get("error") or event.get("message") or "unknown error"
                if isinstance(detail, dict):
                    detail = detail.get("message") or json.dumps(detail, ensure_ascii=False)
                raise RuntimeError(f"codex-cli failed: {detail}")
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    answer = item.get("text")
            if event.get("type") == "turn.completed":
                completed = True
        if not completed or not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("codex-cli returned no completed text response.")
        return answer.strip()
