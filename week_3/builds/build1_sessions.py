"""
Build 1: Session Store
========================
Save and resume conversations on disk. Load AGENTS.md into the system prompt.

Tasks:
  1. create_session() -> session_id
  2. save_session(session_id, messages, title?)
  3. load_session(session_id) -> {id, title, messages, ...}
  4. list_sessions() -> [{id, title, updated_at}, ...]
  5. build_system_prompt() -> base + AGENTS.md contents

Run twice: save a session in run 1, load it in run 2 and confirm messages restored.
"""

import json
import os
import uuid
from datetime import datetime, timezone

SESSIONS_DIR = ".agent/sessions"
AGENTS_PATHS = ("AGENTS.md", ".agent/AGENTS.md")

BASE_PROMPT = "You are Research Desk, a helpful research assistant."


def create_session() -> str:
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    return uuid.uuid4().hex[:8]


def save_session(session_id: str, messages: list, title: str = "Untitled") -> None:
    data = {
        "id": session_id,
        "title": title,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "messages": messages,
    }
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_session(session_id: str) -> dict:
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    with open(path) as f:
        return json.load(f)


def list_sessions() -> list[dict]:
    if not os.path.exists(SESSIONS_DIR):
        return []
    sessions = []
    for fname in os.listdir(SESSIONS_DIR):
        if fname.endswith(".json"):
            sid = fname[:-5]
            s = load_session(sid)
            sessions.append({"id": s["id"], "title": s["title"], "updated_at": s["updated_at"]})
    return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)


def build_system_prompt() -> str:
    prompt = BASE_PROMPT
    for path in AGENTS_PATHS:
        if os.path.exists(path):
            with open(path) as f:
                prompt += "\n\n" + f.read()
            break
    return prompt


if __name__ == "__main__":
    sid = create_session()
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": "What is a surface code?"},
        {"role": "assistant", "content": "A surface code is a type of quantum error correcting code."},
    ]
    save_session(sid, messages, title="Quantum error correction")
    print(f"Saved session: {sid}")
    print(f"All sessions: {list_sessions()}")
    print(f"Loaded: {load_session(sid)['title']}")
