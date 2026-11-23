"""Pruebas de la etapa de reencuadre vertical (reframe.py).

Usan mocks de OpenCV y MediaPipe para no requerir hardware real ni video.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.pipeline.reframe import (
    CropKeyframe,
    _compute_crop,
    _ema_smooth,
    _interpolate_keyframe,
    detect_trajectory,
    load_keyframes,
    reframe_clip,
    save_keyframes,
    smooth_trajectory,
)


def test_compute_crop_with_face():
    """_compute_crop debe centrar el recorte en la cara."""
    face_box = (400, 300, 200, 250)  # x, y, w, h
    frame_w, frame_h = 1920, 1080
    kf = _compute_crop(face_box, frame_w, frame_h, None, t=1.0)

    assert isinstance(kf, CropKeyframe)
    assert kf.w > 0
    assert kf.h > 0
    # Aspect ratio 9:16
    assert abs(kf.w / kf.h - 9 / 16) < 0.05
    # La cara debe estar cerca del centro del recorte (en X)
    face_cx = face_box[0] + face_box[2] // 2
    crop_cx = kf.x + kf.w // 2
    assert abs(face_cx - crop_cx) < kf.w // 2


def test_compute_crop_without_face_keeps_last():
    """Sin cara y con last_crop, debe devolver el mismo recorte."""
    last = CropKeyframe(t=0.0, x=100, y=100, w=500, h=900)
    kf = _compute_crop(None, 1920, 1080, last, t=2.0)
    assert kf.x == last.x
    assert kf.y == last.y
    assert kf.w == last.w
    assert kf.h == last.h


def test_ema_smooth():
    """_ema_smooth debe interpolar entre actual y anterior."""
    current = CropKeyframe(t=1.0, x=100, y=100, w=500, h=900)
    previous = CropKeyframe(t=0.0, x=0, y=0, w=500, h=900)
    smoothed = _ema_smooth(current, previous, alpha=0.5)

    assert smoothed.x == 50  # (100 + 0) / 2
    assert smoothed.y == 50
    assert smoothed.w == 500
    assert smoothed.h == 900


def test_smooth_trajectory():
    """smooth_trajectory debe devolver keyframes suavizados."""
    keyframes = [
        CropKeyframe(t=0.0, x=0, y=0, w=500, h=900),
        CropKeyframe(t=1.0, x=100, y=100, w=500, h=900),
        CropKeyframe(t=2.0, x=200, y=200, w=500, h=900),
    ]
    smoothed = smooth_trajectory(keyframes, alpha=0.5)
    assert len(smoothed) == 3
    assert smoothed[0] == keyframes[0]  # primero no cambia
    assert smoothed[1].x == 50  # (0+100)/2


def test_interpolate_keyframe():
    """_interpolate_keyframe debe interpolar linealmente entre keyframes."""
    keyframes = [
        CropKeyframe(t=0.0, x=0, y=0, w=500, h=900),
        CropKeyframe(t=2.0, x=100, y=100, w=500, h=900),
    ]
    kf = _interpolate_keyframe(keyframes, t=1.0)
    assert kf.x == 50
    assert kf.y == 50

    # Antes del primero
    kf = _interpolate_keyframe(keyframes, t=-1.0)
    assert kf == keyframes[0]

    # Después del último
    kf = _interpolate_keyframe(keyframes, t=10.0)
    assert kf == keyframes[-1]


def test_save_and_load_keyframes(tmp_path):
    """Guardar y cargar keyframes debe ser un roundtrip."""
    keyframes = [
        CropKeyframe(t=0.0, x=10, y=20, w=300, h=540),
        CropKeyframe(t=1.0, x=110, y=120, w=300, h=540),
    ]
    path = tmp_path / "keyframes.json"
    save_keyframes(keyframes, path)
    assert path.exists()

    loaded = load_keyframes(path)
    assert len(loaded) == 2
    assert loaded[0].t == 0.0
    assert loaded[0].x == 10
    assert loaded[1].t == 1.0
    assert loaded[1].x == 110


def test_reframe_clip_ffmpeg_command(tmp_path):
    """reframe_clip debe construir el comando de ffmpeg correctamente (mock)."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video")
    out = tmp_path / "out" / "vertical.mp4"

    # Mock de cv2.VideoCapture para simular lectura de frames
    fake_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)

    class FakeCap:
        def __init__(self):
            self.frame_idx = 0
            self.fps = 30.0

        def isOpened(self):
            return True

        def get(self, prop):
            if prop == cv2.CAP_PROP_FPS:
                return self.fps
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 1920.0
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 1080.0
            if prop == cv2.CAP_PROP_FRAME_COUNT:
                return 90.0
            return 0.0

        def read(self):
            if self.frame_idx >= 30:  # 1 segundo de video
                return False, None
            frame = fake_frame.copy()
            self.frame_idx += 1
            return True, frame

        def release(self):
            pass

    captured_cmds = []

    class FakeProcess:
        def __init__(self, cmd, **kwargs):
            captured_cmds.append(cmd)
            self.stdin = MagicMock()
            self.stdin.write = MagicMock()
            self.stdin.close = MagicMock()
            self.stderr = MagicMock()
            self.stderr.read = MagicMock(return_value=b"")
            self.returncode = 0

        def wait(self):
            self.returncode = 0

    with patch("cv2.VideoCapture", return_value=FakeCap()), \
         patch("subprocess.Popen", side_effect=lambda cmd, **kw: FakeProcess(cmd, **kw)), \
         patch("app.pipeline.reframe.detect_trajectory", return_value=[]), \
         patch("app.pipeline.reframe.smooth_trajectory", return_value=[
             CropKeyframe(t=0.0, x=0, y=0, w=900, h=1600),
             CropKeyframe(t=1.0, x=0, y=0, w=900, h=1600),
         ]):
        result = reframe_clip(video, 0.0, 1.0, out)

    assert result == out
    assert len(captured_cmds) >= 1
    cmd = captured_cmds[0]
    assert cmd[0] == "ffmpeg"
    assert "-f" in cmd
    assert "rawvideo" in cmd
    assert "-i" in cmd
    assert str(out) in cmd


def test_reframe_clip_invalid_range_raises(tmp_path):
    """end <= start debe lanzar ValueError."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    with pytest.raises(ValueError):
        reframe_clip(video, 10.0, 5.0, tmp_path / "out.mp4")


def test_reframe_clip_missing_video_raises(tmp_path):
    """Video inexistente debe lanzar FileNotFoundError."""
    missing = tmp_path / "no_existe.mp4"
    with pytest.raises(FileNotFoundError):
        reframe_clip(missing, 0.0, 10.0, tmp_path / "out.mp4")


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
