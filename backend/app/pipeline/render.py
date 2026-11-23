"""Etapa 3: Cortar y exportar clips (todavía horizontal).

- render_clip(video_path, start, end, out_path): corta un clip con FFmpeg.
  Usa h264_nvenc si está disponible, si no libx264. Audio aac.
  Corte exacto con -ss y -to (reencodeo, no copy).
  Opcionalmente quema subtítulos .ass (filtro `ass` de FFmpeg).
- render_all_from_moments(video_id): lee moments.json y exporta todos los clips
  a data/<video_id>/clips/.
- CLI: python -m app.pipeline.render <video_id> [--top N] [--captions <estilo>]

Nunca se usa shell=True; se pasan listas de argumentos a subprocess.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.config import settings
from app.pipeline.captions import generate_ass, available_styles
from app.pipeline.moments import Moment, select_moments
from app.pipeline.transcribe import Word, _load_transcript

logger = logging.getLogger(__name__)


def _encoder_available(encoder: str) -> bool:
    """Verificar si un encoder de ffmpeg está disponible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            check=False,
        )
        return encoder in result.stdout
    except FileNotFoundError:
        return False


def _pick_video_encoder(preferred: str = "h264_nvenc") -> str:
    """Elegir el encoder de video: preferido (nvenc) con fallback a libx264."""
    if _encoder_available(preferred):
        logger.info("Usando encoder de video: %s (GPU)", preferred)
        return preferred
    logger.warning(
        "Encoder %s no disponible, usando libx264 (CPU)", preferred
    )
    return "libx264"


def render_clip(
    video_path: str | Path,
    start: float,
    end: float,
    out_path: str | Path,
    *,
    encoder: str | None = None,
    captions_style: str | None = None,
    words: list[Word] | None = None,
) -> Path:
    """Renderizar un clip del video original.

    Corta el tramo [start, end] con reencodeo (no copy) para garantizar un
    corte exacto. Video: h264_nvenc (GPU) con fallback a libx264 (CPU).
    Audio: aac.

    Si se indican captions_style y words, se genera un .ass temporal y se
    queman los subtítulos con el filtro `ass` de FFmpeg.

    Devuelve la ruta al archivo de salida.
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"No se encuentra el video: {video_path}")

    if end <= start:
        raise ValueError(f"end ({end}) debe ser mayor que start ({start})")

    duration = end - start
    video_encoder = encoder or _pick_video_encoder(settings.VIDEO_ENCODER)

    # Si hay subtítulos, generar .ass temporal
    ass_path: Path | None = None
    if captions_style:
        if captions_style not in available_styles():
            raise ValueError(
                f"Estilo '{captions_style}' no disponible. "
                f"Opciones: {available_styles()}"
            )
        clip_words = words or []
        ass_path = Path(tempfile.gettempdir()) / f"{out_path.stem}.ass"
        generate_ass(clip_words, start, captions_style, ass_path)

    # -ss antes de -i para seek rápido (keyframe), -to para fin exacto.
    # Reencodeo para corte frame-accurate.
    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-ss", f"{start:.6f}",
        "-i", str(video_path),
        "-to", f"{duration:.6f}",
        "-c:v", video_encoder,
        "-preset", "p4" if video_encoder == "h264_nvenc" else "medium",
        "-rc:v", "vbr" if video_encoder == "h264_nvenc" else "",
        "-cq:v", "24" if video_encoder == "h264_nvenc" else "",
        "-b:v", "5M" if video_encoder == "h264_nvenc" else "",
        "-maxrate", "10M" if video_encoder == "h264_nvenc" else "",
        "-bufsize", "10M" if video_encoder == "h264_nvenc" else "",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
    ]

    # Filtro de subtítulos (quemar .ass en el video)
    if ass_path is not None:
        ass_filter = _ass_filter_path(ass_path)
        cmd.extend(["-vf", ass_filter])

    cmd.append(str(out_path))

    # Eliminar argumentos vacíos
    cmd = [c for c in cmd if c != ""]

    logger.debug("Ejecutando ffmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        # Si falló nvenc, intentar fallback automático a libx264
        if video_encoder == "h264_nvenc":
            logger.warning(
                "h264_nvenc falló, reintentando con libx264 (CPU): %s",
                result.stderr.strip()[:200],
            )
            return render_clip(
                video_path, start, end, out_path,
                encoder="libx264",
                captions_style=captions_style,
                words=words,
            )
        raise RuntimeError(
            f"ffmpeg falló renderizando {video_path} [{start}-{end}]: "
            f"{result.stderr.strip()}"
        )

    # Limpiar archivo .ass temporal
    if ass_path is not None and ass_path.exists():
        try:
            ass_path.unlink()
        except OSError:
            pass

    logger.info("Clip renderizado: %s (%.1fs - %.1fs)", out_path, start, end)
    return out_path


def _ass_filter_path(ass_path: Path) -> str:
    """Construir el argumento -vf ass= con la ruta escapada para Windows.

    En Windows las barras invertidas y los dos puntos de la ruta pueden
    romper el filtro de FFmpeg. Se convierte a barras normales (/) que FFmpeg
    acepta en Windows, y se escapan los caracteres especiales.
    """
    # Usar barras normales (FFmpeg en Windows acepta C:/ruta/archivo.ass)
    posix = ass_path.as_posix()
    # Escapar backslash y dos puntos por si acaso quedan
    escaped = posix.replace("\\", "\\\\").replace(":", "\\:")
    return f"ass={escaped}"


def render_all_from_moments(
    video_id: str,
    *,
    top: int | None = None,
    force: bool = False,
    captions_style: str | None = None,
) -> list[Path]:
    """Renderizar todos los momentos de un video.

    Lee moments.json (calculándolo si no existe) y exporta cada clip a
    data/<video_id>/clips/clip_XXX.mp4.

    Si captions_style se indica, se cargan las palabras de transcript.json
    dentro del rango de cada clip y se queman los subtítulos.

    Devuelve la lista de rutas de los clips generados.
    """
    data_dir = settings.data_dir / video_id
    clips_dir = data_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # Buscar el video original en data/<video_id>/ o en data/
    video_path = _find_video(video_id)
    moments = select_moments(video_id, top=top, force=force)

    if not moments:
        logger.warning("No hay momentos para renderizar en %s", video_id)
        return []

    # Cargar transcript una sola vez si necesitamos subtítulos
    transcript = None
    if captions_style:
        transcript_path = data_dir / "transcript.json"
        if transcript_path.exists():
            transcript = _load_transcript(transcript_path)
        else:
            logger.warning(
                "No se encontró transcript.json para %s; sin subtítulos",
                video_id,
            )

    output_paths: list[Path] = []
    clips_with_moments: list[tuple[Moment, Path]] = []
    for idx, moment in enumerate(moments):
        out_name = f"clip_{idx:03d}_{moment.id:03d}.mp4"
        out_path = clips_dir / out_name
        logger.info(
            "Renderizando clip %d/%d: %.1f-%.1f (%s)",
            idx + 1, len(moments), moment.start, moment.end, moment.title,
        )

        # Palabras del transcript dentro del rango de este clip
        clip_words: list[Word] | None = None
        if transcript is not None:
            clip_words = [
                w for w in transcript.words
                if w.start >= moment.start and w.end <= moment.end
            ]

        render_clip(
            video_path,
            moment.start,
            moment.end,
            out_path,
            captions_style=captions_style,
            words=clip_words,
        )
        output_paths.append(out_path)
        clips_with_moments.append((moment, out_path))

    logger.info(
        "Todos los clips renderizados: %d en %s", len(output_paths), clips_dir
    )
    return output_paths


def _find_video(video_id: str, data_dir: Path | None = None) -> Path:
    """Buscar el archivo de video original para un video_id.

    Busca en data/<video_id>/ y en data/ directamente.
    """
    if data_dir is None:
        data_dir = settings.data_dir
    # Extensiones comunes de video
    extensions = (".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v")

    # 1. Dentro de data/<video_id>/
    video_dir = data_dir / video_id
    if video_dir.is_dir():
        for ext in extensions:
            for candidate in video_dir.glob(f"*{ext}"):
                return candidate

    # 2. Directamente en data/
    for ext in extensions:
        candidate = data_dir / f"{video_id}{ext}"
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        f"No se encontró el video original para '{video_id}' en {data_dir}"
    )


def save_render_log(
    video_id: str,
    clips: list[tuple[Moment, Path]],
) -> Path:
    """Guardar un log de qué clips se renderizaron y con qué parámetros."""
    data_dir = settings.data_dir / video_id
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "render_log.json"

    payload = [
        {
            "moment": asdict(m),
            "output": str(p),
        }
        for m, p in clips
    ]
    log_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return log_path


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Renderizar clips a partir de moments.json"
    )
    parser.add_argument("video_id", help="ID del video (nombre sin extensión)")
    parser.add_argument(
        "--top",
        type=int,
        default=None,
        help="Renderizar solo los N mejores momentos",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar recálculo de moments.json",
    )
    parser.add_argument(
        "--captions",
        choices=available_styles(),
        default=None,
        help="Estilo de subtítulos a quemar (clasico, resaltado, minimal)",
    )
    args = parser.parse_args()

    clips = render_all_from_moments(
        args.video_id,
        top=args.top,
        force=args.force,
        captions_style=args.captions,
    )
    print(json.dumps([str(p) for p in clips], ensure_ascii=False, indent=2))
