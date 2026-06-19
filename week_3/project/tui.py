"""
TUIAgent — full-screen Textual UI inheriting from Agent.

Usage:
  python agent.py --tui

Tasks:
  1. class TUIAgent(Agent) — override _emit() for tool log panel
  2. class ResearchDeskApp(App) — layout, input, key bindings
  3. on_input_submitted -> worker -> self.chat() (inherited from Agent)
  4. Ctrl+L / Ctrl+K / Ctrl+Q from Week 2
"""

import sys
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog

from agent import Agent


class TUIAgent(Agent, App):
    TITLE = "Research Desk"
    CSS = """
    #chat { height: 1fr; border: solid $primary; padding: 0 1; }
    #tools { height: 8; border: solid $secondary; padding: 0 1; }
    Input { dock: bottom; height: 3; }
    """
    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display"),
        Binding("ctrl+k", "clear_history", "Clear history"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self):
        Agent.__init__(self)
        App.__init__(self)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="chat", wrap=True, markup=True)
        yield RichLog(id="tools", wrap=True, markup=True)
        yield Input(placeholder="Ask a research question...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat", RichLog).write(
            f"[bold green]Research Desk [{self.session_id}] ready.[/bold green]\n"
        )
        self.query_one("#tools", RichLog).write("[dim]Tool activity will appear here.[/dim]")
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q:
            return
        event.input.clear()
        self.query_one("#chat", RichLog).write(f"[bold cyan][You][/bold cyan] {q}\n")
        self.query_one("#tools", RichLog).write("[yellow]Researching...[/yellow]")
        self.run_worker(lambda: self._respond(q), thread=True)

    def _respond(self, q: str) -> None:
        chat = self.query_one("#chat", RichLog)
        tools_log = self.query_one("#tools", RichLog)
        try:
            reply = self.chat(q)
            self.call_from_thread(chat.write, "[bold green][Agent][/bold green]")
            self.call_from_thread(chat.write, reply + "\n")
        except Exception as e:
            self.call_from_thread(chat.write, f"[bold red]Error:[/bold red] {str(e)[:200]}")

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            tools_log = self.query_one("#tools", RichLog)
            self.call_from_thread(tools_log.write, f"[blue]-> {data.get('name')}[/blue]")

    def action_clear_display(self) -> None:
        self.query_one("#chat", RichLog).clear()

    def action_clear_history(self) -> None:
        self.messages = self.messages[:1]
        self.query_one("#chat", RichLog).clear()
        self.query_one("#chat", RichLog).write("[bold yellow]History cleared.[/bold yellow]\n")