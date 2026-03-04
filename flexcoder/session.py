"""Interactive session management."""

from __future__ import annotations

from pathlib import Path

from .chatlog import ChatLogStore
from .config import ConfigStore
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

    def _assistant_reply(self, user_text: str) -> str:
        shell_cmd = parse_shell_tag(user_text)
        if shell_cmd:
            tool_output = run_shell(shell_cmd, Path.cwd())
            return f"i see\nTool output:\n{tool_output}"
        return "i see\nI am ready. Add a single tool tag at the end when you want to run a tool."

    def run(self) -> int:
        system_prompt = build_system_prompt(Path.cwd())
        self.log_store.append(self.log_path, "system", system_prompt)

        try:
            while True:
                render(self.settings, self.history[-12:])
                user_input = input("\n> ").strip()
                if not user_input:
                    continue
                self.log_store.append(self.log_path, "user", user_input)
                self.history.append(f"you: {user_input}")

                reply = self._assistant_reply(user_input)
                self.log_store.append(self.log_path, "assistant", reply)
                self.history.append(f"assistant: {reply}")
        except KeyboardInterrupt:
            print(EXIT_BANNER)
            return 0
