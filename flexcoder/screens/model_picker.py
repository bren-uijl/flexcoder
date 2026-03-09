"""screens/model_picker.py — Tab key model picker powered by models.dev."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Input, ListView, ListItem, Label
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import work, on
from rich.markup import escape as esc
from rich.text import Text

from flexcoder import config as cfg_mod
from flexcoder import providers as prov_mod
from flexcoder import modelsdev


# Map models.dev provider id → our provider key + needed api key config
_PROV_MAP = {
    "anthropic":  ("claude",      "anthropic"),
    "openai":     ("chatgpt",     "openai"),
    "google":     ("gemini",      "gemini"),
    "mistral":    ("mistral",     "mistral"),
    "openrouter": ("openrouter",  "openrouter"),
    "groq":       ("groq",        "groq"),
    "deepseek":   ("deepseek",    "deepseek"),
    "cohere":     ("cohere",      "cohere"),
    "perplexity": ("perplexity",  "perplexity"),
    "xai":        ("xai",         "xai"),
    "together":   ("together",    "together"),
    "fireworks":  ("fireworks",   "fireworks"),
    "ollama":     ("ollama",      None),
}


class ModelPickerScreen(ModalScreen):
    """Opencode-style model browser backed by models.dev."""

    BINDINGS = [
        Binding("escape", "cancel",  "Cancel"),
        Binding("enter",  "confirm", "Select"),
        Binding("tab",    "cancel",  "Close"),
    ]

    def __init__(self, doc):
        super().__init__()
        self._doc      = doc
        self._db: dict = {}
        self._providers: list[dict] = []
        self._sel_prov : str = ""
        self._sel_model: str = ""
        self._sel_model_name: str = ""
        self._loading  = True

    def compose(self) -> ComposeResult:
        with Vertical(id="mp-root"):
            with Horizontal(id="mp-header"):
                yield Input(placeholder="Search models…", id="mp-search")
                yield Static("[dim]tab[/dim] cancel", id="mp-hint")
            with Horizontal(id="mp-body"):
                with Vertical(id="mp-left"):
                    yield Static("[dim]Provider[/dim]", id="mp-prov-header")
                    yield ListView(id="mp-prov-list")
                with Vertical(id="mp-right"):
                    yield Static("[dim]Model[/dim]", id="mp-model-header")
                    yield ListView(id="mp-model-list")
            with Horizontal(id="mp-footer"):
                yield Static("", id="mp-model-info")
                yield Static("[dim]Loading models.dev…[/dim]", id="mp-status")

    def on_mount(self):
        self._load_db()

    @work(thread=True)
    def _load_db(self):
        db = modelsdev.fetch()
        self.app.call_from_thread(self._on_db_loaded, db)

    def _on_db_loaded(self, db: dict):
        self._db       = db
        self._loading  = False
        self._providers = modelsdev.get_providers(db)
        self.query_one("#mp-status", Static).update(
            f"[dim]{len(self._providers)} providers · models.dev[/dim]"
        )
        self._populate_providers("")
        # Pre-select current provider
        cur_prov = cfg_mod.get(self._doc, "general", "provider") or ""
        for pid, (our_key, _) in _PROV_MAP.items():
            if our_key == cur_prov and pid in self._db:
                self._select_provider(pid)
                break

    def _populate_providers(self, query: str):
        plist = self.query_one("#mp-prov-list", ListView)
        plist.clear()
        q = query.lower()
        for pinfo in self._providers:
            pid  = pinfo["id"]
            name = pinfo["name"]
            cnt  = pinfo["model_count"]
            if q and q not in name.lower() and q not in pid.lower():
                # Check if any model matches
                models = modelsdev.get_models_for_provider(self._db, pid)
                if not any(q in m["name"].lower() or q in m["id"].lower() for m in models):
                    continue
            # Highlight supported providers
            our_key = _PROV_MAP.get(pid, (None,))[0]
            supported = our_key and our_key in prov_mod.PROVIDERS
            c = prov_mod.PROVIDERS.get(our_key, {}).get("color", "white") if supported else "bright_black"
            plist.append(ListItem(
                Label(f"[{c}]{esc(name)}[/{c}]  [dim]{cnt}[/dim]"),
                id=f"mp-p-{pid}",
            ))
        if self._providers:
            plist.index = 0

    def _select_provider(self, pid: str):
        self._sel_prov = pid
        # Highlight correct item
        plist = self.query_one("#mp-prov-list", ListView)
        for i, pinfo in enumerate(self._providers):
            if pinfo["id"] == pid:
                plist.index = i
                break
        self._populate_models(pid, self.query_one("#mp-search", Input).value)

    def _populate_models(self, pid: str, query: str = ""):
        mlist  = self.query_one("#mp-model-list", ListView)
        mlist.clear()
        our_key = _PROV_MAP.get(pid, (None,))[0]
        c = prov_mod.PROVIDERS.get(our_key, {}).get("color", "white") if our_key else "white"
        models = modelsdev.get_models_for_provider(self._db, pid)
        q      = query.lower()
        shown  = []
        for m in models:
            if q and q not in m["name"].lower() and q not in m["id"].lower():
                continue
            shown.append(m)

        if not shown:
            mlist.append(ListItem(Label("[dim]No models found[/dim]")))
            return

        for m in shown:
            ctx   = modelsdev.format_context(m["context"])
            flags = ""
            if m["reasoning"]:  flags += " [dim]reasoning[/dim]"
            if m["tool_call"]:  flags += " [dim]tools[/dim]"
            mlist.append(ListItem(
                Label(
                    f"[{c}]{esc(m['name'])}[/{c}]  "
                    f"[dim]{ctx}[/dim]{flags}"
                ),
                id=f"mp-m-{esc(m['id']).replace('/', '_').replace(':', '_').replace('.', '_')}",
                data=m,  # type: ignore[call-arg]
            ))
        mlist.index = 0
        if shown:
            self._sel_model      = shown[0]["id"]
            self._sel_model_name = shown[0]["name"]
            self._update_info(shown[0])

    def _update_info(self, m: dict):
        ctx   = modelsdev.format_context(m["context"])
        inp_c = modelsdev.format_cost(m["input_cost"])
        out_c = modelsdev.format_cost(m["output_cost"])
        info  = f"[dim]ctx {ctx}  in {inp_c}/M  out {out_c}/M[/dim]"
        try:
            self.query_one("#mp-model-info", Static).update(info)
        except Exception:
            pass

    @on(Input.Changed, "#mp-search")
    def on_search(self, e: Input.Changed):
        q = e.value
        self._populate_providers(q)
        if self._sel_prov:
            self._populate_models(self._sel_prov, q)

    @on(ListView.Highlighted, "#mp-prov-list")
    def on_prov_highlight(self, e):
        if e.item and e.item.id and e.item.id.startswith("mp-p-"):
            pid = e.item.id[5:]
            if pid != self._sel_prov:
                self._sel_prov = pid
                self._populate_models(pid, self.query_one("#mp-search", Input).value)

    @on(ListView.Highlighted, "#mp-model-list")
    def on_model_highlight(self, e):
        if e.item and hasattr(e.item, "data") and e.item.data:
            m = e.item.data
            self._sel_model      = m["id"]
            self._sel_model_name = m["name"]
            self._update_info(m)

    @on(ListView.Selected, "#mp-model-list")
    def on_model_select(self, e):
        self.action_confirm()

    def on_button_pressed(self, e: Button.Pressed):
        if e.button.id == "btn-mp-confirm":
            self.action_confirm()
        else:
            self.action_cancel()

    def action_confirm(self):
        if self._loading:
            return
        if not self._sel_model:
            return
        # Find our provider key
        our_key = _PROV_MAP.get(self._sel_prov, (None,))[0]
        if not our_key:
            # Unknown provider — register it on-the-fly as custom if possible
            pinfo = self._db.get(self._sel_prov, {})
            our_key = self._sel_prov
            if our_key not in prov_mod.PROVIDERS:
                prov_mod.PROVIDERS[our_key] = {
                    "name":      pinfo.get("name", our_key),
                    "color":     "white",
                    "needs_key": True,
                    "key_cfg":   our_key,
                    "builtin":   False,
                }
                prov_mod.PROVIDER_KEYS.append(our_key)
        # Save model to config cache
        cfg_mod.set_models(self._doc, our_key, [self._sel_model])
        cfg_mod.save(self._doc)
        self.dismiss((our_key, self._sel_model, self._sel_model_name))

    def action_cancel(self):
        self.dismiss(None)
