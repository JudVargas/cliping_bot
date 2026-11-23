"""Prompts del LLM para selección de momentos (en español)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class MomentCandidate(BaseModel):
    """Un momento candidato sugerido por el LLM."""

    start: float = Field(..., description="Inicio del clip en segundos (relativo al video original)")
    end: float = Field(..., description="Fin del clip en segundos (relativo al video original)")
    title: str = Field(..., description="Título corto y descriptivo del momento")
    reason: str = Field(..., description="Por qué este momento es un buen clip")
    score: float = Field(..., description="Puntuación del 0 al 10")

    @field_validator("score")
    def _validate_score(cls, v: float) -> float:
        if not 0 <= v <= 10:
            raise ValueError("score debe estar entre 0 y 10")
        return v

    @field_validator("end")
    def _validate_end_after_start(cls, v: float, info) -> float:
        if info.data.get("start") is not None and v <= info.data["start"]:
            raise ValueError("end debe ser mayor que start")
        return v


class MomentList(BaseModel):
    """Lista de momentos candidatos devuelta por el LLM para una ventana."""

    moments: list[MomentCandidate] = Field(default_factory=list)


def build_moments_prompt(transcript_fragment: str, window_start: float, window_end: float) -> str:
    """Construir el prompt en español para que el LLM seleccione momentos.

    Recibe un fragmento de transcripción con timestamps por palabra y devuelve
    el texto del prompt. El LLM debe responder con JSON estricto validado por
    MomentList.
    """
    return f"""Eres un editor de video experto en crear clips cortos verticales (TikTok / Reels / Shorts) para redes sociales.

TEMPORADA DEL VIDEO A ANALIZAR: de {window_start:.1f}s a {window_end:.1f}s

TRANSCRIPCIÓN CON TIMESTAMPS (palabra: inicio - fin):
{transcript_fragment}

TAREA:
Selecciona los mejores momentos para crear clips de 20 a 60 segundos que se entiendan solos, sin contexto adicional.

REGLAS ESTRICTAS:
1. Cada clip debe durar entre 20 y 60 segundos (end - start entre 20 y 60).
2. Cada clip debe empezar y terminar en frases completas (no cortar a mitad de frase ni a mitad de palabra).
3. Cada clip debe entenderse por sí solo, sin necesidad de haber visto lo anterior ni lo posterior.
4. Preferir historias, remates graciosos, ideas fuertes, opiniones claras y momentos emocionantes.
5. Los start y end deben ajustarse a los límites de palabra más cercanos usando los timestamps de la transcripción.
6. No selecciones momentos que se solapen entre sí.
7. Devuelve una puntuación score (0-10) para cada momento: cuán bueno es como clip viral.

FORMATO DE SALIDA:
Devuelve ÚNICAMENTE un objeto JSON válido, sin texto antes ni después, sin bloques de código markdown, con esta estructura:

{{
  "moments": [
    {{
      "start": 120.5,
      "end": 145.2,
      "title": "Título corto del momento",
      "reason": "Por qué es un buen clip",
      "score": 8.5
    }}
  ]
}}

Si no hay ningún momento válido en esta ventana, devuelve {{"moments": []}}.

Analiza cuidadosamente y selecciona los mejores momentos:"""


SYSTEM_MESSAGE = """Eres un asistente que responde únicamente con JSON válido y estricto. No añadas explicaciones, ni texto antes ni después del JSON. No uses bloques de código markdown."""
