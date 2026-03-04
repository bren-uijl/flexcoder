"""Interactive session management."""

from __future__ import annotations

import json
from pathlib import Path

from .chatlog import ChatLogStore
from .config import ConfigStore
from .llm_client import LLMError, provider_chat
from .system_prompt import build_system_prompt
from .tools import parse_shell_tag, run_shell
from .ui import EXIT_BANNER, render


class Session:
    """Run an interactive terminal chat session."""

    def __init__(self, resume_file: Path | None = None) -> None:
        self.log_store = ChatLogStore()
        self.config_store = ConfigStore()
        self.settings = self.config_store.load()
        self.log_path = resume_file or self.log_store.create_session_path()
        self.history: list[str] = []
        self.messages: list[dict[str, str]] = []

        if resume_file and resume_file.exists():
            self._load_session(resume_file)

    def _load_session(self, path: Path) -> None:
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            role = row.get("role", "")
            content = row.get("content", "")
            if role in {"system", "user", "assistant"}:
                self.messages.append({"role": role, "content": content})
            if role in {"user", "assistant"}:
                label = "you" if role == "user" else "assistant"
                self.history.append(f"{label}: {content}")

    def _assistant_reply(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        raw_reply = provider_chat(self.messages, self.settings).strip()
        if not raw_reply.lower().startswith("i see"):
            raw_reply = f"i see\n{raw_reply}"

        shell_cmd = parse_shell_tag(raw_reply)
        if shell_cmd:
            tool_output = run_shell(shell_cmd, Path.cwd())
            reply = f"{raw_reply}\n\nTool output:\n{tool_output}"
        else:
            reply = raw_reply

        self.messages.append({"role": "assistant", "content": reply})
        return reply

    def run(self) -> int:
        if not self.messages:
            system_prompt = build_system_prompt(Path.cwd())
            self.messages.append({"role": "system", "content": system_prompt})
            self.log_store.append(self.log_path, "system", system_prompt)

        try:
            while True:
                render(self.settings, self.history[-12:])
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                self.log_store.append(self.log_path, "user", user_input)
                self.history.append(f"you: {user_input}")

                try:
                    reply = self._assistant_reply(user_input)
                except LLMError as error:
                    reply = f"i see\nProvider error: {error}"
                    self.messages.append({"role": "assistant", "content": reply})

                self.log_store.append(self.log_path, "assistant", reply)
                self.history.append(f"assistant: {reply}")
        except KeyboardInterrupt:
            print(EXIT_BANNER)
            return 0
