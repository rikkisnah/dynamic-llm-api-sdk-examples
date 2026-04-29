"""Tier 5: Disk persistence for UI state across Streamlit reloads.

The UI's `st.session_state` is in-memory and reset on every Streamlit restart
or browser session boundary. To make selected provider, selected chat model,
selected page, output mode, and prompt history survive reloads we mirror those
keys to a JSON file under `.state/llm_ui_state.json` (repo-root, gitignored).

Environment knobs:

- `LLM_EXAMPLES_STATE_FILE` overrides the on-disk location.
- `LLM_EXAMPLES_DISABLE_STATE=1` makes every read/write a no-op (used in tests
  and ephemeral environments to keep the filesystem clean).

The file carries a `schema_version` so future loaders can migrate or discard
old shapes without crashing.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from contextlib import suppress
from pathlib import Path

PERSIST_VERSION = 1
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_FILE = _REPO_ROOT / ".state" / "llm_ui_state.json"

_PERSISTED_KEYS: tuple[str, ...] = (
    "selected_provider",
    "selected_chat_model_by_provider",
    "selected_page",
    "output_mode",
    "prompt_history",
)


def state_file() -> Path:
    """Resolve the on-disk path for persisted UI state."""
    override = os.environ.get("LLM_EXAMPLES_STATE_FILE", "").strip()
    if override:
        return Path(override).expanduser()
    return DEFAULT_STATE_FILE


def is_persistence_disabled() -> bool:
    """Return True when persistence reads/writes should be no-ops."""
    return bool(os.environ.get("LLM_EXAMPLES_DISABLE_STATE", "").strip())


def persisted_keys() -> tuple[str, ...]:
    """Session-state keys that participate in disk persistence."""
    return _PERSISTED_KEYS


def load_state() -> Mapping[str, object]:
    """Read persisted UI state from disk; return `{}` on any failure."""
    if is_persistence_disabled():
        return {}
    path = state_file()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if data.get("schema_version") != PERSIST_VERSION:
        return {}
    state = data.get("state")
    return state if isinstance(state, dict) else {}


def save_state(payload: Mapping[str, object]) -> None:
    """Atomically write persisted UI state to disk."""
    if is_persistence_disabled():
        return
    path = state_file()
    document = {"schema_version": PERSIST_VERSION, "state": dict(payload)}
    with suppress(OSError):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
