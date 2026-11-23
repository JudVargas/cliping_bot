"""Etapa 1b: Transcripción con faster-whisper.

- faster-whisper en GPU con word_timestamps=True y vad_filter=True.
- Modelo y compute_type desde config. Si int8_float16 falla, reintentar con int8
  y avisar en el log.
- Guardar data/<video_id>/transcript.json con el modelo Transcript.
- Barra de progreso (logging por lotes de segmentos).
- CLI: python -m app.pipeline.transcribe video.mp4 [--force]
- Si ya existe transcript.json, no recalcular salvo --force.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipeline.ingest import ingest

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover
    WhisperModel = None


@dataclass
class Word:
    """Palabra transcrita con timestamps y probabilidad."""

    text: str
    start: float
    end: float
    prob: float


@dataclass
class Segment:
    """Segmento de transcripción."""

    id: int
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


@dataclass
class Transcript:
    """Transcripción completa de un video."""

    language: str
    words: list[Word]
    segments: list[Segment]


def _to_word(w: Any) -> Word:
    """Convertir un objeto Word de faster-whisper a nuestro dataclass Word."""
    return Word(
        text=getattr(w, "word", "") or "",
        start=float(getattr(w, "start", 0.0)),
        end=float(getattr(w, "end", 0.0)),
        prob=float(getattr(w, "probability", 0.0)),
    )


def _load_model(model_name: str, compute_type: str):
    """Cargar WhisperModel con fallback de compute_type.

    Intenta compute_type solicitado (ej. int8_float16) y, si falla, cae a int8,
    avisando en el log en cada intento.
    """
    if WhisperModel is None:
        raise RuntimeError("faster-whisper no está instalado")

    last_error: Exception | None = None
    for ct in (compute_type, "int8"):
        try:
            logger.info(
                "Cargando modelo Whisper %s con compute_type=%s (device=cuda)",
                model_name,
                ct,
            )
            return WhisperModel(model_name, device="cuda", compute_type=ct)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "No se pudo cargar compute_type=%s: %s", ct, exc
            )
            last_error = exc

    raise RuntimeError(f"No se pudo cargar el modelo Whisper: {last_error}")


def _save_transcript(transcript: Transcript, path: Path) -> None:
    """Serializar Transcript a JSON."""
    payload: dict[str, Any] = {
        "language": transcript.language,
        "words": [asdict(w) for w in transcript.words],
        "segments": [
            {
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "words": [asdict(w) for w in s.words],
            }
            for s in transcript.segments
        ],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_transcript(path: Path) -> Transcript:
    """Cargar Transcript desde JSON."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    words = [Word(**w) for w in payload.get("words", [])]
    segments = [
        Segment(
            id=s["id"],
            start=s["start"],
            end=s["end"],
            text=s["text"],
            words=[Word(**w) for w in s.get("words", [])],
        )
        for s in payload.get("segments", [])
    ]
    return Transcript(
        language=payload["language"], words=words, segments=segments
    )


def transcribe(
    video_path: str | Path,
    *,
    force: bool = False,
    language: str | None = None,
) -> Transcript:
    """Transcribir un video y guardar transcript.json.

    Si transcript.json ya existe y force=False, lo carga y lo devuelve sin
    recalcular.
    """
    video_path = Path(video_path)
    video_id = video_path.stem
    data_dir = settings.data_dir / video_id
    data_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = data_dir / "transcript.json"

    if transcript_path.exists() and not force:
        logger.info(
            "transcript.json ya existe, saltando transcripción: %s",
            transcript_path,
        )
        return _load_transcript(transcript_path)

    # 1. Ingesta: extraer audio si aún no existe
    audio_path = data_dir / "audio.wav"
    if not audio_path.exists():
        _, audio_path = ingest(video_path)

    # 2. Cargar modelo (con fallback de compute_type)
    model = _load_model(settings.WHISPER_MODEL, settings.WHISPER_COMPUTE)

    # 3. Transcribir con timestamps de palabra y VAD
    lang = language or settings.WHISPER_LANGUAGE or None
    logger.info(
        "Iniciando transcripción: %s (idioma=%s, word_timestamps=True, vad_filter=True)",
        audio_path,
        lang,
    )

    segments_iter, info = model.transcribe(
        str(audio_path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,
    )

    # faster-whisper devuelve un generador; iteramos mostrando progreso
    words: list[Word] = []
    segments: list[Segment] = []
    seg_idx = 0
    for segment in segments_iter:
        seg_words = [_to_word(w) for w in (segment.words or [])]
        words.extend(seg_words)
        segments.append(
            Segment(
                id=seg_idx,
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text,
                words=seg_words,
            )
        )
        seg_idx += 1
        if seg_idx % 10 == 0:
            logger.info("Progreso: %d segmentos procesados, %d palabras",
                        seg_idx, len(words))

    transcript = Transcript(
        language=(info.language or lang or "es"),
        words=words,
        segments=segments,
    )

    # 4. Guardar JSON para poder reanudar sin recalcular
    _save_transcript(transcript, transcript_path)
    logger.info(
        "Transcripción guardada: %s (%d palabras, %d segmentos, idioma=%s)",
        transcript_path,
        len(words),
        len(segments),
        transcript.language,
    )
    return transcript


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Transcribir video con faster-whisper (GPU)"
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar recálculo aunque exista transcript.json",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Forzar idioma (ej. es). Por defecto detecta automáticamente",
    )
    args = parser.parse_args()

    transcribe(args.video, force=args.force, language=args.language)
    print("Transcripción completa.")
