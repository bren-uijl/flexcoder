"""screens/help.py — Ctrl+H help overlay."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Vertical
from textual.binding import Binding

_HELP = """[bold cyan]flexcoder[/bold cyan] — AI coding assistant

[bold]Navigation[/bold]
  [bold]Tab[/bold]          Open model picker (models.dev)
  [bold]Ctrl+P[/bold]       Command palette / help
  [bold]Ctrl+E[/bold]       Provider settings (API keys, Fetch Models)
  [bold]Ctrl+T[/bold]       AI settings (temperature, tokens…)
  [bold]Ctrl+S[/bold]       Session browser
  [bold]Ctrl+N[/bold]       New session
  [bold]Ctrl+L[/bold]       Clear chat
  [bold]Ctrl+H[/bold]       This help
  [bold]Esc[/bold]          Cancel / interrupt tool
  [bold]Ctrl+C[/bold]       Quit

[bold]Tool approval[/bold]
  [bold]Ctrl+A[/bold]       Toggle auto-approve (AUTO/MANUAL)
  [bold]Ctrl+O[/bold]       Toggle tool output visibility

[bold]Commands[/bold]  (type in the input bar)
  [dim]/help[/dim]           This help
  [dim]/new[/dim]            New session
  [dim]/sessions[/dim]       Session browser
  [dim]/model <name>[/dim]   Switch model
  [dim]/status[/dim]         Show current config
  [dim]/clear[/dim]          Clear chat
  [dim]/quit[/dim]           Quit

[bold]AI tools[/bold]  (the model can use these)
  [dim]<create_file=path>…</create_file>[/dim]
  [dim]<read_file=path />[/dim]       (required before editing)
  [dim]<search_replace=path>…[/dim]
  [dim]<shell>cmd</shell>[/dim]        (outside cwd needs approval)
  [dim]<create_directory=path />[/dim]
  [dim]<move_file source=… destination=… />[/dim]
  [dim]<insert=path>…</insert>[/dim]

[bold]CLI[/bold]
  [dim]flexcoder[/dim]                  Start
  [dim]flexcoder continue[/dim]         Resume last session
  [dim]flexcoder continue <id>[/dim]    Resume specific session
  [dim]flexcoder providers[/dim]        Provider settings
  [dim]flexcoder sessions[/dim]         Session browser
"""


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+h", "close", "Close"),
        Binding("q",      "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-root"):
            yield Static(_HELP, id="help-text", markup=True)
            yield Button("Close  [Esc]", id="help-close")

    def on_button_pressed(self, e):
        self.dismiss(None)

    def action_close(self):
        self.dismiss(None)
