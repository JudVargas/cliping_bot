"""Pruebas de la etapa de subtítulos (captions.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.pipeline.captions import (
    STYLES,
    ass_time,
    available_styles,
    generate_ass,
    group_words_into_lines,
)
from app.pipeline.transcribe import Word


def _make_words():
    return [
        Word(text="Hola", start=0.0, end=0.5, prob=0.9),
        Word(text="mundo", start=0.5, end=1.0, prob=0.9),
        Word(text="esto", start=1.0, end=1.5, prob=0.9),
        Word(text="es", start=1.5, end=1.8, prob=0.9),
        Word(text="una", start=1.8, end=2.2, prob=0.9),
        Word(text="prueba", start=2.2, end=3.0, prob=0.9),
    ]


def test_ass_time_conversion():
    """ass_time debe convertir segundos a H:MM:SS.cc."""
    assert ass_time(0.0) == "0:00:00.00"
    assert ass_time(1.5) == "0:00:01.50"
    assert ass_time(61.25) == "0:01:01.25"
    assert ass_time(3661.99) == "1:01:01.99"
    assert ass_time(0.01) == "0:00:00.01"


def test_available_styles():
    """available_styles debe devolver los 3 estilos."""
    styles = available_styles()
    assert "clasico" in styles
    assert "resaltado" in styles
    assert "minimal" in styles
    assert len(styles) == 3


def test_styles_dict_has_entries():
    """STYLES debe tener las claves esperadas."""
    assert "clasico" in STYLES
    assert "resaltado" in STYLES
    assert "minimal" in STYLES


def test_group_words_into_lines_basic():
    """group_words_into_lines debe agrupar en líneas de hasta 5 palabras."""
    words = _make_words()
    lines = group_words_into_lines(words, max_per_line=3)
    assert len(lines) == 2  # 6 palabras / 3 por línea = 2 líneas
    assert len(lines[0]) == 3
    assert len(lines[1]) == 3


def test_group_words_into_lines_respects_gap():
    """Si hay un gap grande (>0.7s), debe empezar nueva línea."""
    words = [
        Word(text="A", start=0.0, end=0.5, prob=0.9),
        Word(text="B", start=0.5, end=1.0, prob=0.9),
        Word(text="C", start=2.0, end=2.5, prob=0.9),  # gap de 1.0s
        Word(text="D", start=2.5, end=3.0, prob=0.9),
    ]
    lines = group_words_into_lines(words, max_per_line=5)
    assert len(lines) == 2
    assert lines[0] == [words[0], words[1]]
    assert lines[1] == [words[2], words[3]]


def test_generate_ass_creates_file(tmp_path):
    """generate_ass debe crear un archivo .ass con contenido válido."""
    words = _make_words()
    out = tmp_path / "subs.ass"
    path = generate_ass(words, clip_start=0.0, style_name="clasico", output_path=out)

    assert path == out
    assert out.exists()
    content = out.read_text(encoding="utf-8")

    # Debe contener secciones ASS
    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    # Eventos de diálogo
    assert "Dialogue: 0," in content
    # Karaoke tags
    assert "\\k" in content


def test_generate_ass_relative_times(tmp_path):
    """Los tiempos del .ass deben ser relativos al inicio del clip."""
    words = [
        Word(text="A", start=10.0, end=10.5, prob=0.9),
        Word(text="B", start=10.5, end=11.0, prob=0.9),
    ]
    out = tmp_path / "subs.ass"
    generate_ass(words, clip_start=10.0, style_name="clasico", output_path=out)
    content = out.read_text(encoding="utf-8")

    # Primer evento debe empezar en 0:00:00.00 (relativo al clip)
    assert "0:00:00.00" in content
    # No debe contener el tiempo absoluto 10.0 como inicio de evento
    assert "0:00:10.00" not in content


def test_generate_ass_invalid_style_raises(tmp_path):
    """Estilo inválido debe lanzar ValueError."""
    words = _make_words()
    with pytest.raises(ValueError):
        generate_ass(words, clip_start=0.0, style_name="estilo_inexistente", output_path=tmp_path / "x.ass")


def test_generate_ass_empty_words(tmp_path):
    """Con lista vacía de palabras, debe generar un .ass sin eventos."""
    out = tmp_path / "empty.ass"
    path = generate_ass([], clip_start=0.0, style_name="clasico", output_path=out)
    assert path.exists()
    content = out.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "[Events]" in content
    assert "Dialogue:" not in content


def test_generate_ass_all_styles(tmp_path):
    """Cada estilo debe generar un archivo válido con su nombre en Style."""
    words = _make_words()
    for style_name in ["clasico", "resaltado", "minimal"]:
        out = tmp_path / f"{style_name}.ass"
        generate_ass(words, clip_start=0.0, style_name=style_name, output_path=out)
        content = out.read_text(encoding="utf-8")
        assert f"Style: {style_name}," in content


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
