"""Tests for web_research helpers - pure logic only, no network calls."""

from __future__ import annotations

import pytest

from llm_examples.ui.web_research import (
    WebSource,
    _clean_text,
    _dedupe_sources,
    _duckduckgo_topic_items,
    research_context,
    research_sources,
)

# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------


def test_clean_text_empty_and_non_string() -> None:
    assert _clean_text("") == ""
    assert _clean_text(None) == ""
    assert _clean_text(42) == ""


def test_clean_text_strips_html_tags() -> None:
    assert _clean_text("<b>Hello</b> <em>world</em>") == "Hello world"


def test_clean_text_collapses_whitespace() -> None:
    assert _clean_text("  hello   world  ") == "hello world"


def test_clean_text_decodes_html_entities() -> None:
    assert _clean_text("&quot;quoted&quot; &amp; more") == '"quoted" & more'


def test_clean_text_strips_tags_then_decodes_entities() -> None:
    result = _clean_text('<p class="x">&amp;test&quot;</p>')
    assert result == '&test"'


# ---------------------------------------------------------------------------
# _duckduckgo_topic_items
# ---------------------------------------------------------------------------


def test_duckduckgo_topic_items_none_returns_empty() -> None:
    assert _duckduckgo_topic_items(None) == []


def test_duckduckgo_topic_items_non_list_returns_empty() -> None:
    assert _duckduckgo_topic_items("bad") == []
    assert _duckduckgo_topic_items(42) == []


def test_duckduckgo_topic_items_flat_list() -> None:
    items = [
        {"Text": "Item one", "FirstURL": "https://a.com"},
        {"Text": "Item two", "FirstURL": "https://b.com"},
    ]
    result = _duckduckgo_topic_items(items)
    assert result == items


def test_duckduckgo_topic_items_skips_non_dict() -> None:
    result = _duckduckgo_topic_items(["string", None, 42, {"Text": "ok", "FirstURL": "x"}])
    assert len(result) == 1
    assert result[0]["Text"] == "ok"


def test_duckduckgo_topic_items_expands_nested_topics() -> None:
    nested = [
        {
            "Topics": [
                {"Text": "nested-a", "FirstURL": "https://na.com"},
                {"Text": "nested-b", "FirstURL": "https://nb.com"},
            ]
        }
    ]
    result = _duckduckgo_topic_items(nested)
    assert len(result) == 2
    assert result[0]["Text"] == "nested-a"


def test_duckduckgo_topic_items_deep_nesting() -> None:
    deep = [
        {
            "Topics": [
                {
                    "Topics": [
                        {"Text": "deep", "FirstURL": "https://deep.com"},
                    ]
                }
            ]
        }
    ]
    result = _duckduckgo_topic_items(deep)
    assert len(result) == 1
    assert result[0]["Text"] == "deep"


# ---------------------------------------------------------------------------
# _dedupe_sources
# ---------------------------------------------------------------------------


def test_dedupe_sources_empty() -> None:
    assert _dedupe_sources([], limit=5) == []


def test_dedupe_sources_removes_duplicate_urls() -> None:
    items = [
        WebSource(title="A", url="https://a.com", snippet="a"),
        WebSource(title="B", url="https://a.com", snippet="b"),
        WebSource(title="C", url="https://c.com", snippet="c"),
    ]
    result = _dedupe_sources(items, limit=10)
    urls = [item.url for item in result]
    assert urls == ["https://a.com", "https://c.com"]


def test_dedupe_sources_respects_limit() -> None:
    items = [
        WebSource(title=str(i), url=f"https://site{i}.com", snippet="s")
        for i in range(10)
    ]
    result = _dedupe_sources(items, limit=3)
    assert len(result) == 3


def test_dedupe_sources_skips_blank_url() -> None:
    items = [
        WebSource(title="blank", url="  ", snippet="x"),
        WebSource(title="ok", url="https://ok.com", snippet="y"),
    ]
    result = _dedupe_sources(items, limit=5)
    assert len(result) == 1
    assert result[0].url == "https://ok.com"


def test_dedupe_sources_is_case_insensitive_on_url() -> None:
    items = [
        WebSource(title="A", url="https://A.COM/path", snippet="a"),
        WebSource(title="B", url="https://a.com/path", snippet="b"),
    ]
    result = _dedupe_sources(items, limit=5)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# research_sources
# ---------------------------------------------------------------------------


def test_research_sources_empty_query_returns_empty() -> None:
    result = research_sources("   ")
    assert result == []


def test_research_sources_raises_when_both_providers_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "llm_examples.ui.web_research._duckduckgo_sources",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("ddg down")),
    )
    monkeypatch.setattr(
        "llm_examples.ui.web_research._wikipedia_sources",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("wiki down")),
    )
    with pytest.raises(RuntimeError, match="Web research failed"):
        research_sources("anything")


def test_research_sources_returns_deduped_from_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ddg_rows = [WebSource(title="DDG", url="https://d.com", snippet="d")]
    wiki_rows = [WebSource(title="Wiki", url="https://w.com", snippet="w")]
    monkeypatch.setattr(
        "llm_examples.ui.web_research._duckduckgo_sources",
        lambda *_a, **_kw: ddg_rows,
    )
    monkeypatch.setattr(
        "llm_examples.ui.web_research._wikipedia_sources",
        lambda *_a, **_kw: wiki_rows,
    )
    result = research_sources("test", limit=10)
    assert len(result) == 2


def test_research_sources_falls_back_to_wikipedia_when_ddg_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wiki_rows = [WebSource(title="Wiki", url="https://w.com", snippet="w")]
    monkeypatch.setattr(
        "llm_examples.ui.web_research._duckduckgo_sources",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("ddg down")),
    )
    monkeypatch.setattr(
        "llm_examples.ui.web_research._wikipedia_sources",
        lambda *_a, **_kw: wiki_rows,
    )
    result = research_sources("test", limit=5)
    assert result[0].title == "Wiki"


# ---------------------------------------------------------------------------
# research_context
# ---------------------------------------------------------------------------


def test_research_context_empty_results_returns_empty_strings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "llm_examples.ui.web_research.research_sources",
        lambda *_a, **_kw: [],
    )
    context, sources = research_context("any query")
    assert context == ""
    assert sources == ()


def test_research_context_formats_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        WebSource(title="Result One", url="https://r1.com", snippet="First snippet"),
        WebSource(title="Result Two", url="https://r2.com", snippet="Second snippet"),
    ]
    monkeypatch.setattr(
        "llm_examples.ui.web_research.research_sources",
        lambda *_a, **_kw: rows,
    )
    context, sources = research_context("query")
    assert "Web research context" in context
    assert "Result One" in context
    assert "URL: https://r1.com" in context
    assert "First snippet" in context
    assert len(sources) == 2
    assert sources[0].title == "Result One"
