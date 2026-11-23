"""Etapa 4: Generación de subtítulos .ass con palabra activa resaltada.

- Resolución de referencia 1080x1920 (vertical).
- 3 a 5 palabras por línea.
- La palabra activa se resalta con \k (karaoke de ASS).
- 3 estilos predefinidos en un dict fácil de ampliar: "clasico", "resaltado", "minimal".
- Posición: tercio inferior-central.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.pipeline.transcribe import Word

logger = logging.getLogger(__name__)

# Resolución de referencia del canvas ASS (vertical 9:16)
ASS_WIDTH = 1080
ASS_HEIGHT = 1920

# Máximo y mínimo de palabras por línea
MAX_WORDS_PER_LINE = 5
MIN_WORDS_PER_LINE = 3


# ---------------------------------------------------------------------------
# Estilos predefinidos (fácil de ampliar)
# ---------------------------------------------------------------------------
# Colores en ASS: &HBBGGRR& (azul, verde, rojo). Blanco = &H00FFFFFF,
# Negro = &H00000000, Amarillo = &H0000FFFF, Cian = &H00FFFF00.
STYLES: dict[str, dict[str, Any]] = {
    "clasico": {
        "fontname": "Arial",
        "fontsize": 44,
        "primary": "&H00FFFFFF",      # blanco
        "secondary": "&H0000FFFF",    # amarillo (palabra activa)
        "outline": "&H00000000",      # negro
        "back": "&H80000000",
        "bold": -1,
        "italic": 0,
        "border_style": 1,
        "outline_width": 2.5,
        "shadow": 0,
        "alignment": 2,               # centro inferior
        "margin_v": 180,              # tercio inferior, con margen desde abajo
    },
    "resaltado": {
        "fontname": "Arial",
        "fontsize": 52,
        "primary": "&H00FFFFFF",
        "secondary": "&H0000FFFF",    # amarillo fuerte
        "outline": "&H00000000",
        "back": "&H80000000",
        "bold": -1,
        "italic": 0,
        "border_style": 1,
        "outline_width": 3.5,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 150,
    },
    "minimal": {
        "fontname": "Arial",
        "fontsize": 36,
        "primary": "&H00CCCCCC",      # gris claro
        "secondary": "&H00FFFFFF",    # blanco (palabra activa)
        "outline": "&H00000000",
        "back": "&H00000000",
        "bold": 0,
        "italic": 0,
        "border_style": 1,
        "outline_width": 1.5,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 220,
    },
}


def available_styles() -> list[str]:
    """Devuelve la lista de nombres de estilos disponibles."""
    return list(STYLES.keys())


def ass_time(seconds: float) -> str:
    """Convertir segundos a formato de tiempo ASS: H:MM:SS.cc (centésimas)."""
    if seconds < 0:
        seconds = 0.0
    total_cs = int(round(seconds * 100))
    h = total_cs // 360000
    remainder = total_cs % 360000
    m = remainder // 6000
    remainder %= 6000
    s = remainder // 100
    cs = remainder % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _style_section(style_name: str) -> str:
    """Generar la sección [V4+ Styles] para un estilo dado."""
    if style_name not in STYLES:
        raise ValueError(
            f"Estilo '{style_name}' no disponible. Opciones: {available_styles()}"
        )
    s = STYLES[style_name]
    # Formato: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour,
    #          OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut,
    #          ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow,
    #          Alignment, MarginL, MarginR, MarginV, Encoding
    return (
        f"Style: {style_name}, {s['fontname']}, {s['fontsize']}, "
        f"{s['primary']}, {s['secondary']}, {s['outline']}, {s['back']}, "
        f"{s['bold']}, {s['italic']}, 0, 0, 100, 100, 0, 0, "
        f"{s['border_style']}, {s['outline_width']}, {s['shadow']}, "
        f"{s['alignment']}, 30, 30, {s['margin_v']}, 1"
    )


def group_words_into_lines(
    words: list[Word], max_per_line: int = MAX_WORDS_PER_LINE
) -> list[list[Word]]:
    """Agrupar palabras en líneas de hasta max_per_line palabras.

    Respeta pausas: si hay un salto grande entre dos palabras consecutivas
    (más de 0.7 s), se empieza una nueva línea aunque no se llene la actual.
    """
    if not words:
        return []

    lines: list[list[Word]] = []
    current: list[Word] = [words[0]]

    for prev, cur in zip(words, words[1:]):
        gap = cur.start - prev.end
        if len(current) >= max_per_line or gap > 0.7:
            lines.append(current)
            current = [cur]
        else:
            current.append(cur)

    if current:
        lines.append(current)

    return lines


def generate_ass(
    clip_words: list[Word],
    clip_start: float,
    style_name: str = "clasico",
    output_path: str | Path | None = None,
) -> Path:
    """Generar un archivo .ass para un clip.

    Args:
        clip_words: palabras del transcript dentro del rango del clip
                    (tiempos absolutos, relativos al video original).
        clip_start: tiempo de inicio del clip en el video original.
                    Se usa para hacer los tiempos del .ass relativos al clip.
        style_name: nombre del estilo ("clasico", "resaltado", "minimal").
        output_path: ruta donde guardar el .ass. Si es None, se crea un
                     archivo temporal junto al output_path padre o en cwd.

    Devuelve la ruta al archivo .ass generado.
    """
    if style_name not in STYLES:
        raise ValueError(
            f"Estilo '{style_name}' no disponible. Opciones: {available_styles()}"
        )

    if not clip_words:
        # Generar un .ass vacío (sin eventos) para evitar errores en ffmpeg
        content = _ass_header() + "\n" + _style_section(style_name) + "\n" + _events_header() + "\n"
        path = Path(output_path) if output_path else Path("empty_subs.ass")
        path.write_text(content, encoding="utf-8")
        return path

    # Tiempos relativos al inicio del clip
    rel_words = [
        Word(
            text=w.text,
            start=max(0.0, w.start - clip_start),
            end=max(0.0, w.end - clip_start),
            prob=w.prob,
        )
        for w in clip_words
    ]

    lines = group_words_into_lines(rel_words)

    # Construir eventos de diálogo
    events: list[str] = []
    for line in lines:
        if not line:
            continue
        start_rel = line[0].start
        end_rel = line[-1].end
        if end_rel <= start_rel:
            end_rel = start_rel + 1.0

        parts: list[str] = []
        for w in line:
            dur_cs = max(1, int(round((w.end - w.start) * 100)))
            parts.append(f"{{\\k{dur_cs}}}{w.text}")
        text = "".join(parts)

        events.append(
            f"Dialogue: 0, {ass_time(start_rel)}, {ass_time(end_rel)}, "
            f"{style_name}, , 0, 0, 0, , {text}"
        )

    content = (
        _ass_header()
        + "\n"
        + _style_section(style_name)
        + "\n"
        + _events_header()
        + "\n"
        + "\n".join(events)
        + "\n"
    )

    if output_path is None:
        output_path = Path("subtitles.ass")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info(
        "Subtítulos .ass generados: %s (%d líneas, estilo=%s)",
        path,
        len(events),
        style_name,
    )
    return path


def _ass_header() -> str:
    return (
        "[Script Info]\n"
        "Title: ClipForge Subtitles\n"
        f"PlayResX: {ASS_WIDTH}\n"
        f"PlayResY: {ASS_HEIGHT}\n"
        "Timer: 100,0000\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
    )


def _events_header() -> str:
    return (
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    )


if __name__ == "__main__":
    import argparse
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Generar archivo .ass de subtítulos para un clip"
    )
    parser.add_argument("words_json", help="JSON con lista de palabras (start, end, text)")
    parser.add_argument("clip_start", type=float, help="Inicio del clip en segundos")
    parser.add_argument("output", help="Ruta del archivo .ass de salida")
    parser.add_argument(
        "--style",
        default="clasico",
        help="Estilo de subtítulos (clasico, resaltado, minimal)",
    )
    args = parser.parse_args()

    data = json.loads(Path(args.words_json).read_text(encoding="utf-8"))
    words = [Word(**w) for w in data]
    generate_ass(words, args.clip_start, args.style, args.output)
    print(f".ass generado: {args.output}")
