"""screens/chat.py — main flexcoder chat TUI."""

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
from flexcoder.screens.selector import SelectorScreen
from flexcoder.screens.session_browser import SessionBrowserScreen
from flexcoder.screens.provider_settings import ProviderSettingsScreen
from flexcoder.screens.ai_settings import AISettingsScreen

from flexcoder._css import CSS_PATH as _CSS


# ── Tool approval popup ───────────────────────────────────────────────────────

class ApprovalScreen(ModalScreen):
    """Small popup asking to approve/deny a tool call."""

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
        Binding("ctrl+p", "show_selector", "Provider",     priority=True),
        Binding("ctrl+e", "show_settings", "Settings",     priority=True),
        Binding("ctrl+t", "show_ai_cfg",   "AI settings",  priority=True),
        Binding("ctrl+l", "clear_chat",    "Clear",        priority=True),
        Binding("escape", "interrupt",     "Interrupt",    priority=True),
        Binding("ctrl+c", "quit_app",      "Quit",         priority=True),
    ]

    auto_approve: reactive = reactive(True)
    show_output:  reactive = reactive(False)

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, session_id: str | None = None):
        super().__init__()
        self._doc = cfg_mod.load()
        # Load custom providers from config before anything else
        prov_mod._reload_custom(self._doc)

        self.auto_approve = bool(cfg_mod.get(self._doc, "general", "auto_approve") or True)
        self.show_output  = bool(cfg_mod.get(self._doc, "general", "show_output")  or False)

        self._session_id = session_id or sess_mod.new_id()
        self._messages:  list[dict] = []
        self._cwd = str(Path.cwd())
        # If started from the repository root (contains a 'flexcoder' subdirectory), use the user's home directory instead
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
                                 existing.get("model",    self._model))
                self._cwd = existing.get("cwd", self._cwd)
        # Ensure we don’t keep the repository root as cwd – switch to home if necessary
        if (Path(self._cwd) / "flexcoder").is_dir():
            self._cwd = str(Path.home())

        _up = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
        self._warn_home = bool(_up and Path(self._cwd).resolve() == Path(_up).resolve())

        # First-run: no model set anywhere
        models_exist = any(
            cfg_mod.get_models(self._doc, k)
            for k in prov_mod.PROVIDER_KEYS
        )
        self._first_run = not models_exist

    @property
    def _provider(self) -> str:
        return str(cfg_mod.get(self._doc, "general", "provider") or "ollama")

    @property
    def _model(self) -> str:
        return str(cfg_mod.get(self._doc, "general", "model") or "")

    # ── Layout ────────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal(id="header-box"):
                with Vertical(id="header-left"):
                    for i, line in enumerate(FLEXCODER):
                        yield Static(line, id=f"ascii-{i}", classes="header-ascii")
                with Vertical(id="header-right"):
                    yield Static("Selected provider:  [dim]Ctrl+P[/dim]",
                                 id="header-provider-label")
                    yield Static("", id="header-provider-value")
                    yield Static("Selected model:     [dim]Ctrl+P[/dim]",
                                 id="header-model-label")
                    yield Static("", id="header-model-value")
                    yield Static("", id="header-flags")
            yield RichLog(id="chat-log", highlight=True, markup=True, wrap=True)
            with Vertical(id="input-box"):
                yield Input(
                    placeholder="Ask flexcoder anything…  (/help for commands)",
                    id="chat-input",
                )
            with Horizontal(id="footer-bar"):
                yield Static("esc = interrupt", id="footer-left")
                yield Static("ctrl+c = quit",   id="footer-right")

    def on_mount(self):
        self._refresh_header()

        if self._warn_home:
            self._render("warning",
                "You are in your home / USERPROFILE directory. "
                "It is not recommended to run flexcoder here.")

        if self._first_run:
            # Open provider settings as a popup immediately
            def _after_setup(result):
                if result:
                    self._doc = result
                    prov_mod._reload_custom(self._doc)
                    self._refresh_header()
                    self._render("info", "Provider configured. Now press Ctrl+P to select a model.")
                else:
                    self._render("info",
                        "No provider configured yet. Press Ctrl+E to set one up.")
            self.call_after_refresh(
                lambda: self.push_screen(
                    ProviderSettingsScreen(self._doc, first_run=True), _after_setup
                )
            )
        elif not self._model:
            self._render("info",
                "No model selected — press Ctrl+P to pick one, or Ctrl+E to fetch models first.")
        else:
            pinfo = prov_mod.PROVIDERS.get(self._provider, {})
            c     = pinfo.get("color", "white")
            # Show basic session info without markup tags
            info_msg = (
                f"Provider: {pinfo.get('name', self._provider)}  "
                f"Model: {self._model or '(none)'}  "
                f"Session: {self._session_id}  "
                f"cwd: {self._cwd}"
                )
            self._render("info", info_msg)

        if self._messages:
            self.query_one("#chat-log", RichLog).write(
                Text.from_markup(
                    f"[dim]─── Resuming {len(self._messages)} messages ───[/dim]\n"
                )
            )
            for m in self._messages:
                self._render(m["role"], m["content"])

        self.query_one("#chat-input", Input).focus()

    # ── Header ────────────────────────────────────────────────────────────────

    def _refresh_header(self):
        pinfo = prov_mod.PROVIDERS.get(self._provider, {})
        c     = pinfo.get("color", "white")
        label = pinfo.get("name", self._provider)
        model = self._model or "[dim](none)[/dim]"
        auto  = "[bold green]AUTO[/bold green]"   if self.auto_approve else "[bold red]MANUAL[/bold red]"
        out   = "[bold yellow]OUT[/bold yellow]"   if self.show_output  else "[bold dim]QUIET[/bold dim]"
        sid   = f"[dim]{self._session_id}[/dim]"
        try:
            self.query_one("#header-provider-value", Static).update(f"[{c}]{label}[/{c}]")
            self.query_one("#header-model-value",    Static).update(f"[{c}]{model}[/{c}]")
            self.query_one("#header-flags",          Static).update(f"{auto}  {out}  {sid}")
            for i in range(5):
                self.query_one(f"#ascii-{i}", Static).update(f"[{c}]{FLEXCODER[i]}[/{c}]")
        except Exception:
            pass

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render(self, role: str, content: str):
        log   = self.query_one("#chat-log", RichLog)
        pinfo = prov_mod.PROVIDERS.get(self._provider, {})
        c     = pinfo.get("color", "green")
        match role:
            case "user":
                log.write(Text.from_markup(
                    f"[bold cyan]You[/bold cyan]  [dim]›[/dim]  {esc(content)}\n"))
            case "assistant":
                log.write(Text.from_markup(
                    f"[bold {c}]AI[/bold {c}]   [dim]›[/dim]  {esc(content)}\n"))
            case "tool":
                if self.show_output:
                    log.write(Text.from_markup(f"[dim]{esc(content)}[/dim]\n"))
            case "tool_error":
                log.write(Text.from_markup(
                    f"[bold red]Tool error[/bold red]  {esc(content)}\n"))
            case "info":
                log.write(Text.from_markup(
                    f"[bold yellow]•[/bold yellow]  [yellow]{esc(content)}[/yellow]\n"))
            case "error":
                log.write(Text.from_markup(
                    f"[bold red]✘[/bold red]  [red]{esc(content)}[/red]\n"))

    def _status(self, msg: str, color: str = "dim"):
        try:
            self.query_one("#footer-left", Static).update(
                Text.from_markup(f"[{color}]{esc(msg)}[/{color}]") if msg
                else "esc = interrupt"
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
            self._render("error", "No model selected. Press Ctrl+E → Ctrl+P.")
            return

        self._messages.append({"role": "user", "content": text})
        self._render("user", text)
        self._persist()
        self._status("Thinking…", "yellow")
        self._call_ai()

    def _command(self, text: str):
        parts = text.split(maxsplit=1)
        cmd   = parts[0].lower()
        arg   = parts[1].strip() if len(parts) > 1 else ""
        match cmd:
            case "/help" | "/h":           self.action_show_help()
            case "/new":                   self.action_new_session()
            case "/sessions":              self.action_show_sessions()
            case "/provider":              self.action_show_selector()
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
            self._render("info", "Available: " + (", ".join(models) if models else "none"))
            return
        if models and model not in models:
            self._render("error", f"'{model}' not in cached list")
            return
        cfg_mod.set_val(self._doc, "general", "model", model)
        cfg_mod.save(self._doc)
        self._refresh_header()
        self._render("info", f"Model → {model}")

    def _show_status(self):
        pinfo = prov_mod.PROVIDERS.get(self._provider, {})
        self._render("info",
            f"Provider: {pinfo.get('name', self._provider)}  Model: {self._model}  "
            f"Session: {self._session_id}  Auto: {self.auto_approve}  "
            f"Output: {self.show_output}  CWD: {self._cwd}")

    # ── AI call (threaded) ────────────────────────────────────────────────────

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
        self._status("")
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
                self._render("info",
                    f"Tool pending: [{name}]  — Enter to approve, Esc to cancel")

    def _run_tool(self, name: str, groups: tuple, outside_approved: bool):
        result = tools_mod.execute(name, groups, self._cwd,
                                   outside_cwd_approved=outside_approved)
        if result.needs_approval:
            # Shell wants to go outside cwd — ask user via popup
            def _on_approval(allowed: bool):
                if allowed:
                    self._run_tool(name, groups, outside_approved=True)
                else:
                    self._render("info", "Tool denied — command cancelled.")
            self.push_screen(ApprovalScreen(result.approval_prompt), _on_approval)
            return

        if result.ok:
            self._render("tool", str(result))
        else:
            self._render("tool_error", str(result))

        tool_msg = f"[Tool output — {result.tool}]\n{result.output}"
        self._messages.append({"role": "user", "content": tool_msg})
        self._persist()
        self._status("Processing tool result…", "yellow")
        self._call_ai()

    def action_interrupt(self):
        if self._pending_tools:
            self._pending_tools.clear()
            self._render("info", "Pending tool cancelled.")
        self._status("")

    # ── Actions ──────────────────────────────────────────────────────────────

    def action_toggle_auto(self):
        self.auto_approve = not self.auto_approve
        cfg_mod.set_val(self._doc, "general", "auto_approve", self.auto_approve)
        cfg_mod.save(self._doc)
        self._refresh_header()
        self._status(f"Auto-approve: {'ON' if self.auto_approve else 'OFF'}", "cyan")

    def action_toggle_output(self):
        self.show_output = not self.show_output
        cfg_mod.set_val(self._doc, "general", "show_output", self.show_output)
        cfg_mod.save(self._doc)
        self._refresh_header()
        self._status(f"Output: {'visible' if self.show_output else 'hidden'}", "cyan")

    def action_show_help(self):
        self.push_screen(HelpScreen())

    def action_new_session(self):
        tools_mod.reset_session()
        self._session_id = sess_mod.new_id()
        self._messages   = []
        self.query_one("#chat-log", RichLog).clear()
        self._refresh_header()
        self._render("info", f"New session: {self._session_id}")

    def action_show_sessions(self):
        def cb(result):
            if result:
                self._load_session(result)
        self.push_screen(SessionBrowserScreen(), cb)

    def action_show_selector(self):
        def cb(result):
            if result:
                prov, model = result
                cfg_mod.set_val(self._doc, "general", "provider", prov)
                cfg_mod.set_val(self._doc, "general", "model",    model)
                cfg_mod.save(self._doc)
                self._refresh_header()
                pinfo = prov_mod.PROVIDERS.get(prov, {})
                self._render("info",
                    f"Provider → {pinfo.get('name', prov)}  Model → {model}")
        self.push_screen(SelectorScreen(self._doc, self._provider, self._model), cb)

    def action_show_settings(self):
        def cb(result):
            if result is not None:
                self._doc = result
                prov_mod._reload_custom(self._doc)
                self._refresh_header()
                self._render("info", "Provider settings saved.")
        self.push_screen(ProviderSettingsScreen(self._doc), cb)

    def action_show_ai_cfg(self):
        def cb(result):
            if result is not None:
                self._doc = result
                self._render("info", "AI settings saved.")
        self.push_screen(AISettingsScreen(self._doc), cb)

    def action_clear_chat(self):
        self.query_one("#chat-log", RichLog).clear()

    def action_quit_app(self):
        self.exit()

    # ── Session helpers ───────────────────────────────────────────────────────

    def _load_session(self, sid: str):
        existing = sess_mod.load(sid)
        if not existing:
            self._render("error", f"Session not found: {sid}")
            return
        tools_mod.reset_session()
        self._session_id = sid
        self._messages   = existing.get("messages", [])
        cfg_mod.set_val(self._doc, "general", "provider",
                        existing.get("provider", self._provider))
        cfg_mod.set_val(self._doc, "general", "model",
                        existing.get("model", self._model))
        self._cwd = existing.get("cwd", self._cwd)
        self._refresh_header()
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self._render("info", f"Resumed: {sid}")
        for m in self._messages:
            self._render(m["role"], m["content"])

    def _persist(self):
        sess_mod.save(
            self._session_id, self._provider,
            self._model, self._cwd, self._messages,
        )

    def on_unmount(self):
        from rich import print as rprint
        rprint(GOODBYE)
        rprint(f"Session ID: {self._session_id}")
