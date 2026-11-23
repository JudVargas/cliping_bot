"""Pruebas de la etapa de render (mocks de subprocess, sin ffmpeg real)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.render import (
    render_clip,
    _encoder_available,
    _pick_video_encoder,
    _find_video,
)
from app.pipeline.moments import Moment


class FakeCompletedProcess:
    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


def test_render_clip_uses_ffmpeg_list_args(tmp_path):
    """render_clip debe llamar a ffmpeg con lista de argumentos (no shell)."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video")
    out = tmp_path / "out" / "clip.mp4"

    captured = {}

    def fake_run(cmd, capture_output, text, check=False):
        captured["cmd"] = cmd
        return FakeCompletedProcess("", returncode=0)

    with patch("app.pipeline.render.subprocess.run", side_effect=fake_run), \
         patch("app.pipeline.render._encoder_available", return_value=True):
        result = render_clip(video, 10.0, 30.0, out)

    cmd = captured["cmd"]
    assert cmd[0] == "ffmpeg"
    assert "-y" in cmd
    assert "-ss" in cmd
    assert "10.000000" in cmd
    assert "-to" in cmd
    assert "20.000000" in cmd  # duration = end - start
    assert "-c:v" in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd
    assert str(out) in cmd
    # Nunca shell=True: subprocess.run recibe lista
    assert result == out


def test_render_clip_encoder_fallback_nvenc_to_libx264(tmp_path):
    """Si nvenc falla, render_clip debe reintentar con libx264."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video")
    out = tmp_path / "out" / "clip.mp4"

    call_count = 0

    def fake_run(cmd, capture_output, text, check=False):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Primera llamada (nvenc) falla
            return FakeCompletedProcess("", returncode=1, stderr="nvenc error")
        # Segunda llamada (libx264) OK
        return FakeCompletedProcess("", returncode=0)

    with patch("app.pipeline.render.subprocess.run", side_effect=fake_run), \
         patch("app.pipeline.render._encoder_available", return_value=True):
        result = render_clip(video, 5.0, 25.0, out, encoder="h264_nvenc")

    assert call_count == 2
    assert result == out


def test_render_clip_invalid_range_raises(tmp_path):
    """end <= start debe lanzar ValueError."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    with pytest.raises(ValueError):
        render_clip(video, 30.0, 10.0, tmp_path / "out.mp4")


def test_render_clip_missing_video_raises(tmp_path):
    """Video inexistente debe lanzar FileNotFoundError."""
    missing = tmp_path / "no_existe.mp4"
    with pytest.raises(FileNotFoundError):
        render_clip(missing, 0.0, 10.0, tmp_path / "out.mp4")


def test_pick_video_encoder_fallback():
    """_pick_video_encoder debe devolver libx264 si el preferido no está."""
    with patch("app.pipeline.render._encoder_available", return_value=False):
        enc = _pick_video_encoder("h264_nvenc")
    assert enc == "libx264"


def test_pick_video_encoder_preferred_available():
    """Si el preferido está disponible, se usa."""
    with patch("app.pipeline.render._encoder_available", return_value=True):
        enc = _pick_video_encoder("h264_nvenc")
    assert enc == "h264_nvenc"


def test_find_video_in_data_dir(tmp_path):
    """_find_video debe buscar en data/<video_id>/ y en data/."""
    video_dir = tmp_path / "mi_video"
    video_dir.mkdir()
    video_file = video_dir / "mi_video.mp4"
    video_file.write_bytes(b"fake video")

    result = _find_video("mi_video", data_dir=tmp_path)
    assert result == video_file


def test_find_video_not_found(tmp_path):
    """Si no hay video, _find_video debe lanzar FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        _find_video("no_existe", data_dir=tmp_path)


def test_moment_asdict_serialization():
    """Moment debe ser serializable con asdict (usado en render_log)."""
    m = Moment(id=0, start=10.0, end=30.0, title="t", reason="r", score=8.0)
    d = __import__("dataclasses").asdict(m)
    assert d["start"] == 10.0
    assert d["end"] == 30.0
    assert d["title"] == "t"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
