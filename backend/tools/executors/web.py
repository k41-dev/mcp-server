#!/usr/bin/env python3
"""
web.py - Web-Tools
"""

import httpx
from bs4 import BeautifulSoup
import os
from typing import Dict, Any


def web_search(args: Dict[str, Any]) -> Dict[str, Any]:
    query = args.get("query", "").strip()
    if not query:
        return {"content": [{"type": "text", "text": "Error: query cannot be empty"}], "isError": True}

    searxng_url = os.getenv("SEARXNG_URL", "http://searxng:8080")

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(f"{searxng_url}/search", params={"q": query, "format": "json"})
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results", [])[:8]
        if not results:
            return {"content": [{"type": "text", "text": "No results found."}]}

        formatted = "\n".join([
            f"**{r.get('title', 'No title')}**\n{r.get('url', '')}\n{r.get('content', '')[:350]}\n"
            for r in results
        ])
        return {"content": [{"type": "text", "text": formatted}]}

    except httpx.RequestError as e:
        return {"content": [{"type": "text", "text": f"Connection error to SearXNG: {str(e)}"}], "isError": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Search error: {str(e)}"}], "isError": True}


def browse_page(args: Dict[str, Any]) -> Dict[str, Any]:
    BROWSERLESS_URL = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
    BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN", "")

    url = args.get("url", "").strip()
    if not url:
        return {"content": [{"type": "text", "text": "Error: url is required"}], "isError": True}

    timeout = args.get("timeout", 30000)
    extract_text = args.get("extract_text", True)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; MCP-Bot/1.0)"}

        with httpx.Client(timeout=timeout / 1000, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        if extract_text:
            soup = BeautifulSoup(resp.text, "lxml")

            # Entferne unnötige Elemente
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            text = text[:9000] + "\n\n[... truncated]" if len(text) > 9000 else text

            return {
                "content": [{
                    "type": "text",
                    "text": f"**URL:** {url}\n\n{text}"
                }]
            }
        else:
            return {
                "content": [{
                    "type": "text",
                    "text": resp.text[:12000]
                }]
            }

    except httpx.RequestError as e:
        return {"content": [{"type": "text", "text": f"Connection error: {str(e)}"}], "isError": True}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Browse error: {str(e)}"}], "isError": True}