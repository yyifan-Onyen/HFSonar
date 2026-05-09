"""Claude Code operator — subprocess wrapper around the `claude` CLI.

Single-shot prompt → text. Two implementations:
- ClaudeOperator: shells out to `claude -p @<prompt-file> --output-format json`
  Optional tools= list lets a step (e.g. author research) use WebFetch / WebSearch.
- FakeOperator: deterministic stub for tests / token-free dev runs.
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
    def run(
        self,
        prompt_path: Path,
        *,
        label: str = "",
        tools: list[str] | None = None,
    ) -> OperatorResult: ...


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

    def run(
        self,
        prompt_path: Path,
        *,
        label: str = "",
        tools: list[str] | None = None,
    ) -> OperatorResult:
        binary = self._resolve_binary()
        prompt_path = prompt_path.resolve()
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        cmd = [binary, "-p", f"@{prompt_path}", "--output-format", "json"]
        if self.model:
            cmd += ["--model", self.model]
        if tools:
            # Whitelist only the requested tools for this call. The CLI accepts a
            # comma-separated list via --allowedTools.
            cmd += ["--allowedTools", ",".join(tools)]

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
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return OperatorResult(text=stdout, raw=None)

        text = ""
        if isinstance(payload, dict):
            text = payload.get("result") or payload.get("response") or ""
            if not text and "messages" in payload:
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
    from the prompt's role marker, so the orchestrator and tests can run end-to-end
    with zero token spend.
    """

    def run(
        self,
        prompt_path: Path,
        *,
        label: str = "",
        tools: list[str] | None = None,
    ) -> OperatorResult:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        if "[ROLE: CURATOR]" in prompt_text:
            return OperatorResult(text=self._fake_curate(prompt_text))
        if "[ROLE: RESEARCHER]" in prompt_text:
            return OperatorResult(text=self._fake_research(prompt_text))
        if "[ROLE: OUTREACH_DRAFTER]" in prompt_text:
            return OperatorResult(text=self._fake_outreach(prompt_text))
        return OperatorResult(text="[fake-llm]")

    @staticmethod
    def _fake_curate(prompt: str) -> str:
        import re

        ids = re.findall(r"^- id: (.+)$", prompt, flags=re.MULTILINE)
        chosen = ids[:3]
        items = [
            {
                "event_dedup_key": k,
                "angle": "fake angle for smoke testing — would ask about specific design choice",
            }
            for k in chosen
        ]
        return json.dumps({"chosen": items}, ensure_ascii=False)

    @staticmethod
    def _fake_research(prompt: str) -> str:
        # Pull the AUTHOR field from the prompt to make the fake output look plausible.
        import re

        m = re.search(r"^author / org \(from HF metadata\): (.+)$", prompt, flags=re.MULTILINE)
        author_field = (m.group(1).strip() if m else "unknown") or "unknown"
        return json.dumps(
            {
                "primary_author": {
                    "name": author_field or "Unknown",
                    "role": "model_owner",
                    "affiliation": "",
                    "email": "",
                    "twitter": "",
                    "github": "",
                    "linkedin": "",
                    "website": "",
                    "huggingface": f"https://huggingface.co/{author_field}",
                    "confidence": "name_only",
                },
                "coauthors": [],
                "notes": "fake-llm: no real research performed; only HF profile URL inferred from author field.",
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _fake_outreach(prompt: str) -> str:
        return (
            "**Channel:** email\n\n"
            "**To:** <recipient name>\n\n"
            "**Subject:** Loved your work on <topic>\n\n"
            "---\n\n"
            "*(fake-llm draft — set --fake-llm=false to invoke real Claude.)*\n\n"
            "<First sentence: hook from curator's angle.>\n\n"
            "<Body: one observation or question.>\n\n"
            "<Ask: would you be open to a short async exchange?>\n\n"
            "Best,\n"
            "<your name>\n"
        )
