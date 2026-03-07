"""screens/session_browser.py — Ctrl+S session browser."""

from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, DataTable
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from rich.text import Text

from flexcoder import sessions as sess_mod
from flexcoder import providers as prov_mod
from flexcoder import config as cfg_mod


class SessionBrowserScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter",  "resume", "Resume"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="sb-root"):
            yield Static(
                "[bold cyan]Session Browser[/bold cyan]  "
                "[dim]↑↓ scroll · Enter resume · Esc cancel[/dim]",
                id="sb-title",
            )
            yield DataTable(id="sb-table")
            with Horizontal(id="sb-footer"):
                yield Button("▶  Resume  [Enter]", id="btn-resume", classes="btn-confirm")
                yield Button("✘  Cancel  [Esc]",   id="btn-cancel", classes="btn-cancel")

    def on_mount(self):
        self._sessions = sess_mod.list_all()
        tbl = self.query_one(DataTable)
        tbl.cursor_type = "row"
        tbl.add_columns("Session ID", "Provider", "Model", "Msgs", "Last message", "Directory")
        for s in self._sessions:
            info  = prov_mod.PROVIDERS.get(s["provider"], {})
            color = info.get("color", "white")
            tbl.add_row(
                Text(s["id"],                              style="dim cyan"),
                Text(info.get("name", s["provider"]),    style=color),
                Text(s["model"],                           style=color),
                Text(str(s["count"]),                      style="cyan"),
                Text(s["last"],                            style="dim"),
                Text(s["cwd"],                             style="dim"),
            )

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "btn-resume":
            self.action_resume()
        else:
            self.dismiss(None)

    def action_resume(self):
        tbl = self.query_one(DataTable)
        idx = tbl.cursor_row
        if idx is not None and 0 <= idx < len(self._sessions):
            self.dismiss(self._sessions[idx]["id"])
        else:
            self.dismiss(None)

    def action_cancel(self):
        self.dismiss(None)


# ── Standalone (flexcoder sessions) ──────────────────────────────────────────

class _StandaloneApp(App):
    from flexcoder._css import CSS_PATH

    def on_mount(self):
        doc = cfg_mod.load()
        async def _push():
            def _cb(result):
                self.exit()
            await self.push_screen(SessionBrowserScreen(), _cb)
        self.call_after_refresh(_push)


def run_standalone():
    _StandaloneApp().run()
