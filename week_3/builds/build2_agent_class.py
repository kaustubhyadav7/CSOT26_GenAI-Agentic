"""
Build 2: Agent + REPLAgent
===========================
Agent = brain (loop, tools, sessions). REPLAgent = terminal UI.

Before running:
  mkdir -p notes

Tasks:
  1. Agent — chat(), run_once(), _run_loop(), dispatch(), _emit(), session I/O
  2. REPLAgent(Agent) — run() interactive loop
  3. resolve_path, read_file, write_file, list_files, edit_file
  4. main() — one-shot: python build2_agent_class.py "hello"

TUIAgent comes in the project (tui.py). No Textual imports here.
"""

import os
import sys
import json
import glob as glob_module
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", "project", ".env"))

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_ITERATIONS = 10
MAX_READ_CHARS = 12_000

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "openai/gpt-oss-20b:free"

# --- File tools ---

def resolve_path(path: str) -> str:
    full = os.path.normpath(os.path.join(WORKSPACE_ROOT, path))
    if not full.startswith(WORKSPACE_ROOT):
        raise ValueError(f"Path outside workspace: {path}")
    return full

def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> dict:
    try:
        full = resolve_path(path)
        with open(full, encoding="utf-8") as f:
            all_lines = f.readlines()
        end = start_line - 1 + read_lines
        chunk = all_lines[start_line - 1:end]
        numbered = "".join(f"{start_line + i:4}: {l}" for i, l in enumerate(chunk))
        return {
            "content": numbered[:MAX_READ_CHARS],
            "has_more": end < len(all_lines),
            "total_lines": len(all_lines),
        }
    except Exception as e:
        return {"error": str(e)}

def write_file(path: str, content: str) -> dict:
    try:
        full = resolve_path(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return {"content": f"Written to {path}"}
    except Exception as e:
        return {"error": str(e)}

def edit_file(path: str, operation: str, start_line: int,
              end_line: int | None = None, content: str | None = None) -> dict:
    try:
        full = resolve_path(path)
        with open(full, encoding="utf-8") as f:
            lines = f.readlines()
        if operation == "replace":
            lines[start_line - 1:end_line] = [content + "\n"]
        elif operation == "delete":
            del lines[start_line - 1:end_line]
        elif operation == "append":
            lines.append(content + "\n")
        else:
            return {"error": f"Unknown operation: {operation}"}
        with open(full, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return {"content": f"Edited {path} ({operation})"}
    except Exception as e:
        return {"error": str(e)}

def list_files(path: str = ".", pattern: str = "*") -> dict:
    try:
        full = resolve_path(path)
        matches = glob_module.glob(os.path.join(full, pattern))
        names = [os.path.relpath(m, WORKSPACE_ROOT) for m in matches]
        return {"content": "\n".join(names)}
    except Exception as e:
        return {"error": str(e)}

# --- Tool schemas ---

TOOLS = [
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
            "description": "Write content to a file in the workspace.",
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

# --- Agent ---

def build_system_prompt() -> str:
    prompt = "You are Research Desk, a helpful research assistant."
    for path in ("AGENTS.md", ".agent/AGENTS.md"):
        if os.path.exists(path):
            with open(path) as f:
                prompt += "\n\n" + f.read()
            break
    return prompt

class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.workspace = os.path.abspath(workspace)
        self.session_id = session_id or self._new_session_id()
        session = self._load_session()
        if session:
            self.messages = session["messages"]
        else:
            self.messages = [{"role": "system", "content": build_system_prompt()}]

    def _new_session_id(self) -> str:
        import uuid
        os.makedirs(".agent/sessions", exist_ok=True)
        return uuid.uuid4().hex[:8]

    def _load_session(self) -> dict | None:
        path = f".agent/sessions/{self.session_id}.json"
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return None

    def _save_session(self, title: str = "Untitled") -> None:
        from datetime import datetime, timezone
        os.makedirs(".agent/sessions", exist_ok=True)
        data = {
            "id": self.session_id,
            "title": title,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": self.messages,
        }
        with open(f".agent/sessions/{self.session_id}.json", "w") as f:
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
                self.messages.append(msg.model_dump())
                for tc in msg.tool_calls:
                    self._emit("tool_call", name=tc.function.name)
                    result = self.dispatch(tc)
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                self.messages.append({"role": "assistant", "content": msg.content})
                return msg.content

        return "Max iterations reached."

    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        tools_map = {
            "read_file": read_file,
            "write_file": write_file,
            "edit_file": edit_file,
            "list_files": list_files,
        }
        if name in tools_map:
            return json.dumps(tools_map[name](**args))
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
    agent = REPLAgent()
    if len(sys.argv) > 1:
        print(agent.run_once(" ".join(sys.argv[1:])))
        return
    agent.run()

if __name__ == "__main__":
    main()