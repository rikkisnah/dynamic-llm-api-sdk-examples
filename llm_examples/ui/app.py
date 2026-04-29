"""Tier 5: Streamlit UI rendered from capability registry."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import escape
from time import monotonic
from typing import ClassVar, Literal

try:
    import streamlit as st
except Exception:  # pragma: no cover - optional dependency fallback for constrained envs

    class _StreamlitStub:
        session_state: ClassVar[dict[str, object]] = {}

        def __getattr__(self, _name: str) -> Callable[..., object]:
            def _missing(*_: object, **__: object) -> object:
                raise RuntimeError("streamlit is not installed in this environment.")

            return _missing

    st = _StreamlitStub()  # type: ignore[assignment]

from llm_examples.capabilities import CAPABILITIES, Capability, capability_by_name
from llm_examples.config import (
    get_app_version,
    get_provider_config,
    provider_env_names,
    resolve_default_provider,
)
from llm_examples.domain_types import LLMError, ProviderName
from llm_examples.registry import PROVIDERS
from llm_examples.services import check_connection, list_models, run_prompt, stream_prompt
from llm_examples.ui.chat_page import render_chat_page
from llm_examples.ui.helpers import pretty_json, to_json_payload
from llm_examples.ui.helpers import prompt_option_label as format_prompt_option_label
from llm_examples.ui.state import (
    PageName,
    add_prompt_history,
    append_ui_call_log,
    clear_prompt_history,
    clear_ui_call_log,
    get_latest_models,
    get_output_mode,
    get_prompt_history,
    get_selected_page,
    get_selected_provider,
    get_ui_call_log,
    persist_session_state,
    set_latest_models,
    set_output_mode,
    set_selected_provider,
)

logger = logging.getLogger(__name__)

UI_PARAM_BINDINGS: Mapping[str, tuple[str, ...]] = {
    "providers": (),
    "list-models": ("provider",),
    "run": ("provider", "model", "prompt", "prompt-file", "system", "max-tokens", "stream"),
    "check": ("provider",),
}

QUOTES: tuple[tuple[str, str, str], ...] = (
    ("Famous", "Stay hungry, stay foolish.", "Steve Jobs"),
    ("Funny", "I can resist everything except temptation.", "Oscar Wilde"),
    ("Bible", "Let all that you do be done in love.", "1 Corinthians 16:14"),
    ("Hindu Epic", "You have a right to action, not to its fruits.", "Bhagavad Gita 2.47"),
    ("Famous", "Simplicity is the ultimate sophistication.", "Leonardo da Vinci"),
    ("Funny", "Always forgive your enemies; nothing annoys them so much.", "Oscar Wilde"),
    ("Bible", "A gentle answer turns away wrath.", "Proverbs 15:1"),
    ("Hindu Epic", "The mind is restless, but it can be trained.", "Bhagavad Gita 6.35"),
)

OutputMode = Literal["txt", "json"]
PAGE_OPTIONS: tuple[PageName, PageName, PageName] = ("Chat", "API", "Logs")
DEFAULT_PAGE: PageName = "Chat"
API_REPLY_SCROLL_HEIGHT = 340
API_REPLY_SCROLL_CHAR_THRESHOLD = 2_000
API_REPLY_SCROLL_LINE_THRESHOLD = 24


@dataclass(frozen=True, slots=True)
class RunFormInput:
    model: str
    prompt: str
    prompt_file: str
    system: str
    max_tokens: int
    stream: bool


@dataclass(frozen=True, slots=True)
class RunProgress:
    placeholder: object
    started_at: float


def _show_text(mode: OutputMode) -> bool:
    return mode == "txt"


def _show_json(mode: OutputMode) -> bool:
    return mode == "json"


def _should_scroll_api_reply(text: str) -> bool:
    lines = text.splitlines()
    if len(text) >= API_REPLY_SCROLL_CHAR_THRESHOLD:
        return True
    return len(lines) >= API_REPLY_SCROLL_LINE_THRESHOLD


def _render_api_copy_block(text: str) -> None:
    st.caption("Copy-ready text")
    st.code(text, language=None)


def _render_api_text_response(text: str) -> str:
    rendered = text.strip() or "[No response text returned.]"
    if _should_scroll_api_reply(rendered):
        with st.container(height=API_REPLY_SCROLL_HEIGHT):
            st.markdown(rendered)
    else:
        st.markdown(rendered)
    _render_api_copy_block(rendered)
    return rendered


def _render_run_progress(provider: ProviderName, model: str) -> RunProgress:
    status_line = st.empty()
    started_at = monotonic()
    status_line.info(f"Calling `{provider}` / `{model}`...")
    return RunProgress(placeholder=status_line, started_at=started_at)


def _load_provider_model_options(provider: ProviderName) -> list[str]:
    model_options = get_latest_models(provider)
    if model_options:
        return model_options
    try:
        model_options = [model.id for model in list_models(provider)]
        set_latest_models(provider, model_options)
    except LLMError:
        return []
    return model_options


def _prompt_history_scope_for_run(provider: ProviderName) -> str:
    return f"run:{provider}"


def _apply_dark_mode() -> None:
    st.markdown(
        """
<style>
:root { color-scheme: dark; }
[data-testid="stAppViewContainer"] { background-color: #0f1117; color: #e7e9ee; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background-color: #141824; }
[data-testid="stForm"] {
  background-color: #141824;
  border: 1px solid #2a2f3d;
  border-radius: 8px;
  padding: 12px;
}
.chat-wrap {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  word-break: break-word;
  line-height: 1.5;
}
[data-testid="stChatMessage"] {
  padding-top: 0.2rem;
  padding-bottom: 0.2rem;
}
[data-testid="stChatMessageContent"] {
  border: 1px solid #2a2f3d;
  border-radius: 10px;
  background-color: #101624;
  padding: 0.55rem 0.8rem;
}
.chat-empty {
  margin-top: 12vh;
  margin-bottom: 0.75rem;
  text-align: center;
  font-size: 2rem;
  color: #e7e9ee;
}
.chat-subtle {
  margin-bottom: 7vh;
  text-align: center;
  color: #9ca4b5;
}
.quote-line {
  white-space: nowrap;
  overflow-x: auto;
  overflow-y: hidden;
  line-height: 1.5;
  color: #c8cdd8;
}
</style>
        """,
        unsafe_allow_html=True,
    )


def _current_quote_index() -> int:
    stored = st.session_state.get("quote_index")
    if isinstance(stored, int) and 0 <= stored < len(QUOTES):
        return stored
    fallback = date.today().toordinal() % len(QUOTES)
    st.session_state["quote_index"] = fallback
    return fallback


def _quote_for_today() -> tuple[str, str, str]:
    return QUOTES[_current_quote_index()]


def _render_quote() -> None:
    controls_left, controls_right = st.columns([5, 1])
    if controls_right.button(
        " ",
        icon=":material/refresh:",
        key="refresh-quote",
        help="Refresh quote",
        width="content",
    ):
        next_index = (_current_quote_index() + 1) % len(QUOTES)
        st.session_state["quote_index"] = next_index
    category, quote, source = _quote_for_today()
    quote_line = f"Quote of the day · {category} · \"{quote}\" — {source}"
    controls_left.markdown(
        f"<div class='quote-line'>{escape(quote_line)}</div>",
        unsafe_allow_html=True,
    )


def _log_ui_call(
    *,
    provider: ProviderName,
    capability: str,
    status: str,
    message: str,
    model: str | None = None,
    stream: bool | None = None,
) -> None:
    entry: dict[str, object] = {
        "time": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "provider": provider,
        "capability": capability,
        "status": status,
        "model": model,
        "stream": stream,
        "message": message,
    }
    append_ui_call_log(entry)
    logger.info(
        "ui_call provider=%s capability=%s status=%s model=%s stream=%s message=%s",
        provider,
        capability,
        status,
        model,
        stream,
        message,
    )


def _render_ui_call_log() -> None:
    with st.sidebar.expander("Call log", expanded=False):
        logs = get_ui_call_log()
        if not logs:
            st.caption("No calls yet.")
            return
        for item in logs[:30]:
            timestamp = item.get("time", "")
            provider = item.get("provider", "")
            capability = item.get("capability", "")
            status = item.get("status", "")
            message = item.get("message", "")
            st.caption(f"[{timestamp}] {provider} · {capability} · {status}")
            st.text(str(message))


def _render_logs_page() -> None:
    st.subheader("Logs")
    logs = get_ui_call_log()
    if not logs:
        st.info("No call logs yet.")
        return
    st.dataframe(logs, width="stretch")
    st.code(pretty_json({"logs": logs}))
    if st.button("Clear logs", width="stretch"):
        clear_ui_call_log()
        st.rerun()


def _render_providers(_selected_provider: ProviderName, output_mode: OutputMode) -> None:
    rows: list[dict[str, object]] = []
    for provider in PROVIDERS:
        api_env, _base_url_env = provider_env_names(provider)
        configured = True
        try:
            get_provider_config(provider)
        except LLMError:
            configured = False
        rows.append({"provider": provider, "configured": configured, "api_key_env": api_env})
    st.subheader("Providers")
    if _show_text(output_mode):
        st.dataframe(rows, width="stretch")
        copy_lines = ["provider\tconfigured\tapi_key_env"]
        for row in rows:
            copy_lines.append(
                f"{row['provider']}\t{row['configured']}\t{row['api_key_env']}"
            )
        _render_api_copy_block("\n".join(copy_lines))
    if _show_json(output_mode):
        st.code(pretty_json({"providers": rows}))


def _render_list_models(provider: ProviderName, output_mode: OutputMode) -> None:
    st.subheader("List Models")
    if st.button("List models", width="stretch"):
        _log_ui_call(
            provider=provider,
            capability="list-models",
            status="start",
            message="Listing models requested from UI.",
        )
        try:
            models = list_models(provider)
            ids = [model.id for model in models]
            set_latest_models(provider, ids)
            payload = {"provider": provider, "models": [to_json_payload(model) for model in models]}
            if _show_text(output_mode):
                st.write(ids)
                _render_api_copy_block("\n".join(ids) if ids else "[No models returned.]")
            if _show_json(output_mode):
                st.code(pretty_json(payload))
            _log_ui_call(
                provider=provider,
                capability="list-models",
                status="ok",
                message=f"Retrieved {len(ids)} model ids.",
            )
        except LLMError as error:
            st.error(error.message)
            _log_ui_call(
                provider=provider,
                capability="list-models",
                status="error",
                message=error.message,
            )


def _render_run_saved_prompt_controls(
    *, provider: ProviderName, prompt_scope: str, prompt_history: list[str]
) -> str:
    prompt_col, clear_col = st.columns(2)
    selected = prompt_col.selectbox(
        "Saved prompts",
        options=["", *prompt_history],
        key=f"run-saved-prompts-{provider}",
        format_func=lambda value: (
            "Select a previous prompt"
            if value == ""
            else format_prompt_option_label(str(value))
        ),
        help="Pick one of your recent prompts.",
    )
    if clear_col.button(
        "Clear saved prompts",
        key=f"run-clear-prompts-{provider}",
        width="stretch",
    ):
        clear_prompt_history(prompt_scope)
        st.rerun()
    return selected if isinstance(selected, str) else ""


def _render_run_form(
    *,
    cap: Capability,
    defaults: Mapping[str, object],
    model_options: list[str],
    max_tokens_value: int,
    selected_saved_prompt: str,
) -> tuple[RunFormInput, bool]:
    with st.form("run-form"):
        model = ""
        if model_options:
            model_raw = st.selectbox(
                "Model",
                options=model_options,
                index=0,
                help=cap.params[1].help,
            )
            model = model_raw if isinstance(model_raw, str) else ""
        prompt = st.text_area(
            "Prompt",
            value=selected_saved_prompt,
            help=cap.params[2].help,
        )
        prompt_file = st.text_input("Prompt file", help=cap.params[3].help)
        system = st.text_input("System", help=cap.params[4].help)
        max_tokens_raw = st.number_input(
            "Max tokens",
            min_value=1,
            value=max_tokens_value,
            help=cap.params[5].help,
        )
        stream = st.checkbox(
            "Stream",
            value=bool(defaults["stream"]),
            help=cap.params[6].help,
        )
        submitted = st.form_submit_button("Run", width="stretch", disabled=not model_options)
    run_input = RunFormInput(
        model=model,
        prompt=prompt,
        prompt_file=prompt_file,
        system=system,
        max_tokens=int(max_tokens_raw),
        stream=stream,
    )
    return run_input, submitted


def _render_run_stream_result(
    *,
    provider: ProviderName,
    output_mode: OutputMode,
    prompt_text: str,
    run_input: RunFormInput,
    progress: RunProgress,
) -> None:
    result = stream_prompt(
        provider=provider,
        model=run_input.model or None,
        prompt=prompt_text,
        system=run_input.system or None,
        max_tokens=run_input.max_tokens,
    )
    chunks: list[str] = []
    stream_preview = st.empty()
    first_chunk_seen = False
    for chunk in result.chunks:
        if not first_chunk_seen:
            first_chunk_seen = True
            progress.placeholder.info(  # type: ignore[attr-defined]
                f"Streaming reply from `{provider}` / `{run_input.model}`..."
            )
        chunks.append(chunk)
        if _show_text(output_mode):
            stream_preview.code("".join(chunks), language=None)
    rendered_text = "".join(chunks)
    elapsed = monotonic() - progress.started_at
    rendered_clean = rendered_text.strip()
    payload = {
        "provider": provider,
        "model": result.model,
        "stream": True,
        "simulated_stream": result.simulated,
        "text": rendered_text,
        "chunks": chunks,
    }
    if _show_text(output_mode):
        stream_preview.empty()
        _render_api_text_response(rendered_text)
    if rendered_clean:
        progress.placeholder.success(  # type: ignore[attr-defined]
            f"Completed in {elapsed:.1f}s ({len(chunks)} chunks, {len(rendered_clean)} chars)."
        )
    else:
        progress.placeholder.warning(  # type: ignore[attr-defined]
            f"No text returned after {elapsed:.1f}s."
        )
    if _show_json(output_mode):
        st.code(pretty_json(payload))
    _log_ui_call(
        provider=provider,
        capability="run",
        status="ok",
        message=f"Streamed response with {len(chunks)} chunks.",
        model=result.model,
        stream=True,
    )


def _render_run_non_stream_result(
    *,
    provider: ProviderName,
    output_mode: OutputMode,
    prompt_text: str,
    run_input: RunFormInput,
    progress: RunProgress,
) -> None:
    progress.placeholder.info(  # type: ignore[attr-defined]
        f"Generating reply from `{provider}` / `{run_input.model}`..."
    )
    response = run_prompt(
        provider=provider,
        model=run_input.model or None,
        prompt=prompt_text,
        system=run_input.system or None,
        max_tokens=run_input.max_tokens,
    )
    elapsed = monotonic() - progress.started_at
    rendered = response.text.strip() or "[No response text returned.]"
    response_payload = to_json_payload(response)
    if _show_text(output_mode):
        _render_api_text_response(rendered)
    if rendered == "[No response text returned.]":
        progress.placeholder.warning(  # type: ignore[attr-defined]
            f"No text returned after {elapsed:.1f}s."
        )
    else:
        progress.placeholder.success(  # type: ignore[attr-defined]
            f"Completed in {elapsed:.1f}s ({len(rendered)} chars)."
        )
    if _show_json(output_mode):
        st.code(pretty_json(response_payload))
    _log_ui_call(
        provider=provider,
        capability="run",
        status="ok",
        message=f"Run completed in {response.latency_ms:.1f} ms.",
        model=response.model,
        stream=False,
    )


def _render_run(provider: ProviderName, output_mode: OutputMode) -> None:
    cap = capability_by_name("run")
    defaults = {param.name: param.default for param in cap.params}
    max_tokens_default = defaults.get("max-tokens")
    max_tokens_value = max_tokens_default if isinstance(max_tokens_default, int) else 512
    model_options = _load_provider_model_options(provider)
    prompt_scope = _prompt_history_scope_for_run(provider)
    prompt_history = get_prompt_history(prompt_scope)
    st.subheader("Run Prompt")
    if not model_options:
        st.warning("No models available for this provider.")
    selected_saved_prompt = _render_run_saved_prompt_controls(
        provider=provider,
        prompt_scope=prompt_scope,
        prompt_history=prompt_history,
    )
    run_input, submitted = _render_run_form(
        cap=cap,
        defaults=defaults,
        model_options=model_options,
        max_tokens_value=max_tokens_value,
        selected_saved_prompt=selected_saved_prompt,
    )
    if not submitted:
        return
    progress: RunProgress | None = None
    try:
        prompt_text = _resolve_prompt(
            provider=provider,
            prompt=run_input.prompt,
            prompt_file=run_input.prompt_file,
        )
        if run_input.prompt.strip():
            add_prompt_history(prompt_scope, run_input.prompt)
        _log_ui_call(
            provider=provider,
            capability="run",
            status="start",
            message="Prompt execution requested from UI.",
            model=run_input.model or None,
            stream=run_input.stream,
        )
        progress = _render_run_progress(provider, run_input.model or "default")
        if run_input.stream:
            _render_run_stream_result(
                provider=provider,
                output_mode=output_mode,
                prompt_text=prompt_text,
                run_input=run_input,
                progress=progress,
            )
        else:
            _render_run_non_stream_result(
                provider=provider,
                output_mode=output_mode,
                prompt_text=prompt_text,
                run_input=run_input,
                progress=progress,
            )
    except LLMError as error:
        if progress is not None:
            elapsed = monotonic() - progress.started_at
            progress.placeholder.error(  # type: ignore[attr-defined]
                f"Request failed after {elapsed:.1f}s: {error.message}"
            )
        st.error(error.message)
        _log_ui_call(
            provider=provider,
            capability="run",
            status="error",
            message=error.message,
            model=run_input.model or None,
            stream=run_input.stream,
        )


def _resolve_prompt(*, provider: ProviderName, prompt: str, prompt_file: str) -> str:
    if prompt and prompt_file:
        raise LLMError(
            provider=provider,
            model=None,
            kind="bad_request",
            message="Use prompt text or prompt file, not both.",
        )
    if prompt:
        return prompt
    if prompt_file:
        return open(prompt_file, encoding="utf-8").read()
    raise LLMError(
        provider=provider,
        model=None,
        kind="bad_request",
        message="Prompt is required.",
    )


def _render_check(provider: ProviderName, output_mode: OutputMode) -> None:
    st.subheader("Check Connection")
    if st.button("Check credentials", width="stretch"):
        _log_ui_call(
            provider=provider,
            capability="check",
            status="start",
            message="Credential check requested from UI.",
        )
        try:
            result = check_connection(provider)
            payload = to_json_payload(result)
            if _show_text(output_mode):
                summary = f"{provider}: {result.detail} ({result.latency_ms:.1f} ms)"
                st.success(summary)
                _render_api_copy_block(summary)
            if _show_json(output_mode):
                st.code(pretty_json(payload))
            _log_ui_call(
                provider=provider,
                capability="check",
                status="ok",
                message=f"Credential check succeeded in {result.latency_ms:.1f} ms.",
            )
        except LLMError as error:
            st.error(error.message)
            _log_ui_call(
                provider=provider,
                capability="check",
                status="error",
                message=error.message,
        )


def _render_chat_page(provider: ProviderName) -> None:
    render_chat_page(provider, log_ui_call=_log_ui_call)


CAPABILITY_RENDERERS: Mapping[str, Callable[[ProviderName, OutputMode], None]] = {
    "providers": _render_providers,
    "list-models": _render_list_models,
    "run": _render_run,
    "check": _render_check,
}


def render() -> None:
    """Render the complete Streamlit app."""
    st.set_page_config(page_title="LLM SDK Examples", layout="wide")
    _apply_dark_mode()
    st.title("Dynamic LLM API SDK Examples")
    st.caption(f"Version {get_app_version()}")
    _render_quote()
    # Initialise session state for "selected_page" before the widget renders so
    # the radio's `key=` finds a valid value and we don't trip Streamlit's
    # "default value + session_state" warning.
    get_selected_page(DEFAULT_PAGE)
    selected_page = st.sidebar.radio(
        "Page",
        PAGE_OPTIONS,
        key="selected_page",
        on_change=persist_session_state,
    )
    st.sidebar.caption(f"Version {get_app_version()}")
    initial_provider = resolve_default_provider(options=PROVIDERS, fallback=PROVIDERS[0])
    selected = get_selected_provider(initial_provider)
    selected_provider = st.sidebar.selectbox(
        "Provider",
        PROVIDERS,
        index=PROVIDERS.index(selected),
    )
    set_selected_provider(selected_provider)

    _render_ui_call_log()
    if selected_page == "Logs":
        _render_logs_page()
        return
    if selected_page == "Chat":
        _render_chat_page(selected_provider)
        return

    selected_output_mode = get_output_mode("txt")
    output_mode_label = st.radio(
        "Output format",
        ("TXT", "JSON"),
        index=0 if selected_output_mode == "txt" else 1,
        horizontal=True,
    )
    output_mode: OutputMode = "json" if output_mode_label == "JSON" else "txt"
    set_output_mode(output_mode)

    selected_capability = st.sidebar.radio(
        "Capability",
        [cap.name for cap in CAPABILITIES],
        format_func=lambda value: f"{value} - {capability_by_name(value).summary}",
    )
    renderer = CAPABILITY_RENDERERS[selected_capability]
    renderer(selected_provider, output_mode)


def ui_capability_names() -> tuple[str, ...]:
    """Expose capability names present in UI renderer map."""
    return tuple(CAPABILITY_RENDERERS.keys())


if __name__ == "__main__":
    render()
