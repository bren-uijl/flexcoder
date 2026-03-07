"""screens/ai_settings.py — AI generation settings (temperature, max tokens…)."""

from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Input
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from rich.markup import escape as esc

from flexcoder import config as cfg_mod


class AISettingsScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+t", "close", "Close"),
    ]

    def __init__(self, doc):
        super().__init__()
        self._doc = doc

    def compose(self) -> ComposeResult:
        s = self._doc.get("ai_settings", {})
        with Vertical(id="ais-root"):
            yield Static("[bold cyan]AI Generation Settings[/bold cyan]", id="ais-title")

            for label, field, placeholder, tip in [
                ("Temperature",  "temperature",  "0.0 – 2.0",  "Creativity. Default: 1.0"),
                ("Max tokens",   "max_tokens",   "e.g. 4096",  "Max output length."),
                ("Top-P",        "top_p",        "0.0 – 1.0",  "Nucleus sampling. Default: 1.0"),
                ("Top-K",        "top_k",        "-1 = off",   "Top-K sampling. -1 = disabled."),
            ]:
                val = str(s.get(field, ""))
                with Horizontal(classes="ais-row"):
                    yield Static(f"[cyan]{label}[/cyan]", classes="ais-label")
                    yield Input(value=val, placeholder=f"{placeholder}  ({tip})",
                                id=f"ais-{field}", classes="ais-input")

            yield Static("[dim]System prompt addendum[/dim]", classes="field-label")
            yield Input(
                value=str(s.get("system_prompt", "")),
                placeholder="Extra instructions appended to the system prompt…",
                id="ais-system_prompt",
                classes="ais-input",
            )

            with Horizontal(id="ais-footer"):
                yield Button("✔  Save  [Enter]", id="btn-save",   classes="btn-confirm")
                yield Button("✘  Cancel [Esc]",  id="btn-cancel", classes="btn-cancel")

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "btn-save":
            self._save()
        else:
            self.dismiss(None)

    def _save(self):
        def _float(field: str, default: float) -> float:
            try:
                return float(self.query_one(f"#ais-{field}", Input).value)
            except ValueError:
                return default

        def _int(field: str, default: int) -> int:
            try:
                return int(self.query_one(f"#ais-{field}", Input).value)
            except ValueError:
                return default

        cfg_mod.set_val(self._doc, "ai_settings", "temperature",   _float("temperature", 1.0))
        cfg_mod.set_val(self._doc, "ai_settings", "max_tokens",    _int("max_tokens", 4096))
        cfg_mod.set_val(self._doc, "ai_settings", "top_p",         _float("top_p", 1.0))
        cfg_mod.set_val(self._doc, "ai_settings", "top_k",         _int("top_k", -1))
        sp = self.query_one("#ais-system_prompt", Input).value
        cfg_mod.set_val(self._doc, "ai_settings", "system_prompt", sp)
        cfg_mod.save(self._doc)
        self.dismiss(self._doc)

    def action_close(self):
        self.dismiss(None)


# ── Standalone (flexcoder settings) ──────────────────────────────────────────

class _StandaloneApp(App):
    from flexcoder._css import CSS_PATH

    def on_mount(self):
        doc = cfg_mod.load()
        async def _push():
            def _cb(result):
                self.exit()
            await self.push_screen(AISettingsScreen(doc), _cb)
        self.call_after_refresh(_push)


def run_standalone():
    _StandaloneApp().run()
