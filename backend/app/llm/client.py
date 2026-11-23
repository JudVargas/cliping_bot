"""Cliente LLM compatible con OpenAI (Gemini, OpenRouter, Ollama).

Wrapper del SDK `openai` con:
- base_url configurable (desde config)
- reintentos con backoff exponencial
- función ask_json que valida la respuesta con un modelo pydantic y reintenta
  si el JSON es inválido o no pasa la validación.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, TypeVar

from openai import OpenAI
from openai import APIConnectionError, APIStatusError, RateLimitError
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Excepciones que merecen reintento
_RETRYABLE_EXCEPTIONS = (RateLimitError, APIConnectionError, APIStatusError)


class LLMClient:
    """Cliente LLM con reintentos y validación de JSON."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = 3,
        backoff_base: float = 2.0,
    ):
        self.base_url = base_url or settings.LLM_BASE_URL
        self.api_key = api_key or settings.LLM_API_KEY
        self.model = model or settings.LLM_MODEL
        self.max_retries = max_retries
        self.backoff_base = backoff_base

        self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)

    def _completion(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Llamar al LLM con reintentos con backoff exponencial.

        Devuelve el contenido del mensaje de respuesta.
        """
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=kwargs.get("temperature", 0.3),
                    max_tokens=kwargs.get("max_tokens", 2048),
                )
                content = response.choices[0].message.content
                if content is None:
                    raise ValueError("El LLM devolvió contenido vacío")
                return content
            except _RETRYABLE_EXCEPTIONS as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait = self.backoff_base ** attempt
                    logger.warning(
                        "LLM falló (intento %d/%d): %s. Reintentando en %.1f s",
                        attempt + 1,
                        self.max_retries + 1,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error(
                        "LLM falló tras %d intentos: %s", self.max_retries + 1, exc
                    )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.error("Error inesperado del LLM: %s", exc)
                break

        raise RuntimeError(f"LLM falló tras {self.max_retries + 1} intentos: {last_error}")

    def ask_json(
        self,
        messages: list[dict[str, str]],
        schema: type[T],
        *,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> T:
        """Pedir JSON al LLM y validarlo con un esquema pydantic.

        Si el JSON es inválido o no pasa la validación, reintenta (hasta
        max_retries) añadiendo una instrucción de corrección.
        """
        validation_messages = list(messages)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                content = self._completion(
                    validation_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                # Intentar extraer JSON (el modelo puede rodearlo con texto)
                data = self._extract_json(content)
                # Validar con el esquema pydantic
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "JSON inválido del LLM (intento %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
                if attempt < self.max_retries:
                    validation_messages.append(
                        {
                            "role": "assistant",
                            "content": content,
                        }
                    )
                    validation_messages.append(
                        {
                            "role": "user",
                            "content": (
                                "La respuesta anterior no es un JSON válido o no cumple "
                                "el esquema. Devuelve SOLO un objeto JSON válido, sin "
                                "texto adicional, que cumpla exactamente con el esquema solicitado."
                            ),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.error("Error validando JSON del LLM: %s", exc)
                break

        raise RuntimeError(
            f"No se pudo obtener JSON válido del LLM tras {self.max_retries + 1} intentos: {last_error}"
        )

    @staticmethod
    def _extract_json(text: str) -> Any:
        """Extraer el primer objeto JSON válido de un texto.

        El LLM puede envolver el JSON en bloques de código markdown o añadir
        texto alrededor. Buscamos la primera llave y el último cierre balanceado.
        """
        text = text.strip()

        # Quitar bloques de código markdown si los hay
        if text.startswith("```"):
            lines = text.splitlines()
            # Buscar la línea de apertura y el cierre
            start_idx = None
            for i, line in enumerate(lines):
                if line.strip().startswith("```"):
                    start_idx = i
                    break
            if start_idx is not None:
                end_idx = None
                for j in range(start_idx + 1, len(lines)):
                    if lines[j].strip() == "```":
                        end_idx = j
                        break
                if end_idx is not None:
                    text = "\n".join(lines[start_idx + 1:end_idx]).strip()
                else:
                    text = "\n".join(lines[start_idx + 1:]).strip()

        # Encontrar el primer objeto JSON (desde la primera '{' hasta su cierre)
        start = text.find("{")
        if start == -1:
            raise ValueError("No se encontró ningún objeto JSON en la respuesta")

        # Buscar el cierre balanceado contando llaves
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end == -1:
            raise ValueError("No se encontró cierre balanceado del objeto JSON")

        json_text = text[start : end + 1]
        return json.loads(json_text)


def create_client() -> LLMClient:
    """Factory para crear un LLMClient desde la configuración."""
    return LLMClient()
