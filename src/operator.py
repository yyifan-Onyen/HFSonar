"""Claude Code operator — subprocess wrapper around the `claude` CLI.

Pattern borrowed from AutoX-AI-Labs/AutoR's `src/operator.py`, simplified for our
use case: we don't need streaming or tool use, only single-shot prompt → text.

Two operators with the same interface:
- ClaudeOperator: shells out to `claude -p @<prompt-file> --output-format json`
- FakeOperator: deterministic stub for tests / token-free dev runs
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class OperatorResult:
    text: str
    raw: dict | None = None


class Operator(Protocol):
    def run(self, prompt_path: Path, *, label: str = "") -> OperatorResult: ...


class ClaudeOperator:
    """Real Claude Code CLI invocation."""

    def __init__(
        self,
        binary: str = "claude",
        timeout: float = 180.0,
        model: str = "",
    ) -> None:
        self.binary = binary
        self.timeout = timeout
        self.model = model

    def _resolve_binary(self) -> str:
        resolved = shutil.which(self.binary)
        if not resolved:
            raise FileNotFoundError(
                f"Could not find `{self.binary}` on PATH. "
                "Either install Claude Code or use --fake-llm."
            )
        return resolved

    def run(self, prompt_path: Path, *, label: str = "") -> OperatorResult:
        binary = self._resolve_binary()
        prompt_path = prompt_path.resolve()
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        cmd = [binary, "-p", f"@{prompt_path}", "--output-format", "json"]
        if self.model:
            cmd += ["--model", self.model]

        logger.info("[%s] invoking claude: %s", label or prompt_path.name, " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"claude CLI timed out after {self.timeout}s") from e

        if proc.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited {proc.returncode}\n"
                f"stderr:\n{proc.stderr.strip()[:2000]}"
            )

        stdout = proc.stdout.strip()
        # `--output-format json` returns a single JSON object with `result` + meta.
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            # Fallback: treat raw stdout as the answer.
            return OperatorResult(text=stdout, raw=None)

        text = ""
        if isinstance(payload, dict):
            # Newer CLI shape
            text = payload.get("result") or payload.get("response") or ""
            if not text and "messages" in payload:
                # Some versions nest the assistant text in messages[-1].content[0].text
                msgs = payload.get("messages") or []
                if msgs and isinstance(msgs[-1], dict):
                    content = msgs[-1].get("content")
                    if isinstance(content, list) and content:
                        first = content[0]
                        if isinstance(first, dict):
                            text = first.get("text") or ""
                    elif isinstance(content, str):
                        text = content
        return OperatorResult(text=text or stdout, raw=payload if isinstance(payload, dict) else None)


class FakeOperator:
    """Deterministic stub. Reads the prompt and emits a canned response derived
    from the prompt's section markers, so the orchestrator and tests can run end-to-end
    with zero token spend.
    """

    def run(self, prompt_path: Path, *, label: str = "") -> OperatorResult:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        if "[ROLE: CURATOR]" in prompt_text:
            return OperatorResult(text=self._fake_curate(prompt_text))
        if "[ROLE: WRITER]" in prompt_text:
            return OperatorResult(text=self._fake_write(prompt_text))
        return OperatorResult(text="[fake-llm]")

    @staticmethod
    def _fake_curate(prompt: str) -> str:
        # Pick the first up-to-3 candidate IDs we can find in the prompt.
        import re

        ids = re.findall(r"^- id: (.+)$", prompt, flags=re.MULTILINE)
        chosen = ids[:3]
        items = [
            {"event_dedup_key": k, "angle": "fake angle for smoke testing"}
            for k in chosen
        ]
        return json.dumps({"chosen": items}, ensure_ascii=False)

    @staticmethod
    def _fake_write(prompt: str) -> str:
        title_match = None
        for line in prompt.splitlines():
            if line.startswith("title:"):
                title_match = line[len("title:") :].strip()
                break
        title = title_match or "Untitled"
        return (
            f"# {title}\n\n"
            "*(fake-llm draft — set --fake-llm=false to invoke real Claude)*\n\n"
            "- Why it matters: placeholder.\n"
            "- What it is: placeholder.\n"
            "- Where to look: placeholder URL.\n"
        )
