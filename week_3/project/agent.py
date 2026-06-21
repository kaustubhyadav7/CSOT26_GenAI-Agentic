"""
Research Desk — Week 3 Project
===============================
Class hierarchy:
  Agent       — brain: chat(), _run_loop(), dispatch(), sessions
  REPLAgent   — terminal REPL + one-shot CLI
  TUIAgent    — Textual UI (in tui.py)

Usage:
  python agent.py                              # REPLAgent.run()
  python agent.py "What is quantum computing?" # REPLAgent.run_once()
  python agent.py --tui                        # TUIAgent.run()
  python agent.py --session abc123 "continue"
"""
"""
Research Desk — Week 3 Project
"""
import os
import sys
import json
import uuid
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

from tools.web import web_search, web_fetch
from tools.papers import paper_search, read_paper
from tools.files import read_file, write_file, edit_file, list_files

SESSIONS_DIR = ".agent/sessions"
AGENTS_PATHS = ("AGENTS.md", ".agent/AGENTS.md")
MAX_ITERATIONS = 10

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "openai/gpt-oss-120b:free"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the full content of a web page.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description": "Search ML/CS papers on Hugging Face Papers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper",
            "description": "Read full content of a paper by arxiv ID.",
            "parameters": {
                "type": "object",
                "properties": {"arxiv_id": {"type": "string"}},
                "required": ["arxiv_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read lines from a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "read_lines": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in notes/.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file: replace, delete, or append lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string", "enum": ["replace", "delete", "append"]},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"},
                },
                "required": ["path", "operation", "start_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory within the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"},
                },
                "required": [],
            },
        },
    },
]

TOOL_REGISTRY = {
    "web_search": web_search,
    "web_fetch": web_fetch,
    "paper_search": paper_search,
    "read_paper": read_paper,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
}


def build_system_prompt() -> str:
    prompt = "You are Research Desk, a helpful research assistant."
    for path in AGENTS_PATHS:
        if os.path.exists(path):
            with open(path) as f:
                prompt += "\n\n" + f.read()
            break
    return prompt


class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.workspace = os.path.abspath(workspace)
        self.session_id = session_id or uuid.uuid4().hex[:8]
        session = self._load_session()
        if session:
            self.messages = session["messages"]
        else:
            self.messages = [{"role": "system", "content": build_system_prompt()}]

    def _load_session(self) -> dict | None:
        path = f"{SESSIONS_DIR}/{self.session_id}.json"
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def _save_session(self, title: str = "Untitled") -> None:
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        data = {
            "id": self.session_id,
            "title": title,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": self.messages,
        }
        with open(f"{SESSIONS_DIR}/{self.session_id}.json", "w") as f:
            json.dump(data, f, indent=2)

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        answer = self._run_loop()
        self._save_session()
        return answer

    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)

    def _run_loop(self) -> str:
        for _ in range(MAX_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=TOOLS,
            )
            msg = response.choices[0].message
            if msg.tool_calls:
                self.messages.append({
    "role": "assistant",
    "content": msg.content,
    "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
})
                for tc in msg.tool_calls:
                    self._emit("tool_call", name=tc.function.name)
                    result = self.dispatch(tc)
                    self.messages.append({
    "role": "assistant",
    "content": msg.content or "",
    "tool_calls": [
        {
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments,
            },
        }
        for tc in msg.tool_calls
    ],
})
            else:
                self.messages.append({"role": "assistant", "content": msg.content})
                return msg.content
        return "Max iterations reached."

    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            return json.dumps({"error": "Malformed tool arguments from model"})
        func = TOOL_REGISTRY.get(name)
        if func:
            try:
                return json.dumps(func(**args))
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": f"Unknown tool: {name}"})

    def _emit(self, event: str, **data) -> None:
        pass


class REPLAgent(Agent):
    def run(self) -> None:
        print(f"Research Desk [{self.session_id}] — /quit to exit")
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input or user_input in ("/quit", "/exit"):
                break
            print(self.chat(user_input))
            print()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] {data.get('name')}", file=sys.stderr)


def main():
    session_id = None
    args = sys.argv[1:]

    if "--tui" in args:
        from tui import TUIAgent
        TUIAgent().run()
        return

    if "--session" in args:
        idx = args.index("--session")
        session_id = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    agent = REPLAgent(session_id=session_id)

    if args:
        print(agent.run_once(" ".join(args)))
        return

    agent.run()


if __name__ == "__main__":
    main()