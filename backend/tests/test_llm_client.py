"""Pruebas del cliente LLM (mocks, sin API real ni red)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from app.llm.client import LLMClient, _RETRYABLE_EXCEPTIONS


class DummySchema(BaseModel):
    name: str = Field(..., description="nombre")
    value: int = Field(..., description="valor entero")


def test_ask_json_returns_validated_model():
    """ask_json debe devolver una instancia del esquema pydantic."""
    fake_content = '{"name": "clip1", "value": 42}'

    with patch("app.llm.client.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = fake_content
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        llm = LLMClient(base_url="http://localhost:11434/v1", api_key="dummy", model="test")
        result = llm.ask_json([{"role": "user", "content": "hola"}], DummySchema)

    assert isinstance(result, DummySchema)
    assert result.name == "clip1"
    assert result.value == 42


def test_ask_json_retries_on_invalid_json():
    """Si el JSON es inválido, ask_json debe reintentar con instrucción de corrección."""
    first_bad = "esto no es json"
    second_good = '{"name": "clip2", "value": 7}'

    with patch("app.llm.client.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        responses = [
            MagicMock(choices=[MagicMock(message=MagicMock(content=first_bad))]),
            MagicMock(choices=[MagicMock(message=MagicMock(content=second_good))]),
        ]
        mock_client.chat.completions.create.side_effect = responses

        llm = LLMClient(base_url="http://x", api_key="k", model="m", max_retries=1)
        result = llm.ask_json([{"role": "user", "content": "dame json"}], DummySchema)

    assert isinstance(result, DummySchema)
    assert result.name == "clip2"
    assert result.value == 7
    # Se llamó dos veces: primera falló, segunda OK
    assert mock_client.chat.completions.create.call_count == 2


def test_ask_json_extracts_json_from_markdown_block():
    """ask_json debe extraer JSON incluso si viene envuelto en bloques markdown."""
    content_with_markdown = '```json\n{"name": "md", "value": 9}\n```'

    with patch("app.llm.client.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = content_with_markdown
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        llm = LLMClient(base_url="http://x", api_key="k", model="m")
        result = llm.ask_json([{"role": "user", "content": "x"}], DummySchema)

    assert result.name == "md"
    assert result.value == 9


def test_ask_json_raises_after_max_retries():
    """Si siempre falla el JSON, ask_json debe lanzar RuntimeError tras max_retries."""
    bad_json = "no es json nunca"

    with patch("app.llm.client.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = bad_json
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        llm = LLMClient(base_url="http://x", api_key="k", model="m", max_retries=2)
        with pytest.raises(RuntimeError):
            llm.ask_json([{"role": "user", "content": "x"}], DummySchema)

    # max_retries=2 → 3 intentos totales
    assert mock_client.chat.completions.create.call_count == 3


def test_completion_retries_on_rate_limit():
    """_completion debe reintentar ante RateLimitError con backoff."""
    from openai import RateLimitError

    call_count = 0

    def fake_create(*args: Any, **kwargs: Any):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Simular RateLimitError. Necesitamos un response y body para el constructor.
            resp = MagicMock()
            resp.status_code = 429
            resp.headers = {}
            raise RateLimitError("rate limited", response=resp, body=b"")
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"name": "ok", "value": 1}'
        mock_response.choices = [mock_choice]
        return mock_response

    with patch("app.llm.client.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.side_effect = fake_create

        llm = LLMClient(base_url="http://x", api_key="k", model="m", max_retries=3, backoff_base=0.01)
        result = llm.ask_json([{"role": "user", "content": "x"}], DummySchema)

    assert result.name == "ok"
    assert call_count == 3


def test_extract_json_from_plain_text():
    """_extract_json debe extraer el primer objeto JSON de un texto con basura alrededor."""
    from app.llm.client import LLMClient

    text = "Aquí está el resultado: {\"name\": \"extraído\", \"value\": 5} fin del texto"
    result = LLMClient._extract_json(text)
    assert result == {"name": "extraído", "value": 5}


def test_extract_json_raises_on_no_json():
    """Si no hay JSON, _extract_json debe lanzar ValueError."""
    from app.llm.client import LLMClient

    with pytest.raises(ValueError):
        LLMClient._extract_json("esto no tiene llaves")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
