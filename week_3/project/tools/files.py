"""
Sandboxed file tools — see week_3/2_agent_class.md

Implement:
  - resolve_path
  - read_file(path, start_line=1, read_lines=200)  — numbered lines, has_more
  - write_file(path, content)
  - edit_file(path, operation, start_line, end_line?, content?)  — replace | delete | append
  - list_files(path, pattern)
"""

import os
import glob as glob_module

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_READ_CHARS = 12_000


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
