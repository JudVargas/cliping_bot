"""Etapa 1a: Ingesta de video.

- ffprobe: duración, resolución y fps.
- Extraer audio a wav 16 kHz mono en data/<video_id>/audio.wav.

Nunca se usa shell=True; se pasan listas de argumentos a subprocess.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    """Metadatos del video obtenidos con ffprobe."""

    duration: float
    width: int
    height: int
    fps: float


def probe_video(video_path: str | Path) -> VideoInfo:
    """Obtener metadatos del video con ffprobe."""
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"No se encuentra el video: {video_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path),
    ]
    logger.debug("Ejecutando ffprobe: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe falló para {video_path}: {result.stderr.strip()}")

    data: dict[str, Any] = json.loads(result.stdout)
    stream = data["streams"][0]

    width = int(stream["width"])
    height = int(stream["height"])

    # fps puede venir como "num/den" (ej. "30000/1001") o decimal
    fps_str = str(stream.get("r_frame_rate", "0/1"))
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 0.0
    else:
        fps = float(fps_str)

    duration = float(
        data.get("format", {}).get("duration", stream.get("duration", 0)) or 0
    )

    return VideoInfo(duration=duration, width=width, height=height, fps=fps)


def extract_audio(
    video_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Extraer audio a wav 16 kHz mono en data/<video_id>/audio.wav.

    Devuelve la ruta al archivo de audio generado.
    """
    video_path = Path(video_path)
    video_id = video_path.stem
    if output_dir is None:
        output_dir = settings.data_dir / video_id
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    audio_path = output_dir / "audio.wav"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]
    logger.debug("Ejecutando ffmpeg: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg falló extrayendo audio de {video_path}: {result.stderr.strip()}"
        )

    logger.info("Audio extraído: %s", audio_path)
    return audio_path


def ingest(video_path: str | Path) -> tuple[VideoInfo, Path]:
    """Ejecutar ingesta completa: probe + extraer audio.

    Devuelve (VideoInfo, ruta_al_audio).
    """
    info = probe_video(video_path)
    audio_path = extract_audio(video_path)
    return info, audio_path


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Ingesta de video (ffprobe + extraer audio wav 16k mono)"
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    args = parser.parse_args()

    info, audio_path = ingest(args.video)
    print(json.dumps(asdict(info), indent=2, ensure_ascii=False))
    print(f"Audio: {audio_path}")
