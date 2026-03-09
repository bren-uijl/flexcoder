"""screens/chat.py — flexcoder main TUI, opencode-inspired layout."""

from __future__ import annotations
import os
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Static, Input, RichLog, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual import work, on
from rich.text import Text
from rich.markup import escape as esc

from flexcoder import config as cfg_mod
from flexcoder import sessions as sess_mod
from flexcoder import providers as prov_mod
from flexcoder import ai as ai_mod
from flexcoder import tools as tools_mod
from flexcoder import system_prompt as sp_mod
from flexcoder.art import FLEXCODER, GOODBYE

from flexcoder.screens.help import HelpScreen
from flexcoder.screens.model_picker import ModelPickerScreen
from flexcoder.screens.session_browser import SessionBrowserScreen
from flexcoder.screens.provider_settings import ProviderSettingsScreen
from flexcoder.screens.ai_settings import AISettingsScreen

from flexcoder._css import CSS_PATH as _CSS


# ── Tool approval popup ───────────────────────────────────────────────────────

class ApprovalScreen(ModalScreen):
    BINDINGS = [
        Binding("enter",  "approve", "Approve"),
        Binding("escape", "deny",    "Deny"),
    ]

    def __init__(self, prompt: str):
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical(id="ap2-root"):
            yield Static("[bold yellow]Tool approval required[/bold yellow]", id="ap2-title")
            yield Static(esc(self._prompt), id="ap2-body")
            with Horizontal(id="ap2-footer"):
                yield Button("✔  Allow  [Enter]", id="btn-allow",  classes="btn-confirm")
                yield Button("✘  Deny   [Esc]",   id="btn-deny",   classes="btn-cancel")

    def on_button_pressed(self, e: Button.Pressed):
        self.dismiss(e.button.id == "btn-allow")

    def action_approve(self): self.dismiss(True)
    def action_deny(self):    self.dismiss(False)


# ── Main app ──────────────────────────────────────────────────────────────────

class FlexCoderApp(App):
    CSS_PATH = _CSS

    BINDINGS = [
        Binding("ctrl+a", "toggle_auto",   "Auto-approve", priority=True),
        Binding("ctrl+o", "toggle_output", "Output",       priority=True),
        Binding("ctrl+h", "show_help",     "Help",         priority=True),
        Binding("ctrl+n", "new_session",   "New",          priority=True),
        Binding("ctrl+s", "show_sessions", "Sessions",     priority=True),
        Binding("tab",    "show_picker",   "Switch model", priority=True),
        Binding("ctrl+p", "show_commands", "Commands",     priority=True),
        Binding("ctrl+e", "show_settings", "Settings",     priority=True),
        Binding("ctrl+t", "show_ai_cfg",   "AI settings",  priority=True),
        Binding("ctrl+l", "clear_chat",    "Clear",        priority=True),
        Binding("escape", "interrupt",     "Interrupt",    priority=True),
        Binding("ctrl+c", "quit_app",      "Quit",         priority=True),
    ]

    auto_approve: reactive = reactive(True)
    show_output:  reactive = reactive(False)

    def __init__(self, session_id: str | None = None):
        super().__init__()
        self._doc = cfg_mod.load()
        prov_mod._reload_custom(self._doc)

        self.auto_approve = bool(cfg_mod.get(self._doc, "general", "auto_approve") or True)
        self.show_output  = bool(cfg_mod.get(self._doc, "general", "show_output")  or False)

        self._session_id = session_id or sess_mod.new_id()
        self._messages:  list[dict] = []
        self._cwd = str(Path.cwd())
        if (Path(self._cwd) / "flexcoder").is_dir():
            self._cwd = str(Path.home())
        self._pending_tools: list[tuple[str, tuple]] = []

        if session_id:
            existing = sess_mod.load(session_id)
            if existing:
                self._messages = existing.get("messages", [])
                cfg_mod.set_val(self._doc, "general", "provider",
                                existing.get("provider", self._provider))
                cfg_mod.set_val(self._doc, "general", "model",
                                existing.get("model", self._model))
                self._cwd = existing.get("cwd", self._cwd)

        if (Path(self._cwd) / "flexcoder").is_dir():
            self._cwd = str(Path.home())

        self._warn_home = Path(self._cwd).resolve() == Path.home().resolve()
        models_exist = any(cfg_mod.get_models(self._doc, k) for k in prov_mod.PROVIDER_KEYS)
        self._first_run = not models_exist

    @property
    def _provider(self) -> str:
        return str(cfg_mod.get(self._doc, "general", "provider") or "ollama")

    @property
    def _model(self) -> str:
        return str(cfg_mod.get(self._doc, "general", "model") or "")

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical(id="fc-root"):
            # ASCII header
            with Horizontal(id="header-box"):
                with Vertical(id="header-ascii"):
                    for i, line in enumerate(FLEXCODER):
                        yield Static(line, id=f"ascii-{i}", classes="header-ascii")
                with Vertical(id="header-info"):
                    yield Static("", id="hdr-provider")
                    yield Static("", id="hdr-model")
                    yield Static("", id="hdr-flags")
            # Chat log fills remaining space
            yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
            # opencode-style input bar at the bottom
            with Vertical(id="input-area"):
                yield Input(
                    placeholder="What do you want to build?",
                    id="chat-input",
                )
                with Horizontal(id="status-bar"):
                    yield Static("", id="model-badge")
                    yield Static("[dim]tab[/dim] switch model  [dim]ctrl+p[/dim] commands", id="status-right")

    def on_mount(self):
        self._refresh_header()
        if self._warn_home:
            self._render("error", "Running in home directory — navigate to a project folder first.")
        if self._first_run:
            def _after_setup(result):
                if result:
                    self._doc = result
                    prov_mod._reload_custom(self._doc)
                    self._refresh_header()
                    self._render("info", "Provider configured. Press Tab to select a model.")
                else:
                    self._render("info", "Press Ctrl+E to configure a provider.")
            self.call_after_refresh(
                lambda: self.push_screen(ProviderSettingsScreen(self._doc, first_run=True), _after_setup)
            )
        elif not self._model:
            self._render("info", "No model selected — press Tab to pick one.")
        else:
            pinfo = prov_mod.PROVIDERS.get(self._provider, {})
            self._render("info", f"Session {self._session_id}  ·  cwd: {self._cwd}")

        if self._messages:
            self.query_one("#chat-log", RichLog).write(
                Text.from_markup(f"[dim]─── {len(self._messages)} messages resumed ───[/dim]\n"))
            for m in self._messages:
                self._render(m["role"], m["content"])

        self.query_one("#chat-input", Input).focus()

    # ── Header ────────────────────────────────────────────────────────────────

    def _refresh_header(self):
        pinfo = prov_mod.PROVIDERS.get(self._provider, {})
        c     = pinfo.get("color", "cyan")
        pname = pinfo.get("name", self._provider)
        model = self._model or "(none)"
        auto  = "[bold green]AUTO[/bold green]" if self.auto_approve else "[bold red]MANUAL[/bold red]"
        out   = "[bold yellow]OUT[/bold yellow]" if self.show_output  else "[bold dim]QUIET[/bold dim]"
        try:
            for i in range(5):
                self.query_one(f"#ascii-{i}", Static).update(f"[{c}]{FLEXCODER[i]}[/{c}]")
            self.query_one("#hdr-provider", Static).update(
                f"[dim]provider[/dim]  [{c}]{esc(pname)}[/{c}]")
            self.query_one("#hdr-model", Static).update(
                f"[dim]model    [/dim]  [{c}]{esc(model)}[/{c}]")
            self.query_one("#hdr-flags", Static).update(
                f"{auto}  {out}  [dim]{self._session_id}[/dim]")
            # bottom badge
            self.query_one("#model-badge", Static).update(
                f"[{c}]{esc(pname)}[/{c}]  [dim]{esc(model)}[/dim]")
        except Exception:
            pass

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self, role: str, content: str):
        log   = self.query_one("#chat-log", RichLog)
        pinfo = prov_mod.PROVIDERS.get(self._provider, {})
        c     = pinfo.get("color", "cyan")
        match role:
            case "user":
                log.write(Text.from_markup(f"[bold cyan]You[/bold cyan]  [dim]›[/dim]  {esc(content)}\n"))
            case "assistant":
                log.write(Text.from_markup(f"[bold {c}]AI[/bold {c}]   [dim]›[/dim]  {esc(content)}\n"))
            case "tool":
                if self.show_output:
                    log.write(Text.from_markup(f"[dim]{esc(content)}[/dim]\n"))
            case "tool_error":
                log.write(Text.from_markup(f"[bold red]✘ Tool[/bold red]  {esc(content)}\n"))
            case "info":
                log.write(Text.from_markup(f"[dim]{esc(content)}[/dim]\n"))
            case "error":
                log.write(Text.from_markup(f"[bold red]✘[/bold red]  [red]{esc(content)}[/red]\n"))

    def _set_status(self, msg: str, color: str = "dim"):
        try:
            self.query_one("#status-right", Static).update(
                f"[{color}]{esc(msg)}[/{color}]" if msg
                else "[dim]tab[/dim] switch model  [dim]ctrl+p[/dim] commands"
            )
        except Exception:
            pass

    # ── Input ─────────────────────────────────────────────────────────────────

    @on(Input.Submitted, "#chat-input")
    def on_input(self, e: Input.Submitted):
        text = e.value.strip()
        if not text:
            return
        self.query_one("#chat-input", Input).value = ""
        if text.startswith("/"):
            self._command(text)
            return
        if not self._model:
            self._render("error", "No model — press Tab to pick one.")
            return
        self._messages.append({"role": "user", "content": text})
        self._render("user", text)
        self._persist()
        self._set_status("thinking…", "yellow")
        self._call_ai()

    def _command(self, text: str):
        parts = text.split(maxsplit=1)
        cmd   = parts[0].lower()
        arg   = parts[1].strip() if len(parts) > 1 else ""
        match cmd:
            case "/help" | "/h":           self.action_show_help()
            case "/new":                   self.action_new_session()
            case "/sessions":              self.action_show_sessions()
            case "/settings":              self.action_show_settings()
            case "/model":                 self._switch_model(arg)
            case "/clear":                 self.action_clear_chat()
            case "/status":                self._show_status()
            case "/exit" | "/quit" | "/q": self.action_quit_app()
            case _:                        self._render("error", f"Unknown: {cmd}  (/help)")

    def _switch_model(self, model: str):
        pkey   = self._provider
        models = cfg_mod.get_models(self._doc, pkey)
        if not model:
            self._render("info", "Models: " + (", ".join(models) if models else "none — press Tab"))
            return
        cfg_mod.set_val(self._doc, "general", "model", model)
        cfg_mod.save(self._doc)
        self._refresh_header()
        self._render("info", f"Model → {model}")

    def _show_status(self):
        pinfo = prov_mod.PROVIDERS.get(self._provider, {})
        self._render("info",
            f"Provider: {pinfo.get('name', self._provider)}  Model: {self._model}  "
            f"Session: {self._session_id}  Auto: {self.auto_approve}  CWD: {self._cwd}")

    # ── AI call ───────────────────────────────────────────────────────────────

    @work(thread=True)
    def _call_ai(self):
        pkey    = self._provider
        model   = self._model
        pinfo   = prov_mod.PROVIDERS.get(pkey, {})
        api_key = cfg_mod.get_api_key(self._doc, pinfo.get("key_cfg") or pkey)
        s       = self._doc.get("ai_settings", {})
        sysprompt = sp_mod.build(self._cwd, extra=str(s.get("system_prompt", "")))
        reply, err = ai_mod.chat(
            provider=pkey, model=model,
            messages=self._messages, api_key=api_key,
            system_prompt=sysprompt,
            temperature=float(s.get("temperature", 1.0)),
            max_tokens=int(s.get("max_tokens", 4096)),
            top_p=float(s.get("top_p", 1.0)),
            top_k=int(s.get("top_k", -1)),
        )
        self.call_from_thread(self._on_reply, reply, err)

    def _on_reply(self, reply: str | None, err: str | None):
        self._set_status("")
        if err:
            self._render("error", err)
            return
        if not reply:
            return
        self._messages.append({"role": "assistant", "content": reply})
        self._render("assistant", reply)
        self._persist()
        tool_calls = tools_mod.parse_tools(reply)
        if tool_calls:
            name, groups = tool_calls[0]
            if self.auto_approve:
                self._run_tool(name, groups, outside_approved=False)
            else:
                self._pending_tools = [(name, groups)]
                self._render("info", f"Tool pending: {name}  — Enter to approve, Esc to cancel")

    def _run_tool(self, name: str, groups: tuple, outside_approved: bool):
        result = tools_mod.execute(name, groups, self._cwd,
                                   outside_cwd_approved=outside_approved)
        if result.needs_approval:
            def _on_approval(allowed: bool):
                if allowed:
                    self._run_tool(name, groups, outside_approved=True)
                else:
                    self._render("info", "Tool denied.")
            self.push_screen(ApprovalScreen(result.approval_prompt), _on_approval)
            return
        if result.ok:
            self._render("tool", str(result))
        else:
            self._render("tool_error", str(result))
        tool_msg = f"[Tool output — {result.tool}]\n{result.output}"
        self._messages.append({"role": "user", "content": tool_msg})
        self._persist()
        self._set_status("processing…", "yellow")
        self._call_ai()

    def action_interrupt(self):
        if self._pending_tools:
            self._pending_tools.clear()
            self._render("info", "Tool cancelled.")
        self._set_status("")

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_toggle_auto(self):
        self.auto_approve = not self.auto_approve
        cfg_mod.set_val(self._doc, "general", "auto_approve", self.auto_approve)
        cfg_mod.save(self._doc)
        self._refresh_header()
        self._set_status(f"Auto-approve: {'ON' if self.auto_approve else 'OFF'}", "cyan")

    def action_toggle_output(self):
        self.show_output = not self.show_output
        cfg_mod.set_val(self._doc, "general", "show_output", self.show_output)
        cfg_mod.save(self._doc)
        self._refresh_header()
        self._set_status(f"Output: {'visible' if self.show_output else 'hidden'}", "cyan")

    def action_show_help(self):      self.push_screen(HelpScreen())
    def action_clear_chat(self):     self.query_one("#chat-log", RichLog).clear()
    def action_quit_app(self):       self.exit()

    def action_new_session(self):
        tools_mod.reset_session()
        self._session_id = sess_mod.new_id()
        self._messages   = []
        self.query_one("#chat-log", RichLog).clear()
        self._refresh_header()
        self._render("info", f"New session: {self._session_id}")

    def action_show_sessions(self):
        self.push_screen(SessionBrowserScreen(), lambda r: self._load_session(r) if r else None)

    def action_show_picker(self):
        self.push_screen(ModelPickerScreen(self._doc), self._on_model_picked)

    def action_show_commands(self):
        self.push_screen(HelpScreen())

    def _on_model_picked(self, result):
        if result:
            provider_key, model_id, model_name = result
            cfg_mod.set_val(self._doc, "general", "provider", provider_key)
            cfg_mod.set_val(self._doc, "general", "model", model_id)
            cfg_mod.save(self._doc)
            self._refresh_header()
            self._render("info", f"Model → {model_name}")

    def action_show_settings(self):
        def cb(result):
            if result is not None:
                self._doc = result
                prov_mod._reload_custom(self._doc)
                self._refresh_header()
        self.push_screen(ProviderSettingsScreen(self._doc), cb)

    def action_show_ai_cfg(self):
        def cb(result):
            if result is not None:
                self._doc = result
        self.push_screen(AISettingsScreen(self._doc), cb)

    def _load_session(self, sid: str):
        existing = sess_mod.load(sid)
        if not existing:
            self._render("error", f"Session not found: {sid}")
            return
        tools_mod.reset_session()
        self._session_id = sid
        self._messages   = existing.get("messages", [])
        cfg_mod.set_val(self._doc, "general", "provider", existing.get("provider", self._provider))
        cfg_mod.set_val(self._doc, "general", "model",    existing.get("model", self._model))
        self._cwd = existing.get("cwd", self._cwd)
        self._refresh_header()
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self._render("info", f"Resumed: {sid}")
        for m in self._messages:
            self._render(m["role"], m["content"])

    def _persist(self):
        sess_mod.save(self._session_id, self._provider, self._model, self._cwd, self._messages)

    def on_unmount(self):
        from rich import print as rprint
        rprint(GOODBYE)
        rprint(f"Session ID: {self._session_id}")
