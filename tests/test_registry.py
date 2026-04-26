"""Registry tests for provider dispatch."""

from __future__ import annotations

import pytest

from llm_examples.llm_client import BaseClient
from llm_examples.registry import PROVIDERS, get_client


@pytest.mark.parametrize("provider_name", PROVIDERS)
def test_get_client_returns_base_client(provider_name: str) -> None:
    client = get_client(provider_name)  # type: ignore[arg-type]
    assert isinstance(client, BaseClient)
    assert client.provider == provider_name
