# Week 3 Submission — Research Desk

## What I Built

Research Desk is an upgraded version of week2 research agent,it also searches academic papers through the Hugging Face Papers API,also saves findings to notes/ as markdown files, and remembers every conversation. Basically, it picks up exactly where you left off.

## How It Works

The core is an Agent class that holds everything — the loop, the tools, the
session I/O. Unlike Week 2 where everything lived in one file, here the
main thing is separated from the UI. **REPLAgent** adds a terminal loop on
top of Agent. TUIAgent adds the Textual interface. The same Agent runs all
three modes:

    python agent.py "question"   — one shot, print answer, exit
    python agent.py              — interactive REPL
    python agent.py --tui        — Week 2 style Textual UI

The loop itself is the same **ReAct** pattern from Week 2 — send messages to the
model, if it wants a tool run it and feed the result back, repeat until it
gives a text answer. What's new is that every conversation is saved to
.agent/sessions/{id}.json after each chat() call, so nothing is ever lost.

## Memory

**Session memory** — the full conversation history saved to disk as JSON.
Each session has an ID, title, and timestamp. Can resume any past session
by passing --session <id>.

**Procedural memory** — AGENTS.md. On startup the agent reads this file and
appends it to the system prompt. It tells the agent things like: use
paper_search for ML questions, save findings to notes/, cite sources inline.

**Research notes** — the agent writes its own findings to notes/ via
write_file. These persist across sessions. Over time the notes/ folder becomes
a research archive the agent can also read back with read_file.

## Tools

Eight tools total:

- web_search — Serper API, from Week 2
- web_fetch — trafilatura page reader, from Week 2
- paper_search — searches Hugging Face Papers index by keyword
- read_paper — fetches full markdown content of a paper by arxiv ID
- read_file — sandboxed file reader with line numbers and has_more
- write_file — writes to notes/ 
- edit_file — replace, delete, or append lines with diff preview
- list_files — lists files in a directory

The AGENTS.md rules tell the agent when to use which: paper_search for ML
research questions, web_search for everything else, never guess arxiv IDs.

## What I Found Interesting

The AGENTS.md pattern. The idea that you can control an agent's entire
behaviour just by loading a markdown file into the system prompt — no code
changes — is surprisingly powerful. The agent started citing papers correctly
and saving notes automatically just because the rules file told it to.

## Challenges

The main pain point was message serialization. When the model returns a tool
call, appending the raw ChatCompletionMessage object to the history breaks JSON
serialization when saving the session, and some OpenRouter providers also
reject it on the next API call. The fix was manually reconstructing the message
as a plain dict with only id, type, and function keys — no extra fields the
provider doesn't expect.

Free model quotas also ran out mid-session a couple of times, which meant
switching models during the operation.

## How to Run

1. `pip install openai python-dotenv requests trafilatura textual`
2. Create `.env` with `OPENROUTER_API_KEY` and `SERPER_API_KEY`
3. `python agent.py "question"` — one-shot research query
4. `python agent.py` — interactive REPL, /quit to exit
5. `python agent.py --tui` — full Textual UI
6. `python agent.py --session <id>` — resume a past session