"""screens/provider_settings.py — provider settings popup (Ctrl+E / flexcoder providers)."""

import tomlkit
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Input, ListView, ListItem, Label, Switch
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.binding import Binding
from textual import work, on
from rich.markup import escape as esc

from flexcoder import config as cfg_mod
from flexcoder import providers as prov_mod


class ProviderSettingsScreen(ModalScreen):
    """Provider settings popup: API keys + live model fetch."""

    BINDINGS = [
        Binding("escape",    "close", "Close"),
        Binding("ctrl+e",    "close", "Close"),
        Binding("tab",       "focus_next",     "Next"),
        Binding("shift+tab", "focus_previous", "Prev"),
    ]

    def __init__(self, doc, first_run: bool = False):
        super().__init__()
        self._doc       = doc
        self._pkeys     = prov_mod.PROVIDER_KEYS
        self._sel       = cfg_mod.get(doc, "general", "provider") or "ollama"
        self._first_run = first_run

    def compose(self) -> ComposeResult:
        title = (
            "[bold cyan]Welcome to flexcoder![/bold cyan]  Set up at least one provider to continue."
            if self._first_run else
            "[bold cyan]Provider Settings[/bold cyan]  —  API keys & models"
        )
        with Vertical(id="ps-root"):
            yield Static(title, id="ps-title")
            with Horizontal(id="ps-body"):
                # Left: provider list + add custom button
                with Vertical(id="ps-left"):
                    yield Static("[bold]Providers[/bold]", classes="col-header")
                    yield ListView(id="ps-prov-list")
                    yield Button("＋  Add custom…", id="btn-add-prov", classes="btn-add")
                # Right: settings panel
                with Vertical(id="ps-right"):
                    yield Static("", id="ps-prov-label")
                    yield Static("[dim]API Key[/dim]", classes="field-label")
                    yield Input(password=True, placeholder="Paste key here…", id="ps-key-input")
                    with Horizontal(id="ps-key-row"):
                        yield Button("Show",        id="btn-show",     classes="btn-action")
                        yield Button("✔ Save Key",  id="btn-save-key", variant="primary")
                    yield Static("", id="ps-key-status")
                    with Horizontal(id="ps-model-row"):
                        yield Static("[bold]Models[/bold]", id="ps-model-title")
                        yield Button("⟳  Fetch Models", id="btn-fetch", variant="success")
                    yield Static("", id="ps-fetch-status")
                    yield ListView(id="ps-model-list")
            with Horizontal(id="ps-footer"):
                yield Button("✔  Done", id="btn-done",   classes="btn-confirm")
                if not self._first_run:
                    yield Button("✘  Cancel", id="btn-cancel", classes="btn-cancel")

    def on_mount(self):
        self._repopulate_provider_list()
        self._load_panel(self._sel)

    def _repopulate_provider_list(self):
        plist = self.query_one("#ps-prov-list", ListView)
        plist.clear()
        for key, info in prov_mod.PROVIDERS.items():
            c = info["color"]
            plist.append(ListItem(
                Label(f"[{c}]{info['name']}[/{c}]"),
                id=f"prov-{key}",
            ))
        for i, k in enumerate(self._pkeys):
            if k == self._sel:
                plist.index = i
                break

    @on(ListView.Highlighted, "#ps-prov-list")
    def on_prov(self, e):
        if e.item and e.item.id:
            k = e.item.id.replace("prov-", "")
            if k in prov_mod.PROVIDERS and k != self._sel:
                self._sel = k
                self._load_panel(k)

    def _load_panel(self, key: str):
        if key not in prov_mod.PROVIDERS:
            return
        info = prov_mod.PROVIDERS[key]
        c    = info["color"]
        self.query_one("#ps-prov-label", Static).update(f"[bold {c}]{info['name']}[/bold {c}]")

        ki          = self.query_one("#ps-key-input", Input)
        kname       = info.get("key_cfg") or key
        ki.value    = cfg_mod.get_api_key(self._doc, kname) or ""
        ki.password = True
        disabled    = not info.get("needs_key", True)
        ki.disabled = disabled
        self.query_one("#btn-show",     Button).disabled = disabled
        self.query_one("#btn-save-key", Button).disabled = disabled
        self.query_one("#ps-key-status",  Static).update("")
        self.query_one("#ps-fetch-status",Static).update("")
        self._refresh_models(key)

    def _refresh_models(self, key: str):
        mlist = self.query_one("#ps-model-list", ListView)
        mlist.clear()
        info   = prov_mod.PROVIDERS.get(key, {})
        c      = info.get("color", "white")
        models = cfg_mod.get_models(self._doc, key)
        if not models:
            mlist.append(ListItem(Label("[dim]No models cached — press Fetch Models[/dim]")))
            return
        for m in models:
            mid = esc(m).replace("/", "-").replace(":", "-")
            mlist.append(ListItem(Label(f"[{c}]{esc(m)}[/{c}]"), id=f"m-{mid}"))

    def on_button_pressed(self, e: Button.Pressed):
        match e.button.id:
            case "btn-show":
                inp         = self.query_one("#ps-key-input", Input)
                inp.password = not inp.password
                e.button.label = "Hide" if not inp.password else "Show"

            case "btn-save-key":
                self._save_key()

            case "btn-fetch":
                self._do_fetch()

            case "btn-add-prov":
                self.app.push_screen(AddProviderScreen(self._doc), self._on_provider_added)

            case "btn-done":
                self.dismiss(self._doc)

            case "btn-cancel":
                self.dismiss(None)

    def _save_key(self):
        key   = self._sel
        val   = self.query_one("#ps-key-input", Input).value.strip()
        kname = prov_mod.PROVIDERS[key].get("key_cfg") or key
        if "api_keys" not in self._doc:
            self._doc.add("api_keys", tomlkit.table())
        self._doc["api_keys"][kname] = val
        cfg_mod.save(self._doc)
        self.query_one("#ps-key-status", Static).update("[bold green]✔ Key saved[/bold green]")

    def _do_fetch(self):
        key     = self._sel
        info    = prov_mod.PROVIDERS.get(key, {})
        kname   = info.get("key_cfg") or key
        api_key = cfg_mod.get_api_key(self._doc, kname)
        if info.get("needs_key", True) and not api_key:
            self.query_one("#ps-fetch-status", Static).update(
                "[bold red]⚠  Save an API key first[/bold red]")
            return
        self.query_one("#ps-fetch-status", Static).update("[yellow]Fetching…[/yellow]")
        self.query_one("#btn-fetch", Button).disabled = True
        self._fetch_worker(key, api_key)

    @work(thread=True)
    def _fetch_worker(self, key: str, api_key: str):
        models, err = prov_mod.fetch_models(key, api_key)
        # FIX: use self.app.call_from_thread — call_from_thread lives on App, not Screen
        self.app.call_from_thread(self._on_fetched, key, models, err)

    def _on_fetched(self, key: str, models: list[str], err: str | None):
        self.query_one("#btn-fetch", Button).disabled = False
        if err:
            self.query_one("#ps-fetch-status", Static).update(f"[bold red]✘  {esc(err)}[/bold red]")
            return
        cfg_mod.set_models(self._doc, key, models)
        cfg_mod.save(self._doc)
        self.query_one("#ps-fetch-status", Static).update(
            f"[bold green]✔  {len(models)} models fetched[/bold green]")
        if key == self._sel:
            self._refresh_models(key)

    def _on_provider_added(self, result):
        if result:
            self._doc = result
            prov_mod._reload_custom(self._doc)
            self._pkeys = prov_mod.PROVIDER_KEYS
            self._repopulate_provider_list()

    def action_close(self):
        self.dismiss(self._doc)


# ── Add custom provider popup ─────────────────────────────────────────────────

class AddProviderScreen(ModalScreen):
    """Small popup to register a custom OpenAI-compatible provider."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, doc):
        super().__init__()
        self._doc = doc

    def compose(self) -> ComposeResult:
        with Vertical(id="ap-root"):
            yield Static("[bold cyan]Add Custom Provider[/bold cyan]", id="ap-title")
            yield Static("[dim]Display name[/dim]", classes="field-label")
            yield Input(placeholder="e.g. My LM Studio", id="ap-name")
            yield Static("[dim]Key in config (unique, no spaces)[/dim]", classes="field-label")
            yield Input(placeholder="e.g. lmstudio", id="ap-key")
            yield Static("[dim]Base URL[/dim]", classes="field-label")
            yield Input(placeholder="e.g. http://localhost:1234/v1", id="ap-url")
            yield Static("[dim]Models list endpoint  [bold](GET)[/bold][/dim]", classes="field-label")
            yield Input(placeholder="e.g. http://localhost:1234/v1/models", id="ap-models-url")
            yield Static("[dim]API key needed?[/dim]", classes="field-label")
            with Horizontal(id="ap-switch-row"):
                yield Switch(value=False, id="ap-needs-key")
                yield Static(" No key needed", id="ap-key-label")
            yield Static("", id="ap-status")
            with Horizontal(id="ap-footer"):
                yield Button("✔  Add",    id="btn-ap-add",    classes="btn-confirm")
                yield Button("✘  Cancel", id="btn-ap-cancel", classes="btn-cancel")

    @on(Switch.Changed, "#ap-needs-key")
    def on_switch(self, e):
        self.query_one("#ap-key-label", Static).update(
            " Key required" if e.value else " No key needed")

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "btn-ap-add":
            self._add()
        else:
            self.dismiss(None)

    def _add(self):
        name      = self.query_one("#ap-name",       Input).value.strip()
        key       = self.query_one("#ap-key",        Input).value.strip().lower().replace(" ", "_")
        url       = self.query_one("#ap-url",        Input).value.strip()
        murl      = self.query_one("#ap-models-url", Input).value.strip()
        needs_key = self.query_one("#ap-needs-key",  Switch).value

        if not name or not key or not url:
            self.query_one("#ap-status", Static).update("[red]Name, key, and URL are required[/red]")
            return
        if key in prov_mod.PROVIDERS:
            self.query_one("#ap-status", Static).update(f"[red]Key '{key}' already exists[/red]")
            return

        # Persist custom providers in config
        if "custom_providers" not in self._doc:
            self._doc.add("custom_providers", tomlkit.table())
        t = tomlkit.table()
        t["name"]       = name
        t["color"]      = "white"
        t["base_url"]   = url
        t["models_url"] = murl
        t["needs_key"]  = needs_key
        t["key_cfg"]    = key
        self._doc["custom_providers"][key] = t

        # Empty model list placeholder
        if "models" not in self._doc:
            self._doc.add("models", tomlkit.table())
        arr = tomlkit.array()
        self._doc["models"][key] = arr
        if "api_keys" not in self._doc:
            self._doc.add("api_keys", tomlkit.table())
        self._doc["api_keys"][key] = ""

        cfg_mod.save(self._doc)
        self.dismiss(self._doc)

    def action_cancel(self):
        self.dismiss(None)


# ── Standalone (flexcoder providers) ─────────────────────────────────────────

class _StandaloneApp(App):
    from flexcoder._css import CSS_PATH

    def on_mount(self):
        doc = cfg_mod.load()
        def _cb(result):
            if result is not None:
                cfg_mod.save(result)
            self.exit()
        self.push_screen(ProviderSettingsScreen(doc), _cb)


def run_standalone():
    _StandaloneApp().run()
