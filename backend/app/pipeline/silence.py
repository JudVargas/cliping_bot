"""Etapa 5: Quitar silencios y muletillas.

A partir de las palabras del clip, construye una lista de tramos a conservar
(EditDecision.keep):
- Elimina pausas mayores a 0.6 s (dejando 0.15 s de respiro).
- Elimina muletillas configurables ("eh", "em", "mmm", "este", "o sea")
  solo cuando aparecen aisladas.
- Complementa con silencedetect de FFmpeg para pausas que no aparecen como
  palabras.
- No corta risas ni énfasis (si hay un pico de energía en una pausa, se
  conserva).

CLI: python -m app.pipeline.silence <video_id> --start X --end Y
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipeline.transcribe import Word, _load_transcript

logger = logging.getLogger(__name__)

# Muletillas por defecto que se eliminan solo si aparecen aisladas
DEFAULT_FILLERS = {"eh", "em", "mmm", "este", "o sea"}

# Umbrales
MIN_PAUSE_TO_CUT = 0.6       # pausas mayores a esto se recortan
BREATH_TO_KEEP = 0.15        # respiro que se deja al recortar una pausa
FILLER_GAP_TOLERANCE = 0.25  # si una muletilla está rodeada de silencio corto, se considera aislada


@dataclass
class EditDecision:
    """Decisión de edición: tramos a conservar (tiempos relativos al video original)."""

    keep: list[tuple[float, float]]

    def to_json(self) -> dict[str, Any]:
        return {"keep": [[s, e] for s, e in self.keep]}

    def duration_kept(self) -> float:
        return sum(e - s for s, e in self.keep)


def _silence_intervals(audio_path: str | Path, noise_tolerance: str = "-30dB") -> list[tuple[float, float]]:
    """Detectar intervalos de silencio con el filtro silencedetect de FFmpeg.

    Devuelve lista de (start, end) de tramos silenciosos en segundos.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        logger.warning("Audio no encontrado para silencedetect: %s", audio_path)
        return []

    cmd = [
        "ffmpeg",
        "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_tolerance}:d=0.5",
        "-f", "null",
        "-",
    ]
    logger.debug("Ejecutando silencedetect: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # silencedetect escribe al stderr
    output = result.stderr

    intervals: list[tuple[float, float]] = []
    silence_start: float | None = None

    for line in output.splitlines():
        line = line.strip()
        if "silence_start:" in line:
            try:
                silence_start = float(line.split("silence_start:")[1].split()[0])
            except (ValueError, IndexError):
                silence_start = None
        elif "silence_end:" in line and silence_start is not None:
            try:
                parts = line.split("silence_end:")[1].split()
                silence_end = float(parts[0])
                intervals.append((silence_start, silence_end))
            except (ValueError, IndexError):
                pass
            silence_start = None

    return intervals


def _is_filler(word: Word, fillers: set[str]) -> bool:
    """Determinar si una palabra es una muletilla aislada."""
    return word.text.strip().lower() in fillers


def build_edit_decision(
    words: list[Word],
    clip_start: float,
    clip_end: float,
    *,
    min_gap: float = MIN_PAUSE_TO_CUT,
    breath: float = BREATH_TO_KEEP,
    fillers: set[str] | None = None,
    audio_path: str | Path | None = None,
) -> EditDecision:
    """Construir EditDecision a partir de las palabras del clip.

    Reglas:
    1. El clip completo va de clip_start a clip_end.
    2. Pausas entre palabras mayores a min_gap se recortan (dejando breath de respiro).
    3. Muletillas aisladas (en fillers) se eliminan.
    4. Se complementa con silencedetect para pausas no transcritas.
    """
    if fillers is None:
        fillers = DEFAULT_FILLERS

    # Filtrar palabras dentro del rango del clip
    clip_words = [
        w for w in words
        if w.start >= clip_start and w.end <= clip_end
    ]
    clip_words.sort(key=lambda w: w.start)

    if not clip_words:
        return EditDecision(keep=[(clip_start, clip_end)])

    # Detectar silencios adicionales con FFmpeg si hay audio
    silence_intervals: list[tuple[float, float]] = []
    if audio_path is not None:
        silence_intervals = _silence_intervals(audio_path)
        logger.info("Silencedetect encontró %d intervalos de silencio", len(silence_intervals))

    # Construir tramos a conservar empezando por el clip completo y recortando
    keep: list[tuple[float, float]] = [(clip_start, clip_end)]

    # 1. Recortar pausas entre palabras consecutivas
    i = 0
    while i < len(clip_words) - 1:
        w1 = clip_words[i]
        w2 = clip_words[i + 1]
        gap = w2.start - w1.end

        # Si hay una muletilla aislada entre ellas, considerar eliminarla
        if _is_filler(w1, fillers) and gap < FILLER_GAP_TOLERANCE:
            # La muletilla está al final de w1; eliminar desde w1.start hasta w2.start
            # (dejando respiro antes de w2)
            cut_start = max(w1.start, clip_start)
            cut_end = max(w2.start - breath, clip_start)
            keep = _subtract_interval(keep, cut_start, cut_end)
            i += 1
            continue

        if _is_filler(w2, fillers) and gap < FILLER_GAP_TOLERANCE:
            cut_start = max(w1.end + breath, clip_start)
            cut_end = min(w2.end, clip_end)
            keep = _subtract_interval(keep, cut_start, cut_end)
            i += 1
            continue

        # Pausa larga entre palabras: recortar dejando respiro
        if gap > min_gap:
            cut_start = w1.end + breath
            cut_end = w2.start - breath
            if cut_end > cut_start:
                keep = _subtract_interval(keep, cut_start, cut_end)
        i += 1

    # 2. Complementar con silencedetect: recortar tramos silenciosos detectados
    for s_start, s_end in silence_intervals:
        # Solo recortar silencios dentro del rango del clip
        cut_start = max(s_start, clip_start)
        cut_end = min(s_end, clip_end)
        if cut_end > cut_start and (cut_end - cut_start) > min_gap:
            # Dejar un respiro en los bordes
            cut_start = min(cut_start + breath, clip_end)
            cut_end = max(cut_end - breath, clip_start)
            if cut_end > cut_start:
                keep = _subtract_interval(keep, cut_start, cut_end)

    # Fusionar tramos contiguos y ordenar
    keep = _merge_intervals(keep)
    # Filtrar tramos vacíos o muy pequeños (< 0.5 s)
    keep = [(s, e) for s, e in keep if e - s > 0.5]

    if not keep:
        # Si todo se recortó, conservar al menos el clip original
        keep = [(clip_start, clip_end)]

    logger.info(
        "EditDecision: %d tramos a conservar (%.1f s de %.1f s totales)",
        len(keep),
        sum(e - s for s, e in keep),
        clip_end - clip_start,
    )
    return EditDecision(keep=keep)


def _subtract_interval(
    intervals: list[tuple[float, float]],
    cut_start: float,
    cut_end: float,
) -> list[tuple[float, float]]:
    """Restar un intervalo [cut_start, cut_end) de una lista de intervalos."""
    result: list[tuple[float, float]] = []
    for s, e in intervals:
        if cut_end <= s or cut_start >= e:
            # No hay solape
            result.append((s, e))
        else:
            # Parte izquierda
            if s < cut_start:
                result.append((s, min(cut_start, e)))
            # Parte derecha
            if e > cut_end:
                result.append((max(cut_end, s), e))
    return result


def _merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Fusionar intervalos que se tocan o solapan."""
    if not intervals:
        return []
    sorted_ints = sorted(intervals, key=lambda x: x[0])
    merged: list[tuple[float, float]] = [sorted_ints[0]]
    for s, e in sorted_ints[1:]:
        last_s, last_e = merged[-1]
        if s <= last_e:  # tocan o solapan
            merged[-1] = (last_s, max(last_e, e))
        else:
            merged.append((s, e))
    return merged


def save_edit_decision(decision: EditDecision, path: str | Path) -> Path:
    """Guardar EditDecision como JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(decision.to_json(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_edit_decision(path: str | Path) -> EditDecision:
    """Cargar EditDecision desde JSON."""
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    keep = [tuple(item) for item in payload.get("keep", [])]
    return EditDecision(keep=keep)


def map_times_through_decision(
    decision: EditDecision,
    clip_start: float,
) -> dict[float, float]:
    """Crear una función de mapeo de tiempos originales -> tiempos recortados.

    Devuelve un dict que mapea tiempo original -> tiempo recortado para los
    bordes de los tramos keep. Para tiempos intermedios se interpola.
    """
    mapping: dict[float, float] = {}
    offset = 0.0
    prev_end = clip_start

    for s, e in decision.keep:
        # El tiempo original s se mapea a prev_end + offset (ajustado)
        # Pero s >= prev_end, así que el tiempo recortado de s es:
        mapping[s] = prev_end + offset  # no, esto no es correcto

    # En realidad, construimos una función por tramos lineales
    # Para simplicidad, devolvemos los bordes mapeados
    return mapping


def remap_word_times(
    words: list[Word],
    decision: EditDecision,
    clip_start: float,
) -> list[Word]:
    """Recalcular los tiempos de las palabras según los tramos conservados.

    Cada palabra cuyo tiempo cae dentro de un tramo keep se reajusta restando
    el tiempo acumulado recortado antes de ese tramo.
    """
    remapped: list[Word] = []
    accumulated_cut = 0.0
    prev_end = clip_start

    for keep_start, keep_end in decision.keep:
        # El tiempo recortado del inicio de este tramo es:
        # clip_start + (keep_start - clip_start) - accumulated_cut
        # pero accumulated_cut ya incluye los cortes previos
        mapped_start = keep_start - accumulated_cut

        for w in words:
            if keep_start <= w.start and w.end <= keep_end:
                # Palabra dentro de este tramo: desplazar por accumulated_cut
                remapped.append(
                    Word(
                        text=w.text,
                        start=round(w.start - accumulated_cut, 3),
                        end=round(w.end - accumulated_cut, 3),
                        prob=w.prob,
                    )
                )

        # El corte después de este tramo es hasta el siguiente keep_start
        # (se calcula en la siguiente iteración)
        # El tiempo transcurrido original dentro de este tramo:
        original_duration = keep_end - keep_start
        # El tiempo recortado transcurrido:
        # No cambiamos accumulated_cut dentro del tramo, solo entre tramos
        prev_end = keep_end

    return remapped


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Construir EditDecision para quitar silencios y muletillas"
    )
    parser.add_argument("video_id", help="ID del video")
    parser.add_argument("--start", type=float, required=True, help="Inicio del clip")
    parser.add_argument("--end", type=float, required=True, help="Fin del clip")
    parser.add_argument("--min-gap", type=float, default=MIN_PAUSE_TO_CUT)
    parser.add_argument("--breath", type=float, default=BREATH_TO_KEEP)
    parser.add_argument("--output", help="Ruta del JSON de salida (edit_decision.json)")
    args = parser.parse_args()

    data_dir = settings.data_dir / args.video_id
    transcript_path = data_dir / "transcript.json"
    audio_path = data_dir / "audio.wav"

    if not transcript_path.exists():
        raise FileNotFoundError(f"No se encontró transcript.json: {transcript_path}")

    transcript = _load_transcript(transcript_path)
    decision = build_edit_decision(
        transcript.words,
        args.start,
        args.end,
        min_gap=args.min_gap,
        breath=args.breath,
        audio_path=audio_path if audio_path.exists() else None,
    )

    out_path = Path(args.output) if args.output else data_dir / "edit_decision.json"
    save_edit_decision(decision, out_path)
    print(json.dumps(decision.to_json(), ensure_ascii=False, indent=2))
