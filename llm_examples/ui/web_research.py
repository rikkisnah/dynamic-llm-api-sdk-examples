"""Tier 5: Lightweight web research helpers for chat context."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

_REQUEST_TIMEOUT = 12.0
_USER_AGENT = "dynamic-llm-api-sdk-examples/1.0 (+https://github.com/rikkisnah)"


@dataclass(frozen=True, slots=True)
class WebSource:
    title: str
    url: str
    snippet: str


def _clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    return " ".join(text.split())


def _duckduckgo_sources(query: str, limit: int) -> list[WebSource]:
    response = httpx.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_html": "1",
            "no_redirect": "1",
            "skip_disambig": "1",
        },
        timeout=_REQUEST_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    )
    response.raise_for_status()
    payload = response.json()
    rows: list[WebSource] = []
    abstract = _clean_text(payload.get("AbstractText"))
    abstract_url = _clean_text(payload.get("AbstractURL"))
    heading = _clean_text(payload.get("Heading")) or "DuckDuckGo"
    if abstract and abstract_url:
        rows.append(WebSource(title=heading, url=abstract_url, snippet=abstract))

    for item in _duckduckgo_topic_items(payload.get("RelatedTopics")):
        if len(rows) >= limit:
            break
        text = _clean_text(item.get("Text"))
        url = _clean_text(item.get("FirstURL"))
        if text and url:
            rows.append(WebSource(title="DuckDuckGo Topic", url=url, snippet=text))
    return rows[:limit]


def _duckduckgo_topic_items(raw_topics: object) -> list[dict[str, object]]:
    if not isinstance(raw_topics, list):
        return []
    queue: list[object] = list(raw_topics)
    rows: list[dict[str, object]] = []
    while queue:
        item = queue.pop(0)
        if not isinstance(item, dict):
            continue
        nested = item.get("Topics")
        if isinstance(nested, list):
            queue.extend(nested)
            continue
        rows.append(item)
    return rows


def _wikipedia_sources(query: str, limit: int) -> list[WebSource]:
    response = httpx.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "utf8": "1",
            "format": "json",
            "srlimit": str(limit),
        },
        timeout=_REQUEST_TIMEOUT,
        headers={"User-Agent": _USER_AGENT},
    )
    response.raise_for_status()
    payload = response.json()
    query_payload = payload.get("query")
    if not isinstance(query_payload, dict):
        return []
    search_rows = query_payload.get("search")
    if not isinstance(search_rows, list):
        return []
    rows: list[WebSource] = []
    for item in search_rows:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title")) or "Wikipedia"
        snippet = _clean_text(item.get("snippet"))
        page_id = item.get("pageid")
        if isinstance(page_id, int):
            url = f"https://en.wikipedia.org/?curid={page_id}"
        else:
            continue
        if snippet:
            rows.append(WebSource(title=title, url=url, snippet=snippet))
    return rows[:limit]


def _dedupe_sources(items: list[WebSource], limit: int) -> list[WebSource]:
    seen: set[str] = set()
    rows: list[WebSource] = []
    for item in items:
        key = item.url.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(item)
        if len(rows) >= limit:
            break
    return rows


def research_sources(query: str, *, limit: int = 5) -> list[WebSource]:
    """Return normalized web sources for a query.

    This function is best-effort and intentionally tolerant: it raises only when
    both providers fail, so callers can degrade gracefully.
    """
    cleaned = " ".join(query.split())
    if not cleaned:
        return []
    errors: list[Exception] = []
    rows: list[WebSource] = []
    try:
        rows.extend(_duckduckgo_sources(cleaned, limit))
    except Exception as exc:  # pragma: no cover - network behavior varies
        errors.append(exc)
    try:
        rows.extend(_wikipedia_sources(cleaned, limit))
    except Exception as exc:  # pragma: no cover - network behavior varies
        errors.append(exc)
    deduped = _dedupe_sources(rows, limit)
    if deduped:
        return deduped
    if errors:
        raise RuntimeError(f"Web research failed ({len(errors)} source errors).") from errors[0]
    return []


def research_context(query: str, *, limit: int = 5) -> tuple[str, tuple[WebSource, ...]]:
    """Build prompt-ready web research context and source list."""
    rows = research_sources(query, limit=limit)
    if not rows:
        return "", ()
    lines: list[str] = [
        "Web research context (summarized):",
        "Use these findings as references and cite relevant URLs in your answer.",
    ]
    for idx, item in enumerate(rows, start=1):
        lines.append(f"{idx}. {item.title}")
        lines.append(f"   URL: {item.url}")
        lines.append(f"   Snippet: {item.snippet}")
    return "\n".join(lines), tuple(rows)
