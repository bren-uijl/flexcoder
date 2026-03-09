"""screens/model_picker.py — Tab key model picker powered by models.dev."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Input, ListView, ListItem, Label
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import work, on
from rich.markup import escape as esc

from flexcoder import config as cfg_mod
from flexcoder import providers as prov_mod
from flexcoder import modelsdev

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
    """Tab-key model browser backed by models.dev."""

    BINDINGS = [
        Binding("escape", "cancel",  "Cancel"),
        Binding("enter",  "confirm", "Select"),
        Binding("tab",    "cancel",  "Close"),
    ]

    def __init__(self, doc):
        super().__init__()
        self._doc       = doc
        self._db: dict  = {}
        self._providers: list[dict] = []
        self._sel_prov : str = ""
        self._sel_model: str = ""
        self._sel_model_name: str = ""
        self._loading   = True
        # Maps list item id → model dict  (avoids passing data= to ListItem)
        self._model_index: dict[str, dict] = {}

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
        self._db        = db
        self._loading   = False
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
                return
        # fallback: select first
        if self._providers:
            self._select_provider(self._providers[0]["id"])

    def _populate_providers(self, query: str):
        plist = self.query_one("#mp-prov-list", ListView)
        plist.clear()
        q = query.lower()
        for pinfo in self._providers:
            pid  = pinfo["id"]
            name = pinfo["name"]
            cnt  = pinfo["model_count"]
            if q:
                models = modelsdev.get_models_for_provider(self._db, pid)
                match_prov  = q in name.lower() or q in pid.lower()
                match_model = any(q in m["name"].lower() or q in m["id"].lower() for m in models)
                if not match_prov and not match_model:
                    continue
            our_key   = _PROV_MAP.get(pid, (None,))[0]
            supported = our_key and our_key in prov_mod.PROVIDERS
            c = prov_mod.PROVIDERS.get(our_key, {}).get("color", "bright_black") if supported else "bright_black"
            plist.append(ListItem(
                Label(f"[{c}]{esc(name)}[/{c}]  [dim]{cnt}[/dim]"),
                id=f"mp-p-{pid}",
            ))

    def _select_provider(self, pid: str):
        self._sel_prov = pid
        plist = self.query_one("#mp-prov-list", ListView)
        for i, pinfo in enumerate(self._providers):
            if pinfo["id"] == pid:
                try:
                    plist.index = i
                except Exception:
                    pass
                break
        self._populate_models(pid, self.query_one("#mp-search", Input).value)

    def _populate_models(self, pid: str, query: str = ""):
        mlist = self.query_one("#mp-model-list", ListView)
        mlist.clear()
        self._model_index.clear()

        our_key = _PROV_MAP.get(pid, (None,))[0]
        c = prov_mod.PROVIDERS.get(our_key, {}).get("color", "white") if our_key else "white"
        models = modelsdev.get_models_for_provider(self._db, pid)
        q = query.lower()

        shown = [m for m in models
                 if not q or q in m["name"].lower() or q in m["id"].lower()]

        if not shown:
            mlist.append(ListItem(Label("[dim]No models found[/dim]")))
            self._sel_model = ""
            self._sel_model_name = ""
            return

        for m in shown:
            ctx   = modelsdev.format_context(m["context"])
            flags = ""
            if m["reasoning"]: flags += " [dim]reasoning[/dim]"
            if m["tool_call"]: flags += " [dim]tools[/dim]"
            # Build a safe unique id from model id
            safe_id = esc(m["id"]).replace("/","_").replace(":","_").replace(".","_").replace("-","_")
            item_id = f"mp-m-{safe_id}"
            self._model_index[item_id] = m
            mlist.append(ListItem(
                Label(f"[{c}]{esc(m['name'])}[/{c}]  [dim]{ctx}[/dim]{flags}"),
                id=item_id,
            ))

        # Pre-select first
        try:
            mlist.index = 0
        except Exception:
            pass
        self._sel_model      = shown[0]["id"]
        self._sel_model_name = shown[0]["name"]
        self._update_info(shown[0])

    def _update_info(self, m: dict):
        ctx   = modelsdev.format_context(m["context"])
        inp_c = modelsdev.format_cost(m["input_cost"])
        out_c = modelsdev.format_cost(m["output_cost"])
        try:
            self.query_one("#mp-model-info", Static).update(
                f"[dim]ctx {ctx}  in {inp_c}/M  out {out_c}/M[/dim]")
        except Exception:
            pass

    @on(Input.Changed, "#mp-search")
    def on_search(self, e: Input.Changed):
        self._populate_providers(e.value)
        if self._sel_prov:
            self._populate_models(self._sel_prov, e.value)

    @on(ListView.Highlighted, "#mp-prov-list")
    def on_prov_highlight(self, e):
        if e.item and e.item.id and e.item.id.startswith("mp-p-"):
            pid = e.item.id[5:]
            if pid != self._sel_prov:
                self._sel_prov = pid
                self._populate_models(pid, self.query_one("#mp-search", Input).value)

    @on(ListView.Highlighted, "#mp-model-list")
    def on_model_highlight(self, e):
        if e.item and e.item.id and e.item.id in self._model_index:
            m = self._model_index[e.item.id]
            self._sel_model      = m["id"]
            self._sel_model_name = m["name"]
            self._update_info(m)

    @on(ListView.Selected, "#mp-model-list")
    def on_model_select(self, e):
        self.action_confirm()

    def action_confirm(self):
        if self._loading or not self._sel_model:
            return
        our_key = _PROV_MAP.get(self._sel_prov, (None,))[0]
        if not our_key:
            pinfo = self._db.get(self._sel_prov, {})
            our_key = self._sel_prov
            if our_key not in prov_mod.PROVIDERS:
                prov_mod.PROVIDERS[our_key] = {
                    "name":    pinfo.get("name", our_key),
                    "color":   "white",
                    "needs_key": True,
                    "key_cfg": our_key,
                    "builtin": False,
                }
                prov_mod.PROVIDER_KEYS.append(our_key)
        cfg_mod.set_models(self._doc, our_key, [self._sel_model])
        cfg_mod.save(self._doc)
        self.dismiss((our_key, self._sel_model, self._sel_model_name))

    def action_cancel(self):
        self.dismiss(None)
