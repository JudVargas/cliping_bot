"""Etapa 2: Selección de momentos con LLM.

- Divide la transcripción en ventanas de ~8-10 min con solape de 60 s.
- Llama al LLM por ventana pidiendo JSON estricto validado por pydantic.
- Une resultados, elimina duplicados por solape (IoU de tiempo).
- Ajusta start/end al límite de palabra/frase más cercano usando los timestamps.
- Guarda moments.json ordenado por score.

CLI: python -m app.pipeline.moments <video_id> [--top 10]
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from app.config import settings
from app.llm.client import create_client
from app.llm.prompts import MomentCandidate, MomentList, build_moments_prompt, SYSTEM_MESSAGE
from app.pipeline.transcribe import Transcript, Word, Segment, _load_transcript

logger = logging.getLogger(__name__)


@dataclass
class Moment:
    """Momento seleccionado para un clip."""

    id: int
    start: float
    end: float
    title: str
    reason: str
    score: float


# --- Parámetros de ventanas ---
WINDOW_DURATION = 600.0  # ~10 min en segundos
WINDOW_OVERLAP = 60.0    # solape de 60 s entre ventanas


def _make_windows(transcript: Transcript) -> list[tuple[float, float]]:
    """Dividir la transcripción en ventanas con solape."""
    if not transcript.segments:
        return []

    total_duration = max(seg.end for seg in transcript.segments)
    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < total_duration:
        end = min(start + WINDOW_DURATION, total_duration)
        windows.append((start, end))
        if end >= total_duration:
            break
        start += WINDOW_DURATION - WINDOW_OVERLAP
    return windows


def _transcript_fragment(transcript: Transcript, start: float, end: float) -> str:
    """Extraer el fragmento de transcripción dentro de una ventana [start, end).

    Formato: palabra: inicio - fin  (relativo al video original)
    """
    lines: list[str] = []
    for word in transcript.words:
        if word.start >= end:
            break
        if word.end <= start:
            continue
        lines.append(f"{word.text}: {word.start:.2f} - {word.end:.2f}")
    return "\n".join(lines)


def _iou(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Intersección sobre unión de dos intervalos de tiempo."""
    inter_start = max(a_start, b_start)
    inter_end = min(a_end, b_end)
    inter = max(0.0, inter_end - inter_start)
    union = max(a_end, b_end) - min(a_start, b_start)
    if union <= 0:
        return 0.0
    return inter / union


def _dedup(moments: list[Moment], iou_threshold: float = 0.3) -> list[Moment]:
    """Eliminar momentos duplicados por solape (IoU de tiempo).

    Se conserva el de mayor score.
    """
    if not moments:
        return []

    # Ordenar por score descendente para conservar el mejor
    sorted_moments = sorted(moments, key=lambda m: m.score, reverse=True)
    kept: list[Moment] = []
    for m in sorted_moments:
        is_duplicate = False
        for k in kept:
            if _iou(m.start, m.end, k.start, k.end) > iou_threshold:
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(m)
    return kept


def _adjust_to_word_boundaries(
    moments: list[Moment],
    transcript: Transcript,
) -> list[Moment]:
    """Ajustar start/end al límite de palabra/frase más cercano.

    start se mueve al inicio de la primera palabra cuya end >= start original.
    end se mueve al fin de la última palabra cuya start <= end original.
    """
    if not transcript.words:
        return moments

    word_starts = [w.start for w in transcript.words]
    word_ends = [w.end for w in transcript.words]

    adjusted: list[Moment] = []
    for m in moments:
        # start: primer palabra que termina en o después del start solicitado
        new_start = m.start
        for w in transcript.words:
            if w.end >= m.start:
                new_start = w.start
                break

        # end: última palabra que empieza en o antes del end solicitado
        new_end = m.end
        for w in reversed(transcript.words):
            if w.start <= m.end:
                new_end = w.end
                break

        # Asegurar que end > start
        if new_end <= new_start:
            new_end = new_start + 20.0  # mínimo 20 s

        adjusted.append(
            Moment(
                id=m.id,
                start=round(new_start, 2),
                end=round(new_end, 2),
                title=m.title,
                reason=m.reason,
                score=m.score,
            )
        )
    return adjusted


def select_moments(
    video_id: str,
    *,
    top: int | None = None,
    force: bool = False,
) -> list[Moment]:
    """Seleccionar momentos para un video usando el LLM.

    Si moments.json ya existe y force=False, lo carga y lo devuelve.
    """
    data_dir = settings.data_dir / video_id
    transcript_path = data_dir / "transcript.json"
    moments_path = data_dir / "moments.json"

    if moments_path.exists() and not force:
        logger.info("moments.json ya existe, cargando: %s", moments_path)
        return _load_moments(moments_path, top=top)

    if not transcript_path.exists():
        raise FileNotFoundError(
            f"No se encuentra transcript.json para {video_id}. Ejecuta primero la transcripción."
        )

    transcript = _load_transcript(transcript_path)

    # 1. Crear ventanas
    windows = _make_windows(transcript)
    logger.info("Transcripción dividida en %d ventanas", len(windows))

    # 2. Llamar al LLM por ventana
    client = create_client()
    all_moments: list[Moment] = []
    moment_id = 0

    for idx, (w_start, w_end) in enumerate(windows, 1):
        logger.info("Procesando ventana %d/%d (%.1fs - %.1fs)", idx, len(windows), w_start, w_end)
        fragment = _transcript_fragment(transcript, w_start, w_end)
        if not fragment.strip():
            logger.info("Ventana %d sin transcripción, saltando", idx)
            continue

        prompt = build_moments_prompt(fragment, w_start, w_end)
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ]

        try:
            result: MomentList = client.ask_json(messages, MomentList)
        except Exception as exc:  # noqa: BLE001
            logger.error("LLM falló para la ventana %d: %s", idx, exc)
            continue

        for cand in result.moments:
            # Filtrar duraciones fuera de rango (20-60 s)
            duration = cand.end - cand.start
            if duration < 20 or duration > 60:
                logger.debug(
                    "Descartando momento %.1f-%.1f (duración %.1f fuera de rango)",
                    cand.start, cand.end, duration,
                )
                continue

            all_moments.append(
                Moment(
                    id=moment_id,
                    start=round(cand.start, 2),
                    end=round(cand.end, 2),
                    title=cand.title,
                    reason=cand.reason,
                    score=round(cand.score, 1),
                )
            )
            moment_id += 1

    logger.info("Total momentos crudos: %d", len(all_moments))

    # 3. Deduplicar por solape
    deduped = _dedup(all_moments)
    logger.info("Después del dedup: %d momentos", len(deduped))

    # 4. Ajustar a límites de palabra/frase
    adjusted = _adjust_to_word_boundaries(deduped, transcript)

    # 5. Ordenar por score descendente
    adjusted.sort(key=lambda m: m.score, reverse=True)

    # 6. Aplicar top si se pide
    if top is not None:
        adjusted = adjusted[:top]

    # 7. Reasignar ids
    for i, m in enumerate(adjusted):
        m.id = i

    # 8. Guardar JSON
    _save_moments(adjusted, moments_path)
    logger.info("moments.json guardado: %s (%d momentos)", moments_path, len(adjusted))

    return adjusted


def _save_moments(moments: list[Moment], path: Path) -> None:
    """Guardar lista de momentos como JSON."""
    payload = [asdict(m) for m in moments]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_moments(path: Path, *, top: int | None = None) -> list[Moment]:
    """Cargar lista de momentos desde JSON."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    moments = [Moment(**m) for m in payload]
    moments.sort(key=lambda m: m.score, reverse=True)
    if top is not None:
        moments = moments[:top]
    for i, m in enumerate(moments):
        m.id = i
    return moments


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Seleccionar momentos de un video con LLM"
    )
    parser.add_argument("video_id", help="ID del video (nombre del archivo sin extensión)")
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Devolver solo los N mejores momentos",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar recálculo aunque exista moments.json",
    )
    args = parser.parse_args()

    moments = select_moments(args.video_id, top=args.top, force=args.force)
    print(json.dumps([asdict(m) for m in moments], ensure_ascii=False, indent=2))
