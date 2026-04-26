"""Tier 5: Streamlit UI rendered from capability registry."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import date

try:
    import streamlit as st
except Exception:  # pragma: no cover - optional dependency fallback for constrained envs
    class _StreamlitStub:
        session_state: dict[str, object] = {}

        def __getattr__(self, _name: str) -> Callable[..., object]:
            def _missing(*_: object, **__: object) -> object:
                raise RuntimeError("streamlit is not installed in this environment.")

            return _missing

    st = _StreamlitStub()  # type: ignore[assignment]

from llm_examples.capabilities import CAPABILITIES, capability_by_name
from llm_examples.config import get_provider_config, provider_env_names
from llm_examples.domain_types import LLMError, ProviderName
from llm_examples.registry import PROVIDERS
from llm_examples.services import check_connection, list_models, run_prompt, stream_prompt
from llm_examples.ui.helpers import pretty_json, to_json_payload
from llm_examples.ui.state import (
    get_latest_models,
    get_selected_provider,
    set_latest_models,
    set_selected_provider,
)

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


def _apply_dark_mode() -> None:
    st.markdown(
        """
<style>
:root { color-scheme: dark; }
[data-testid="stAppViewContainer"] { background-color: #0f1117; color: #e7e9ee; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background-color: #141824; }
[data-testid="stForm"] { background-color: #141824; border: 1px solid #2a2f3d; border-radius: 8px; padding: 12px; }
</style>
        """,
        unsafe_allow_html=True,
    )


def _quote_for_today() -> tuple[str, str, str]:
    index = date.today().toordinal() % len(QUOTES)
    return QUOTES[index]


def _render_quote() -> None:
    category, quote, source = _quote_for_today()
    st.caption(f"Quote of the day · {category}")
    st.markdown(f"> {quote}\n>\n> — {source}")


def _render_providers(_: ProviderName) -> None:
    rows: list[dict[str, object]] = []
    for provider in PROVIDERS:
        api_env, _ = provider_env_names(provider)
        configured = True
        try:
            _ = get_provider_config(provider)
        except LLMError:
            configured = False
        rows.append({"provider": provider, "configured": configured, "api_key_env": api_env})
    st.subheader("Providers")
    st.dataframe(rows, width="stretch")


def _render_list_models(provider: ProviderName) -> None:
    st.subheader("List Models")
    if st.button("List models", width="stretch"):
        try:
            models = list_models(provider)
            ids = [model.id for model in models]
            set_latest_models(ids)
            st.write(ids)
            st.code(pretty_json({"provider": provider, "models": [to_json_payload(model) for model in models]}))
        except LLMError as error:
            st.error(error.message)


def _render_run(provider: ProviderName) -> None:
    cap = capability_by_name("run")
    defaults = {param.name: param.default for param in cap.params}
    st.subheader("Run Prompt")
    with st.form("run-form"):
        model_default = get_latest_models()[0] if get_latest_models() else ""
        model = st.text_input("Model", value=model_default, help=cap.params[1].help)
        prompt = st.text_area("Prompt", help=cap.params[2].help)
        prompt_file = st.text_input("Prompt file", help=cap.params[3].help)
        system = st.text_input("System", help=cap.params[4].help)
        max_tokens = st.number_input(
            "Max tokens",
            min_value=1,
            value=int(defaults["max-tokens"] or 512),
            help=cap.params[5].help,
        )
        stream = st.checkbox("Stream", value=bool(defaults["stream"]), help=cap.params[6].help)
        submitted = st.form_submit_button("Run", width="stretch")

    if not submitted:
        return
    try:
        prompt_text = _resolve_prompt(provider=provider, prompt=prompt, prompt_file=prompt_file)
        if stream:
            result = stream_prompt(
                provider=provider,
                model=model or None,
                prompt=prompt_text,
                system=system or None,
                max_tokens=int(max_tokens),
            )
            chunks = list(result.chunks)
            st.write_stream(iter(chunks))
            st.code(
                pretty_json(
                    {
                        "provider": provider,
                        "model": result.model,
                        "stream": True,
                        "simulated_stream": result.simulated,
                        "text": "".join(chunks),
                        "chunks": chunks,
                    }
                )
            )
        else:
            response = run_prompt(
                provider=provider,
                model=model or None,
                prompt=prompt_text,
                system=system or None,
                max_tokens=int(max_tokens),
            )
            st.write(response.text)
            st.code(pretty_json(to_json_payload(response)))
    except LLMError as error:
        st.error(error.message)


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


def _render_check(provider: ProviderName) -> None:
    st.subheader("Check Connection")
    if st.button("Check credentials", width="stretch"):
        try:
            result = check_connection(provider)
            st.success(f"{provider}: {result.detail} ({result.latency_ms:.1f} ms)")
            st.code(pretty_json(to_json_payload(result)))
        except LLMError as error:
            st.error(error.message)


CAPABILITY_RENDERERS: Mapping[str, Callable[[ProviderName], None]] = {
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
    _render_quote()
    selected = get_selected_provider(PROVIDERS[0])
    selected_provider = st.sidebar.selectbox("Provider", PROVIDERS, index=PROVIDERS.index(selected))
    set_selected_provider(selected_provider)
    selected_capability = st.sidebar.radio(
        "Capability",
        [cap.name for cap in CAPABILITIES],
        format_func=lambda value: f"{value} - {capability_by_name(value).summary}",
    )
    renderer = CAPABILITY_RENDERERS[selected_capability]
    renderer(selected_provider)


def ui_capability_names() -> tuple[str, ...]:
    """Expose capability names present in UI renderer map."""
    return tuple(CAPABILITY_RENDERERS.keys())


if __name__ == "__main__":
    render()
