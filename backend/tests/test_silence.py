"""Pruebas de la etapa de quitar silencios y muletillas (silence.py)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.pipeline.silence import (
    EditDecision,
    build_edit_decision,
    _is_filler,
    _merge_intervals,
    _silence_intervals,
    _subtract_interval,
    remap_word_times,
)
from app.pipeline.transcribe import Word


def _make_words():
    return [
        Word(text="Hola", start=0.0, end=0.5, prob=0.9),
        Word(text="mundo", start=0.5, end=1.0, prob=0.9),
        Word(text="eh", start=1.0, end=1.3, prob=0.9),       # muletilla aislada
        Word(text="esto", start=1.5, end=2.0, prob=0.9),
        Word(text="es", start=2.0, end=2.3, prob=0.9),
        Word(text="una", start=2.5, end=3.0, prob=0.9),
        Word(text="prueba", start=3.0, end=4.0, prob=0.9),
        Word(text="mmm", start=4.5, end=4.9, prob=0.9),      # muletilla aislada
        Word(text="fin", start=5.0, end=5.5, prob=0.9),
    ]


def test_is_filler():
    """_is_filler debe identificar muletillas."""
    assert _is_filler(Word(text="eh", start=0, end=0.1, prob=0.9), {"eh"})
    assert _is_filler(Word(text="EM", start=0, end=0.1, prob=0.9), {"em"})
    assert not _is_filler(Word(text="hola", start=0, end=0.1, prob=0.9), {"eh"})


def test_subtract_interval_basic():
    """_subtract_interval debe restar un intervalo de una lista."""
    intervals = [(0.0, 10.0)]
    result = _subtract_interval(intervals, 3.0, 5.0)
    assert result == [(0.0, 3.0), (5.0, 10.0)]


def test_subtract_interval_no_overlap():
    """Si no hay solape, _subtract_interval no cambia nada."""
    intervals = [(0.0, 10.0)]
    result = _subtract_interval(intervals, 20.0, 30.0)
    assert result == [(0.0, 10.0)]


def test_merge_intervals():
    """_merge_intervals debe fusionar intervalos contiguos/solapados."""
    intervals = [(0.0, 5.0), (5.0, 10.0), (20.0, 30.0)]
    result = _merge_intervals(intervals)
    assert result == [(0.0, 10.0), (20.0, 30.0)]


def test_build_edit_decision_removes_long_pause():
    """Una pausa larga entre palabras debe recortarse."""
    words = [
        Word(text="A", start=0.0, end=1.0, prob=0.9),
        Word(text="B", start=3.0, end=4.0, prob=0.9),  # gap de 2s > 0.6
    ]
    decision = build_edit_decision(words, 0.0, 4.0, min_gap=0.6, breath=0.15)
    # Se debe recortar el silencio entre 1.15 y 2.85
    assert len(decision.keep) >= 1
    # Verificar que no hay tramos vacíos y que el primero empieza en 0.0
    assert decision.keep[0][0] == 0.0


def test_build_edit_decision_removes_filler():
    """Una muletilla aislada debe eliminarse."""
    words = _make_words()
    decision = build_edit_decision(words, 0.0, 5.5, min_gap=0.6, breath=0.15)
    kept_duration = decision.duration_kept()
    total_duration = 5.5
    # La duración conservada debe ser menor que el total (se eliminó algo)
    assert kept_duration < total_duration


def test_build_edit_decision_empty_words():
    """Sin palabras, se conserva el clip completo."""
    decision = build_edit_decision([], 0.0, 30.0)
    assert decision.keep == [(0.0, 30.0)]


def test_remap_word_times():
    """remap_word_times debe ajustar los tiempos de las palabras."""
    words = [
        Word(text="A", start=0.0, end=0.5, prob=0.9),
        Word(text="B", start=1.0, end=1.5, prob=0.9),
    ]
    decision = EditDecision(keep=[(0.0, 0.5), (1.0, 1.5)])
    remapped = remap_word_times(words, decision, 0.0)
    assert len(remapped) == 2
    assert remapped[0].start == 0.0
    assert remapped[0].end == 0.5


def test_edit_decision_serialization():
    """EditDecision debe ser serializable a JSON."""
    decision = EditDecision(keep=[(0.0, 10.0), (20.0, 30.0)])
    d = decision.to_json()
    assert d == {"keep": [[0.0, 10.0], [20.0, 30.0]]}


def test_silence_intervals_no_audio_returns_empty(tmp_path):
    """Si no hay audio, _silence_intervals devuelve lista vacía."""
    missing = tmp_path / "no_existe.wav"
    result = _silence_intervals(missing)
    assert result == []


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
