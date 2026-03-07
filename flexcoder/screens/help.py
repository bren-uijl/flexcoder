"""screens/help.py — Ctrl+H help overlay."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Vertical
from textual.binding import Binding

_TEXT = """\
[bold cyan]flexcoder[/bold cyan] — AI Coding Assistant TUI

[bold yellow]KEYBOARD SHORTCUTS[/bold yellow]
  [bold]Ctrl+A[/bold]   Toggle auto-approve  [dim](header: AUTO / MANUAL)[/dim]
  [bold]Ctrl+O[/bold]   Toggle output visibility  [dim](header: OUT / QUIET)[/dim]
  [bold]Ctrl+H[/bold]   This help screen
  [bold]Ctrl+N[/bold]   New session
  [bold]Ctrl+S[/bold]   Session browser  [dim](↑↓ + Enter)[/dim]
  [bold]Ctrl+P[/bold]   Provider / model selector
  [bold]Ctrl+E[/bold]   Provider settings  [dim](API keys + Fetch Models)[/dim]
  [bold]Ctrl+T[/bold]   AI generation settings  [dim](temperature, max tokens…)[/dim]
  [bold]Ctrl+L[/bold]   Clear chat display
  [bold]Esc[/bold]      Interrupt current AI request / close modal
  [bold]Ctrl+C[/bold]   Quit

[bold yellow]HEADER INDICATORS[/bold yellow]
  [bold green]AUTO[/bold green]   Auto-approve ON   [dim]AI actions execute without confirmation[/dim]
  [bold red]MANUAL[/bold red] Auto-approve OFF  [dim]Each AI action requires approval[/dim]
  [bold yellow]OUT[/bold yellow]    Output visible    [dim]Tool output shown in chat[/dim]
  [bold dim]QUIET[/bold dim]  Output hidden     [dim]Only errors shown[/dim]

[bold yellow]CHAT COMMANDS[/bold yellow]
  [bold]/help[/bold]          Show this screen
  [bold]/new[/bold]           Start a new session
  [bold]/sessions[/bold]      Open session browser
  [bold]/provider[/bold]      Open provider selector
  [bold]/settings[/bold]      Open AI settings
  [bold]/model <n>[/bold]  Switch model
  [bold]/clear[/bold]         Clear chat
  [bold]/status[/bold]        Show current config
  [bold]/exit[/bold]          Quit

[bold yellow]STARTUP[/bold yellow]
  [bold]flexcoder[/bold]                        Default (saved config)
  [bold]flexcoder ollama gemma3:3b[/bold]       Start with Ollama gemma3:3b
  [bold]flexcoder continue[/bold]               Resume most recent session
  [bold]flexcoder continue <id>[/bold]          Resume specific session
  [bold]flexcoder providers[/bold]              Provider settings TUI
  [bold]flexcoder settings[/bold]               AI settings TUI
  [bold]flexcoder sessions[/bold]               Session browser TUI

[bold dim]Config:   ~/.flexcoder/config.toml[/bold dim]
[bold dim]Sessions: ~/.flexcoder/sessions/[/bold dim]
"""


class HelpScreen(ModalScreen):
    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("ctrl+h", "dismiss", "Close"),
        Binding("q",      "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-root"):
            yield Static(_TEXT, id="help-text")
            yield Button("Close  [Esc]", id="help-close", variant="primary")

    def on_button_pressed(self, _): self.dismiss()
    def on_key(self, e):
        if e.key in ("escape", "q"): self.dismiss()
