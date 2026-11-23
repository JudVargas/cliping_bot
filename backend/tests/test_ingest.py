"""Pruebas de la etapa de ingesta (ffprobe + extraer audio).

Usan mocks de subprocess para no requerir ffmpeg instalado.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.pipeline.ingest import probe_video, extract_audio, ingest, VideoInfo


class FakeCompletedProcess:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr


FFPROBE_OUTPUT = json.dumps({
    "streams": [
        {
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30000/1001",
            "duration": "120.5",
        }
    ],
    "format": {"duration": "120.5"},
})


def test_probe_video_returns_metadata(monkeypatch, tmp_path):
    """probe_video debe parsear duración, resolución y fps de ffprobe."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def fake_run(cmd, capture_output, text, check=False):
        assert cmd[0] == "ffmpeg" or cmd[0] == "ffprobe", cmd
        return FakeCompletedProcess(FFPROBE_OUTPUT)

    with patch("app.pipeline.ingest.subprocess.run", side_effect=fake_run):
        info = probe_video(video)

    assert isinstance(info, VideoInfo)
    assert info.width == 1920
    assert info.height == 1080
    assert info.duration == 120.5
    # 30000/1001 ≈ 29.97
    assert abs(info.fps - 29.97002997002997) < 1e-6


def test_probe_video_decimal_fps(monkeypatch, tmp_path):
    """El fps puede venir como decimal directo."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    output = json.dumps({
        "streams": [{
            "width": 1280,
            "height": 720,
            "r_frame_rate": "25",
            "duration": "60.0",
        }],
        "format": {"duration": "60.0"},
    })

    def fake_run(cmd, capture_output, text, check=False):
        return FakeCompletedProcess(output)

    with patch("app.pipeline.ingest.subprocess.run", side_effect=fake_run):
        info = probe_video(video)

    assert info.fps == 25.0


def test_probe_video_missing_file_raises(tmp_path):
    """Si el video no existe, debe lanzar FileNotFoundError."""
    missing = tmp_path / "no_existe.mp4"
    with pytest.raises(FileNotFoundError):
        probe_video(missing)


def test_probe_video_ffprobe_failure_raises(monkeypatch, tmp_path):
    """Si ffprobe falla, debe lanzar RuntimeError."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def fake_run(cmd, capture_output, text, check=False):
        return FakeCompletedProcess("", returncode=1, stderr="error de ffprobe")

    with patch("app.pipeline.ingest.subprocess.run", side_effect=fake_run):
        with pytest.raises(RuntimeError):
            probe_video(video)


def test_extract_audio_ffmpeg_command(tmp_path):
    """extract_audio debe construir el comando de ffmpeg sin shell=True."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    captured = {}

    def fake_run(cmd, capture_output, text, check=False):
        captured["cmd"] = cmd
        return FakeCompletedProcess("")

    with patch("app.pipeline.ingest.subprocess.run", side_effect=fake_run):
        path = extract_audio(video, output_dir=tmp_path / "out")

    assert captured["cmd"][0] == "ffmpeg"
    assert "-vn" in captured["cmd"]
    assert "-acodec" in captured["cmd"]
    assert "pcm_s16le" in captured["cmd"]
    assert "-ar" in captured["cmd"]
    assert "16000" in captured["cmd"]
    assert "-ac" in captured["cmd"]
    assert "1" in captured["cmd"]
    assert path.suffix == ".wav"
    assert path.name == "audio.wav"
    # shell=True nunca se usa: subprocess.run recibe lista y check=False


def test_ingest_returns_info_and_audio(monkeypatch, tmp_path):
    """ingest devuelve (VideoInfo, ruta_audio)."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")

    def fake_run(cmd, capture_output, text, check=False):
        if cmd[0] == "ffprobe":
            return FakeCompletedProcess(FFPROBE_OUTPUT)
        return FakeCompletedProcess("")

    with patch("app.pipeline.ingest.subprocess.run", side_effect=fake_run):
        info, audio_path = ingest(video)

    assert isinstance(info, VideoInfo)
    assert audio_path.name == "audio.wav"
