"""
Unit tests for openai_client.chat_to_json.
"""
from typing import Any, Dict

import pytest

import linkedin_insights.openai_client as oc


def _mock_create(*_args, **_kwargs):  # noqa: D401 – mock signature
    """Return an object mimicking OpenAI's response shape."""
    class _Choice:
        class _Message:
            content = '{"foo": 1}'

        message = _Message()

    class _Response:
        choices = [_Choice()]

    return _Response()


def test_chat_to_json_parses(monkeypatch) -> None:
    """chat_to_json should return parsed dict when OpenAI responds."""
    # Patch the underlying client call
    monkeypatch.setattr(
        oc.client.chat.completions, "create", _mock_create, raising=True
    )

    result: Dict[str, Any] = oc.chat_to_json("irrelevant user prompt")
    assert result == {"foo": 1}
