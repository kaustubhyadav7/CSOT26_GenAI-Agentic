"""
Paper search and read tools — Hugging Face Papers API (arXiv index).

Implement:
  - paper_search(query, limit) -> {papers: [{arxiv_id, title, abstract, url}, ...]}
  - read_paper(arxiv_id) -> {title, abstract, content, url, ...}

API docs: week_3/3_paper_tools.md
"""
import re
import requests

HF_BASE = "https://huggingface.co"
MAX_CONTENT = 12_000


def _normalize_id(arxiv_id: str) -> str:
    """Strip URL prefixes and version suffixes. '2205.14135v2' -> '2205.14135'"""
    arxiv_id = arxiv_id.strip()
    # Strip URL prefix if present
    arxiv_id = re.sub(r".*arxiv\.org/(abs|pdf)/", "", arxiv_id)
    # Strip version suffix
    arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
    return arxiv_id


def paper_search(query: str, limit: int = 5) -> dict:
    try:
        resp = requests.get(
            f"{HF_BASE}/api/papers/search",
            params={"q": query, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        papers = []
        for item in results:
            # Handle both {paper: {...}} and flat {...} shapes
            p = item.get("paper", item)
            papers.append({
                "arxiv_id": p.get("id", ""),
                "title": p.get("title", ""),
                "summary": (p.get("summary", "") or "")[:300],
            })
        return {"content": papers}
    except Exception as e:
        return {"error": str(e)}


def read_paper(arxiv_id: str) -> dict:
    arxiv_id = _normalize_id(arxiv_id)
    try:
        # Get metadata
        meta_resp = requests.get(
            f"{HF_BASE}/api/papers/{arxiv_id}",
            timeout=10,
        )
        if meta_resp.status_code == 404:
            return {"error": f"Paper {arxiv_id} not found on HF. Try web_fetch on arxiv.org/abs/{arxiv_id}"}
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        # Try markdown content
        md_resp = requests.get(
            f"{HF_BASE}/papers/{arxiv_id}.md",
            timeout=10,
        )
        if md_resp.status_code == 200:
            content = md_resp.text[:MAX_CONTENT]
        else:
            # Fall back to abstract
            content = meta.get("summary", "No content available.")

        return {
            "arxiv_id": arxiv_id,
            "title": meta.get("title", ""),
            "content": content,
        }
    except Exception as e:
        return {"error": str(e)}