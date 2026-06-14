# Week2 Submission- ResearchBot (your own Perplexity)

This is a terminal based research agent built on top of openrouter.ai. It searches the web, reads the relevant pages, and synthesises a cited answer, all running inside a full-screen terminal UI. It can also search academic papers through the AlphaXiv MCP server.

# HOW IT WORKS?????

The whole thing revolves around the agent loop in run_agent. Unlike week 1 where the model just talked, here the model can actually do things using tools. The user's question plus a list of tools is sent to the model, and the model decides whether it needs a tool or can answer directly. This is checked using finish_reason- if it comes back as **tool_calls** the model wants a tool, if it's "stop" the model is done and gives the final answer.

There are two tools- **web_search** which hits the Serper API to get real Google results, and **web_fetch** which downloads a full page and uses trafilatura to strip the messy HTML down to readable text. When the model asks for a tool, dispatch runs it and the result is fed back as a tool message, then the loop goes again. So the model can search, read, search again, and keep going until it has enough to answer.

All of this is wrapped in a Textual TUI with two panels- a chat panel for the conversation and a separate panel that shows the tool activity live. The API call runs on a background thread using run_worker so the UI doesn't freeze while the model is thinking.

For papers, there is a separate script alphaxiv_search_cli.py that connects to the AlphaXiv MCP server and uses discover_papers to pull research papers on a topic.

# Key Decisions

*Truncating fetched pages* (MAX_CHARS = 8000): A single web page can be 50,000+ characters. Sending all of that floods the model's context and wastes tokens, so I cut the fetched text to 8000 characters before handing it over.

*System prompt to stop over-searching*: Early on the agent kept searching endlessly- search, fetch, search again, never deciding it had enough, and hitting the iteration cap with no answer. So I rewrote the system prompt to tell it to do at most 2-3 tool calls and then commit to an answer, instead of chasing the perfect source.

*MCP as a separate script*: Since we only need to connect to an MCP server, not build one for this week, and AlphaXiv needs OAuth which wasn't covered in the lessons, I used the OAuth helper to run the paper search as its own command-line tool rather than forcing it into the main agent.

# Note on Structure

The main agent (web search + fetch + loop + TUI) is in **agent.py**, evolved step by step from the starter- base call working, then tools, then tested from the command line, then the TUI last. The AlphaXiv MCP paper search is kept in **alphaxiv_search_cli.py** since it needs its own OAuth flow.

# Challenges / What I Learned

The biggest lesson this week was that the code being correct doesn't mean the system works. My agent worked perfectly from the command line- searched, read pages, gave clean cited answers. But in the TUI the answer sometimes wouldn't show up in the chat panel. I spent a long time thinking it was some display bug, but after isolating it- running the engine on its own (worked fine) and logging the reply to a file (the answer was there, correct and cited)- the real cause turned out to be free-tier API calls hanging mid-loop, with the background thread showing it as a blank panel. The actual skill here was isolating where the failure lived instead of guessing.

I also learned that bigger models aren't always better. The small free models were fine for plain chat in the builds, but choked when web_fetch dumped a full page into the context- they'd stop producing an answer. The larger model handled the same loop fine.

The MCP part taught me about OAuth. AlphaXiv returns a 401 unless you authenticate through a proper OAuth 2.0 browser flow, which was more involved than the lesson's example. My first attempt timed out because creating the account took too long and the callback server stopped listening, but the second run caught it and pulled real papers.

# What I'd Improve


Add retry/timeout wrappers on the model call so a stuck free-tier call retries itself instead of freezing the TUI- that's the one thing still standing between this and a TUI that works reliably every time.

Wire the AlphaXiv paper search directly into the main agent loop as a tool, instead of a separate script.

Possibly default to a stronger model since small ones often just freeze.


# How to Run


1. pip install openai python-dotenv requests markdownify trafilatura textual (for the main agent)
2. pip install mcp httpx (extra, only needed for the AlphaXiv paper search)
3. Create a .env file with:
    OPENROUTER_API_KEY=your_key
    SERPER_API_KEY=your_key
4. Run the research agent: python agent.py
5. Type a question and press Enter. Ctrl+L clears the display, Ctrl+K clears history, Ctrl+Q quits.
6. For paper search: python alphaxiv_search_cli.py "your topic" - on first run it opens a browser for AlphaXiv login (OAuth), after that it remembers you.