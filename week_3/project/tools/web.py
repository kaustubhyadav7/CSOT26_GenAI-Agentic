"""
Web search and fetch tools — carry forward from Week 2.

Implement or copy from your week_2/project/:
  - web_search(query) — Serper
  - web_fetch(url) — requests + trafilatura/markdownify
"""

import os
import json
import requests
import trafilatura

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
MAX_CHARS = 8_000


def web_search(query: str, num_results: int = 5) -> dict:
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
    return {"content": results}


def web_fetch(url: str) -> dict:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
        html = requests.get(url, headers=headers, allow_redirects=True, timeout=10).text
        text = trafilatura.extract(html, include_comments=False, include_tables=True) or ""
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[...truncated]"
        return {"content": text}
    except Exception as e:
        return {"error": f"Error fetching {url}: {e}"}
