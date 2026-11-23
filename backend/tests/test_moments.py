"""Pruebas de la selección de momentos (mocks, sin LLM real ni video real)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.pipeline.moments import (
    select_moments,
    _make_windows,
    _iou,
    _dedup,
    _adjust_to_word_boundaries,
    Moment,
    MomentCandidate,
)
from app.pipeline.transcribe import Transcript, Word, Segment


def _make_transcript() -> Transcript:
    """Transcript de ejemplo con palabras y segmentos."""
    words = [
        Word(text="Hola", start=0.0, end=0.5, prob=0.9),
        Word(text="mundo", start=0.5, end=1.0, prob=0.9),
        Word(text="esto", start=1.0, end=1.5, prob=0.9),
        Word(text="es", start=1.5, end=1.8, prob=0.9),
        Word(text="una", start=1.8, end=2.2, prob=0.9),
        Word(text="prueba", start=2.2, end=3.0, prob=0.9),
        Word(text="de", start=3.0, end=3.3, prob=0.9),
        Word(text="transcripcion", start=3.3, end=4.2, prob=0.9),
        Word(text="para", start=4.2, end=4.7, prob=0.9),
        Word(text="momentos", start=4.7, end=5.5, prob=0.9),
    ]
    segments = [
        Segment(id=0, start=0.0, end=5.5, text="Hola mundo esto es una prueba de transcripcion para momentos", words=words),
    ]
    return Transcript(language="es", words=words, segments=segments)


def test_make_windows():
    """_make_windows debe crear ventanas con solape."""
    transcript = _make_transcript()
    windows = _make_windows(transcript)
    assert len(windows) >= 1
    # Primera ventana empieza en 0
    assert windows[0][0] == 0.0
    # Las ventanas deben tener solape
    if len(windows) > 1:
        assert windows[1][0] < windows[0][1]


def test_iou():
    """_iou debe calcular intersección sobre unión."""
    assert _iou(0, 10, 5, 15) == 5.0 / 15.0  # intersección 5, unión 15
    assert _iou(0, 5, 10, 15) == 0.0  # sin solape
    assert _iou(0, 10, 2, 8) == 6.0 / 10.0  # uno dentro del otro


def test_dedup_keeps_highest_score():
    """_dedup debe conservar el momento de mayor score cuando hay solape."""
    moments = [
        Moment(id=0, start=0.0, end=30.0, title="A", reason="r", score=8.0),
        Moment(id=1, start=10.0, end=40.0, title="B", reason="r", score=9.0),  # solape IoU=0.5 > 0.3
        Moment(id=2, start=100.0, end=120.0, title="C", reason="r", score=7.0),  # sin solape
    ]
    result = _dedup(moments, iou_threshold=0.3)
    # B tiene score mayor y se solapa con A, así que se conserva B y C
    ids = {m.id for m in result}
    assert ids == {1, 2}


def test_dedup_no_overlap_keeps_all():
    """Si no hay solape, _dedup conserva todos."""
    moments = [
        Moment(id=0, start=0.0, end=30.0, title="A", reason="r", score=5.0),
        Moment(id=1, start=100.0, end=130.0, title="B", reason="r", score=6.0),
    ]
    result = _dedup(moments)
    assert len(result) == 2


def test_adjust_to_word_boundaries():
    """_adjust_to_word_boundaries debe ajustar start/end a palabras."""
    transcript = _make_transcript()
    moments = [
        Moment(id=0, start=0.7, end=4.6, title="A", reason="r", score=5.0),
    ]
    result = _adjust_to_word_boundaries(moments, transcript)

    # start=0.7 → primera palabra con end>=0.7 es "mundo" (end=1.0) → start=0.5
    assert result[0].start == 0.5
    # end=4.6 → última palabra con start<=4.6 es "para" (start=4.2) → end=4.7
    assert result[0].end == 4.7


def test_select_moments_uses_existing_without_force(tmp_path):
    """Si existe moments.json y no hay --force, se carga sin llamar al LLM."""
    video_id = "video_test"
    data_dir = settings.data_dir / video_id
    data_dir.mkdir(parents=True, exist_ok=True)
    moments_path = data_dir / "moments.json"

    existing = [
        Moment(id=0, start=10.0, end=30.0, title="cached", reason="r", score=9.0),
    ]
    import json as _json
    moments_path.write_text(_json.dumps([m.__dict__ for m in existing]), encoding="utf-8")

    with patch("app.pipeline.moments.create_client") as mock_client:
        result = select_moments(video_id, force=False)

    mock_client.assert_not_called()
    assert len(result) == 1
    assert result[0].title == "cached"


def test_select_moments_calls_llm_per_window(monkeypatch, tmp_path):
    """select_moments debe llamar al LLM por ventana y unir resultados."""
    video_id = "video_test2"
    data_dir = settings.data_dir / video_id
    data_dir.mkdir(parents=True, exist_ok=True)

    # Crear transcript.json real para que se cargue
    transcript = _make_transcript()
    from app.pipeline.transcribe import _save_transcript
    _save_transcript(transcript, data_dir / "transcript.json")

    # Mock del cliente LLM: devuelve un momento por ventana
    mock_instance = MagicMock()

    def fake_ask_json(messages, schema, **kwargs):
        return schema(
            moments=[
                MomentCandidate(start=0.0, end=25.0, title="momento 1", reason="r", score=8.0)
            ]
        )

    mock_instance.ask_json.side_effect = fake_ask_json

    with patch("app.pipeline.moments.create_client", return_value=mock_instance):
        result = select_moments(video_id, force=True)

    assert mock_instance.ask_json.call_count >= 1
    assert len(result) >= 1
    assert result[0].title == "momento 1"


def test_select_moments_filters_duration_out_of_range(monkeypatch, tmp_path):
    """Momentos con duración fuera de 20-60 s deben filtrarse."""
    video_id = "video_test3"
    data_dir = settings.data_dir / video_id
    data_dir.mkdir(parents=True, exist_ok=True)

    transcript = _make_transcript()
    from app.pipeline.transcribe import _save_transcript
    _save_transcript(transcript, data_dir / "transcript.json")

    mock_instance = MagicMock()

    def fake_ask_json(messages, schema, **kwargs):
        return schema(
            moments=[
                MomentCandidate(start=0.0, end=10.0, title="demasiado corto", reason="r", score=9.0),
                MomentCandidate(start=0.0, end=100.0, title="demasiado largo", reason="r", score=9.0),
                MomentCandidate(start=0.0, end=30.0, title="bien", reason="r", score=8.0),
            ]
        )

    mock_instance.ask_json.side_effect = fake_ask_json

    with patch("app.pipeline.moments.create_client", return_value=mock_instance):
        result = select_moments(video_id, force=True)

    titles = {m.title for m in result}
    assert "bien" in titles
    assert "demasiado corto" not in titles
    assert "demasiado largo" not in titles


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
