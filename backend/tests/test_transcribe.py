"""Pruebas de la etapa de transcripción (faster-whisper).

Usan mocks para no requerir faster-whisper ni GPU instalados.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.config import settings
from app.pipeline.transcribe import (
    Word,
    Segment,
    Transcript,
    _to_word,
    _save_transcript,
    _load_transcript,
    transcribe,
    WhisperModel,
)


def test_to_word_converts_faster_whisper_word():
    """_to_word debe extraer text, start, end, prob de un objeto palabra."""
    fake = MagicMock()
    fake.word = "hola"
    fake.start = 1.5
    fake.end = 2.0
    fake.probability = 0.95

    w = _to_word(fake)
    assert w.text == "hola"
    assert w.start == 1.5
    assert w.end == 2.0
    assert w.prob == 0.95


def test_to_word_handles_missing_attributes():
    """Si faltan atributos, usar valores por defecto."""
    fake = MagicMock()
    del fake.word
    del fake.start
    del fake.end
    del fake.probability

    w = _to_word(fake)
    assert w.text == ""
    assert w.start == 0.0
    assert w.end == 0.0
    assert w.prob == 0.0


def test_save_and_load_transcript_roundtrip(tmp_path):
    """Guardar y cargar transcript debe ser un roundtrip fiel."""
    transcript = Transcript(
        language="es",
        words=[
            Word(text="hola", start=0.0, end=0.5, prob=0.9),
            Word(text="mundo", start=0.5, end=1.0, prob=0.85),
        ],
        segments=[
            Segment(id=0, start=0.0, end=1.0, text="hola mundo",
                    words=[
                        Word(text="hola", start=0.0, end=0.5, prob=0.9),
                        Word(text="mundo", start=0.5, end=1.0, prob=0.85),
                    ]),
        ],
    )

    path = tmp_path / "transcript.json"
    _save_transcript(transcript, path)
    assert path.exists()

    loaded = _load_transcript(path)
    assert loaded.language == "es"
    assert len(loaded.words) == 2
    assert loaded.words[0].text == "hola"
    assert loaded.words[1].text == "mundo"
    assert len(loaded.segments) == 1
    assert loaded.segments[0].id == 0
    assert loaded.segments[0].text == "hola mundo"
    assert loaded.segments[0].words[0].text == "hola"


def test_transcribe_uses_existing_transcript_without_force(tmp_path):
    """Si existe transcript.json y --force no se pide, no recalcular."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    video_id = video.stem
    data_dir = settings.data_dir / video_id
    data_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = data_dir / "transcript.json"

    existing = Transcript(
        language="es",
        words=[Word(text="cached", start=0.0, end=0.5, prob=1.0)],
        segments=[],
    )
    _save_transcript(existing, transcript_path)

    with patch("app.pipeline.transcribe._load_model") as mock_load:
        result = transcribe(video, force=False)

    mock_load.assert_not_called()
    assert result.language == "es"
    assert result.words[0].text == "cached"


def test_transcribe_forces_recalculation(monkeypatch, tmp_path):
    """Con --force se recalcula aunque exista transcript.json."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    data_dir = tmp_path / "video"
    data_dir.mkdir()
    transcript_path = data_dir / "transcript.json"

    _save_transcript(
        Transcript(language="es", words=[], segments=[]), transcript_path
    )

    # Mock de ingest (para que no necesite ffmpeg real)
    fake_audio = data_dir / "audio.wav"
    fake_audio.write_bytes(b"fake audio")

    def fake_ingest(vp):
        from app.pipeline.ingest import VideoInfo
        return VideoInfo(duration=10.0, width=1920, height=1080, fps=30.0), fake_audio

    with patch("app.pipeline.transcribe.ingest", side_effect=fake_ingest), \
         patch("app.pipeline.transcribe._load_model") as mock_load:
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "hola mundo"
        mock_segment.words = []
        mock_model.transcribe.return_value = ([mock_segment], MagicMock(language="es"))
        mock_load.return_value = mock_model

        result = transcribe(video, force=True)

    mock_load.assert_called_once()
    assert result.language == "es"
    assert len(result.segments) == 1
    assert result.segments[0].text == "hola mundo"


def test_transcribe_model_fallback_int8(monkeypatch, tmp_path):
    """Si int8_float16 falla, _load_model debe intentar int8 y avisar en log."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    data_dir = settings.data_dir / video.stem
    data_dir.mkdir(parents=True, exist_ok=True)
    fake_audio = data_dir / "audio.wav"
    fake_audio.write_bytes(b"fake audio")

    def fake_ingest(vp):
        from app.pipeline.ingest import VideoInfo
        return VideoInfo(duration=10.0, width=1920, height=1080, fps=30.0), fake_audio

    # Primera instancia (int8_float16) lanza excepción; segunda (int8) funciona.
    mock_instance = MagicMock()
    mock_instance.transcribe.return_value = ([], MagicMock(language="es"))

    whisper_mock = MagicMock()
    whisper_mock.side_effect = [
        RuntimeError("falló int8_float16"),
        mock_instance,
    ]

    with patch("app.pipeline.transcribe.ingest", side_effect=fake_ingest), \
         patch("app.pipeline.transcribe.WhisperModel", whisper_mock):
        transcribe(video, force=True)

    # WhisperModel se intentó dos veces: int8_float16 (falló) y int8 (OK)
    assert whisper_mock.call_count == 2
    first_call_kwargs = whisper_mock.call_args_list[0].kwargs
    second_call_kwargs = whisper_mock.call_args_list[1].kwargs
    assert first_call_kwargs["compute_type"] == "int8_float16"
    assert second_call_kwargs["compute_type"] == "int8"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
