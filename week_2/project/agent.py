"""
ResearchBot: Week 2 Project Starter
======================================
This file currently makes a basic single-turn call to OpenRouter.
Your job is to evolve it into a full research agent with:
  - Web search and web fetch tools (using OpenAI SDK tool calling)
  - An agent loop that iterates until the model stops requesting tools
  - A Textual TUI with a chat panel and a tool activity log
  - Keyboard shortcuts: Ctrl+L (clear display), Ctrl+K (clear history), Ctrl+Q (quit),
    and at least one more of your choice

Start by getting this file working, then add tools, then add the TUI.
Don't try to build everything at once.
"""

import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import trafilatura
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from rich.markup import escape

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
    timeout=30
)

MODEL = "openai/gpt-oss-20b:free"
SERPER_API_KEY = os.environ["SERPER_API_KEY"]


def call_model(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content
def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web. Returns a list of {title, link, snippet} dicts."""
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": num_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })
    return results

MAX_CHARS = 8000

def web_fetch(url: str) -> str:
    """Fetch a web page and return cleaned text."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
        html = requests.get(url, headers=headers, allow_redirects=True, timeout=10).text
        text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[...truncated]"
        return text
    except Exception as e:
        return f"[Error fetching {url}: {e}]"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information. Use for recent events, facts, or anything uncertain. Returns title, URL, snippet for each result.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "The search query. Be specific."}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the full content of a web page. Use after web_search to read a result in detail.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "The full URL including https://"}},
                "required": ["url"],
            },
        },
    },
]

TOOL_REGISTRY = {"web_search": web_search, "web_fetch": web_fetch}

import sys

def dispatch(tool_call) -> str:
    name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    func = TOOL_REGISTRY.get(name)
    if func is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        result = func(**arguments)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e)})


SYSTEM_PROMPT = """You are a research assistant. When the user asks a question, use web_search to find sources, then web_fetch to read the most relevant one or two, then ANSWER.

Important rules:
- Do at most 2-3 tool calls total, then synthesize an answer from what you found.
- Do not keep searching for the perfect source. Answer with what you have, noting any uncertainty.
- Always cite the URLs you used.
- After you have enough to give a reasonable answer, STOP calling tools and respond."""

MAX_ITERATIONS = 10

def run_agent(messages: list, on_tool=None) -> str:
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        if finish_reason == "tool_calls":
            messages.append(message)
            for tool_call in message.tool_calls:
                if on_tool:
                    on_tool(f"{tool_call.function.name}({tool_call.function.arguments})")
                result = dispatch(tool_call)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
            continue

        if finish_reason == "stop":
            return message.content

    return "[Agent stopped after max iterations]"

class ResearchApp(App):
    TITLE = "ResearchBot — your terminal Perplexity"
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
        super().__init__()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="chat", wrap=True, markup=True)
        yield RichLog(id="tools", wrap=True, markup=True)
        yield Input(placeholder="Ask a research question and press Enter...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat", RichLog).write("[bold green]ResearchBot ready.[/bold green] Ask me anything.\n")
        self.query_one("#tools", RichLog).write("[dim]Tool activity will appear here.[/dim]")
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q:
            return
        event.input.clear()
        self.query_one("#chat", RichLog).write(f"[bold cyan][You][/bold cyan] {q}\n")
        self.messages.append({"role": "user", "content": q})
        self.query_one("#tools", RichLog).write("[yellow]Researching...[/yellow]")
        self.run_worker(self._respond, thread=True)

    def _respond(self) -> None:
        chat = self.query_one("#chat", RichLog)
        tools = self.query_one("#tools", RichLog)
        try:
            def report(activity):
                self.call_from_thread(tools.write, f"[blue]-> {activity}[/blue]")
            reply = run_agent(self.messages, on_tool=report)
            if not reply:
                reply = "[No answer returned]"
            self.messages.append({"role": "assistant", "content": reply})
            safe_reply = str(reply).encode("ascii", "ignore").decode("ascii")
            self.call_from_thread(chat.write, "[bold green][Agent][/bold green]")
            self.call_from_thread(chat.write, safe_reply)
        except Exception as e:
            self.call_from_thread(chat.write, f"[bold red]Error:[/bold red] {str(e)[:200]}")

    def action_clear_display(self) -> None:
        self.query_one("#chat", RichLog).clear()

    def action_clear_history(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.query_one("#chat", RichLog).clear()
        self.query_one("#chat", RichLog).write("[bold yellow]History cleared.[/bold yellow]\n")


if __name__ == "__main__":
    ResearchApp().run()