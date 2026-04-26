"""Tier 5: Streamlit chat page renderer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

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

from llm_examples.domain_types import LLMError, ProviderName
from llm_examples.services import list_models, run_prompt, stream_prompt
from llm_examples.ui.helpers import (
    UploadedFileLike,
    build_attachment_context,
    build_chat_prompt,
    is_image_attachment,
    normalize_uploaded_files,
    wrapped_text_html,
)
from llm_examples.ui.helpers import (
    prompt_option_label as format_prompt_option_label,
)
from llm_examples.ui.state import (
    add_prompt_history,
    append_chat_message,
    clear_chat_messages,
    clear_prompt_history,
    get_chat_messages,
    get_latest_models,
    get_prompt_history,
    get_selected_chat_model,
    set_latest_models,
    set_selected_chat_model,
)


@dataclass(frozen=True, slots=True)
class ChatControls:
    selected_saved_prompt: str
    send_saved_prompt: bool
    stream: bool
    max_tokens: int
    system: str


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


def _prompt_history_scope_for_chat(provider: ProviderName, model: str) -> str:
    return f"chat:{provider}:{model}"


def _render_chat_message(role: str, content: str) -> None:
    chat_role = "assistant" if role == "assistant" else "user"
    with st.chat_message(chat_role):
        if role == "assistant":
            rendered = content.strip() or "[No response text returned.]"
            st.markdown(wrapped_text_html(rendered), unsafe_allow_html=True)
            return
        if len(content) > 1_000:
            st.markdown(wrapped_text_html(content[:1_000] + "..."), unsafe_allow_html=True)
            with st.expander("Show full message"):
                st.markdown(wrapped_text_html(content), unsafe_allow_html=True)
            return
        st.markdown(wrapped_text_html(content), unsafe_allow_html=True)


def _render_chat_model_selector(provider: ProviderName, model_options: list[str]) -> str:
    selected_model = get_selected_chat_model(provider, model_options)
    model_index = model_options.index(selected_model) if selected_model in model_options else 0
    model_col, scope_col = st.columns([2, 3])
    model_raw = model_col.selectbox(
        "Model",
        options=model_options,
        index=model_index,
        key=f"chat-model-{provider}",
        help="Choose the active model for this chat thread.",
    )
    model_value = model_raw if isinstance(model_raw, str) else model_options[0]
    set_selected_chat_model(provider, model_value)
    scope_col.caption(f"Conversation scope: {provider} / {model_value}")
    return model_value


def _render_chat_thread_controls(provider: ProviderName, model_value: str) -> None:
    controls_left, info_col = st.columns([1, 3])
    if controls_left.button(
        "Clear chat",
        icon=":material/delete:",
        key=f"chat-clear-history-{provider}-{model_value}",
        width="content",
    ):
        clear_chat_messages(provider, model_value)
        st.rerun()
    info_col.caption("Use the `+` icon in the message box to attach files or paste images.")


def _render_chat_saved_prompt_controls(
    *,
    provider: ProviderName,
    model_value: str,
    prompt_scope: str,
    prompt_history: list[str],
) -> tuple[str, bool]:
    prompt_left, prompt_send_col, prompt_clear_col = st.columns([3, 1, 1])
    selected = prompt_left.selectbox(
        "Saved prompts",
        options=["", *prompt_history],
        key=f"chat-saved-prompts-{provider}-{model_value}",
        format_func=lambda value: (
            "Select a previous prompt"
            if value == ""
            else format_prompt_option_label(str(value))
        ),
        help="Pick one of your recent prompts.",
    )
    send_saved_prompt = prompt_send_col.button(
        "Send",
        icon=":material/send:",
        key=f"chat-send-saved-{provider}-{model_value}",
        width="content",
    )
    if prompt_clear_col.button(
        "Clear",
        icon=":material/delete_sweep:",
        key=f"chat-clear-prompts-{provider}-{model_value}",
        width="content",
    ):
        clear_prompt_history(prompt_scope)
        st.rerun()
    selected_prompt = selected if isinstance(selected, str) else ""
    return selected_prompt, send_saved_prompt


def _render_chat_generation_controls() -> tuple[bool, int, str]:
    stream_col, max_tokens_col = st.columns([1, 1])
    stream = stream_col.toggle("Stream response", value=True)
    max_tokens_raw = max_tokens_col.number_input(
        "Max tokens",
        min_value=1,
        value=512,
        step=1,
        key="chat-max-tokens",
    )
    system = st.text_input(
        "System instruction (optional)",
        value="",
        key="chat-system",
    )
    return stream, int(max_tokens_raw), system


def _render_chat_history(history: list[dict[str, str]]) -> None:
    for message in history:
        _render_chat_message(message.get("role", "assistant"), message.get("content", ""))


def _resolve_chat_input(
    *, send_saved_prompt: bool, selected_saved_prompt: str, model_value: str
) -> tuple[str | None, list[UploadedFileLike]]:
    user_message = st.chat_input(
        f"Message {model_value}",
        accept_file="multiple",
    )
    if isinstance(user_message, str) and user_message.strip():
        return user_message.strip(), []
    text_value_obj = getattr(user_message, "text", None)
    files_obj = getattr(user_message, "files", None)
    if isinstance(text_value_obj, str) or isinstance(files_obj, list):
        text_value = text_value_obj if isinstance(text_value_obj, str) else ""
        uploaded_files = normalize_uploaded_files(files_obj if isinstance(files_obj, list) else [])
        if text_value.strip() or uploaded_files:
            text_message = text_value.strip() or "Analyze these attachments."
            return text_message, uploaded_files
    if send_saved_prompt and selected_saved_prompt.strip():
        return selected_saved_prompt.strip(), []
    if send_saved_prompt:
        st.warning("Select a saved prompt first.")
    return None, []


def _render_chat_user_turn(
    cleaned_user_message: str,
    attachment_names: list[str],
    uploaded_files: list[UploadedFileLike],
) -> None:
    with st.chat_message("user"):
        if attachment_names:
            attachments_label = ", ".join(attachment_names)
            st.markdown(
                wrapped_text_html(f"{cleaned_user_message}\n\nAttachments: {attachments_label}"),
                unsafe_allow_html=True,
            )
        else:
            st.markdown(wrapped_text_html(cleaned_user_message), unsafe_allow_html=True)
        for uploaded_file in uploaded_files:
            if is_image_attachment(uploaded_file):
                st.image(uploaded_file.getvalue(), caption=uploaded_file.name, width=260)


def _render_chat_assistant_reply(
    *,
    provider: ProviderName,
    model_value: str,
    prompt: str,
    system: str,
    max_tokens: int,
    stream: bool,
) -> str:
    with st.chat_message("assistant"):
        if stream:
            stream_result = stream_prompt(
                provider=provider,
                model=model_value,
                prompt=prompt,
                system=system or None,
                max_tokens=max_tokens,
            )
            rendered_reply = st.empty()
            parts: list[str] = []
            for chunk in stream_result.chunks:
                parts.append(chunk)
                rendered_reply.markdown(
                    wrapped_text_html("".join(parts)),
                    unsafe_allow_html=True,
                )
            reply = "".join(parts).strip()
            if reply:
                return reply
            fallback = "[No response text returned.]"
            rendered_reply.markdown(wrapped_text_html(fallback), unsafe_allow_html=True)
            return fallback
        response = run_prompt(
            provider=provider,
            model=model_value,
            prompt=prompt,
            system=system or None,
            max_tokens=max_tokens,
        )
        reply = response.text.strip() or "[No response text returned.]"
        st.markdown(wrapped_text_html(reply), unsafe_allow_html=True)
        return reply


def _render_chat_controls(
    *,
    provider: ProviderName,
    model_value: str,
    prompt_scope: str,
    prompt_history: list[str],
) -> ChatControls:
    with st.expander("Chat settings", expanded=False):
        _render_chat_thread_controls(provider, model_value)
        selected_saved_prompt, send_saved_prompt = _render_chat_saved_prompt_controls(
            provider=provider,
            model_value=model_value,
            prompt_scope=prompt_scope,
            prompt_history=prompt_history,
        )
        stream, max_tokens, system = _render_chat_generation_controls()
    return ChatControls(
        selected_saved_prompt=selected_saved_prompt,
        send_saved_prompt=send_saved_prompt,
        stream=stream,
        max_tokens=max_tokens,
        system=system,
    )


def _submit_chat_turn(
    *,
    provider: ProviderName,
    model_value: str,
    prompt_scope: str,
    cleaned_user_message: str,
    uploaded_files: list[UploadedFileLike],
    history: list[dict[str, str]],
    stream: bool,
    max_tokens: int,
    system: str,
    log_ui_call: Callable[..., None],
) -> None:
    add_prompt_history(prompt_scope, cleaned_user_message)
    attachment_context, attachment_names = build_attachment_context(uploaded_files)
    user_turn = cleaned_user_message
    if attachment_context:
        user_turn = f"{cleaned_user_message}\n\nAttachment context:\n{attachment_context}"
    prompt = build_chat_prompt(
        history=history,
        user_message=cleaned_user_message,
        attachment_context=attachment_context,
    )
    log_ui_call(
        provider=provider,
        capability="chat",
        status="start",
        message="Chat message requested from UI.",
        model=model_value,
        stream=stream,
    )
    append_chat_message(provider, model_value, "user", user_turn)
    _render_chat_user_turn(cleaned_user_message, attachment_names, uploaded_files)
    try:
        reply = _render_chat_assistant_reply(
            provider=provider,
            model_value=model_value,
            prompt=prompt,
            system=system,
            max_tokens=max_tokens,
            stream=stream,
        )
        append_chat_message(provider, model_value, "assistant", reply)
        log_ui_call(
            provider=provider,
            capability="chat",
            status="ok",
            message=f"Chat turn completed; response chars={len(reply)}.",
            model=model_value,
            stream=stream,
        )
    except LLMError as error:
        st.error(error.message)
        log_ui_call(
            provider=provider,
            capability="chat",
            status="error",
            message=error.message,
            model=model_value,
            stream=stream,
        )


def render_chat_page(provider: ProviderName, *, log_ui_call: Callable[..., None]) -> None:
    """Render Chat page for the selected provider."""
    st.subheader("Chat")
    model_options = _load_provider_model_options(provider)
    if not model_options:
        st.warning("No models available for this provider.")
        return
    model_value = _render_chat_model_selector(provider, model_options)
    prompt_scope = _prompt_history_scope_for_chat(provider, model_value)
    controls = _render_chat_controls(
        provider=provider,
        model_value=model_value,
        prompt_scope=prompt_scope,
        prompt_history=get_prompt_history(prompt_scope),
    )
    history = get_chat_messages(provider, model_value)
    if history:
        _render_chat_history(history)
    else:
        st.markdown(
            "<div class='chat-empty'>What are you working on?</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            (
                "<div class='chat-subtle'>Start chatting below. Use Chat settings for prompts, "
                "files, and controls.</div>"
            ),
            unsafe_allow_html=True,
        )
    cleaned_user_message, uploaded_files = _resolve_chat_input(
        send_saved_prompt=controls.send_saved_prompt,
        selected_saved_prompt=controls.selected_saved_prompt,
        model_value=model_value,
    )
    if cleaned_user_message is None:
        return
    _submit_chat_turn(
        provider=provider,
        model_value=model_value,
        prompt_scope=prompt_scope,
        cleaned_user_message=cleaned_user_message,
        uploaded_files=uploaded_files,
        history=history,
        stream=controls.stream,
        max_tokens=controls.max_tokens,
        system=controls.system,
        log_ui_call=log_ui_call,
    )
