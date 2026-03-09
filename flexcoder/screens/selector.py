"""screens/selector.py — Ctrl+P provider + model picker."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, ListView, ListItem, Label
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
from rich.markup import escape as esc

from flexcoder import config as cfg_mod
from flexcoder import providers as prov_mod


class SelectorScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter",  "confirm", "Select"),
    ]

    def __init__(self, doc, current_provider: str = "ollama", current_model: str = ""):
        super().__init__()
        self._doc      = doc
        self._pkeys    = prov_mod.PROVIDER_KEYS
        self._sel_prov = current_provider
        self._sel_mod  = current_model

    def compose(self) -> ComposeResult:
        with Vertical(id="sel-root"):
            yield Static(
                "[bold cyan]Select Provider & Model[/bold cyan]  "
                "[dim]↑↓ navigate · Enter confirm · Esc cancel[/dim]",
                id="sel-title",
            )
            with Horizontal(id="sel-body"):
                with Vertical(id="sel-left"):
                    yield Static("[bold]Provider[/bold]", classes="col-header")
                    yield ListView(id="sel-prov-list")
                with Vertical(id="sel-right"):
                    yield Static("[bold]Model[/bold]", classes="col-header")
                    yield ListView(id="sel-model-list")
            yield Static("", id="sel-hint")
            with Horizontal(id="sel-footer"):
                yield Button("✔  Confirm  [Enter]", id="btn-confirm", classes="btn-confirm")
                yield Button("✘  Cancel   [Esc]",   id="btn-cancel",  classes="btn-cancel")

    async def on_mount(self):
        plist = self.query_one("#sel-prov-list", ListView)
        for key, info in prov_mod.PROVIDERS.items():
            c = info["color"]
            plist.append(ListItem(Label(f"[{c}]{info['name']}[/{c}]"), id=f"sprov-{key}"))
        for i, k in enumerate(self._pkeys):
            if k == self._sel_prov:
                plist.index = i
                break
        await self._populate_models(self._sel_prov)

    async def _populate_models(self, pkey: str):
        mlist = self.query_one("#sel-model-list", ListView)
        await mlist.clear()
        info   = prov_mod.PROVIDERS[pkey]
        c      = info["color"]
        models = cfg_mod.get_models(self._doc, pkey)
        if not models:
            mlist.append(ListItem(
                Label("[dim]No models — use Ctrl+E to fetch[/dim]")))
            self.query_one("#sel-hint", Static).update(
                "[dim]Press Ctrl+E to configure API key and fetch models first[/dim]")
            self._sel_mod = ""
            return
        self.query_one("#sel-hint", Static).update("")
        for m in models:
            mid = esc(m).replace("/", "-").replace(":", "-").replace(".", "-")
            mlist.append(ListItem(Label(f"[{c}]{esc(m)}[/{c}]"), id=f"smod-{mid}"))
        # pre-select
        idx = 0
        if self._sel_mod in models:
            idx = models.index(self._sel_mod)
        elif models:
            self._sel_mod = models[0]
        mlist.index = idx

    @on(ListView.Highlighted, "#sel-prov-list")
    async def on_prov(self, e):
        if e.item and e.item.id:
            k = e.item.id.replace("sprov-", "")
            if k in prov_mod.PROVIDERS:
                self._sel_prov = k
                self._sel_mod  = ""
                await self._populate_models(k)

    @on(ListView.Highlighted, "#sel-model-list")
    def on_model(self, e):
        if e.item and e.item.id and e.item.id.startswith("smod-"):
            raw    = e.item.id[5:]  # strip "smod-"
            models = cfg_mod.get_models(self._doc, self._sel_prov)
            for m in models:
                if esc(m).replace("/", "-").replace(":", "-").replace(".", "-") == raw:
                    self._sel_mod = m
                    break

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "btn-confirm":
            self.action_confirm()
        else:
            self.action_cancel()

    def action_confirm(self):
        if self._sel_mod:
            self.dismiss((self._sel_prov, self._sel_mod))
        else:
            self.notify("Select a model first — use Ctrl+E to fetch models", severity="warning")

    def action_cancel(self):
        self.dismiss(None)
