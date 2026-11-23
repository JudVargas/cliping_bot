"""Pruebas de la Etapa 7: reencuadre multi-persona (reframe.py v2).

Usan mocks de OpenCV y MediaPipe para no requerir hardware real ni video.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from app.pipeline.reframe import (
    MODE_AUTO,
    MODE_SINGLE,
    MODE_SPLIT,
    CropKeyframe,
    FaceTracker,
    TrackedFace,
    VoiceActivityDetector,
    _compute_crop_for_face,
    _ema_smooth,
    _iou,
    _mouth_open_ratio,
    _split_screen_crops,
    detect_trajectory,
    load_keyframes,
    reframe_clip,
    save_keyframes,
    select_speaker,
    smooth_trajectory,
)


# ---------------------------------------------------------------------------
# FaceTracker
# ---------------------------------------------------------------------------

def test_face_tracker_assign_ids_stably():
    """El tracker debe dar ids estables a caras que se mantienen entre frames."""
    tracker = FaceTracker(iou_threshold=0.3, max_lost=5)

    # Frame 1: una cara
    frame1 = [(100, 100, 100, 100, 0.9)]
    tracks1 = tracker.update(frame1, frame_idx=0)
    assert len(tracks1) == 1
    assert tracks1[0].face_id == 0

    # Frame 2: misma cara (IoU alto)
    frame2 = [(105, 105, 100, 100, 0.9)]
    tracks2 = tracker.update(frame2, frame_idx=1)
    assert len(tracks2) == 1
    assert tracks2[0].face_id == 0  # mismo id


def test_face_tracker_new_face_gets_new_id():
    """Una cara nueva debe obtener un id diferente."""
    tracker = FaceTracker(iou_threshold=0.3, max_lost=5)

    frame1 = [(100, 100, 100, 100, 0.9)]
    tracker.update(frame1, frame_idx=0)

    frame2 = [(500, 500, 100, 100, 0.9)]  # cara diferente, sin solape
    tracks2 = tracker.update(frame2, frame_idx=1)
    ids = {t.face_id for t in tracks2}
    assert 0 in ids  # la primera sigue activa (no se perdió aún)
    assert 1 in ids  # la nueva tiene id 1


def test_face_tracker_lost_faces_removed():
    """Las caras que no se detectan por varios frames deben eliminarse."""
    tracker = FaceTracker(iou_threshold=0.3, max_lost=2)

    tracker.update([(100, 100, 100, 100, 0.9)], frame_idx=0)
    # Frames sin detecciones
    tracker.update([], frame_idx=1)
    tracker.update([], frame_idx=2)
    tracker.update([], frame_idx=3)  # max_lost=2, se elimina en el 3

    active = tracker.get_all()
    assert len(active) == 0


# ---------------------------------------------------------------------------
# Funciones de recorte
# ---------------------------------------------------------------------------

def test_compute_crop_for_face_with_face():
    """El recorte debe centrar la cara."""
    face_box = (400, 300, 200, 250)
    frame_w, frame_h = 1920, 1080
    kf = _compute_crop_for_face(face_box, frame_w, frame_h, None, t=1.0)

    assert isinstance(kf, CropKeyframe)
    assert abs(kf.w / kf.h - 9 / 16) < 0.05  # aspect ratio 9:16

    face_cx = face_box[0] + face_box[2] // 2
    crop_cx = kf.x + kf.w // 2
    assert abs(face_cx - crop_cx) < kf.w // 2


def test_compute_crop_for_face_without_face_keeps_last():
    """Sin cara y con last_crop, mantener el mismo recorte."""
    last = CropKeyframe(t=0.0, x=100, y=100, w=500, h=900)
    kf = _compute_crop_for_face(None, 1920, 1080, last, t=2.0)
    assert kf.x == last.x
    assert kf.y == last.y
    assert kf.w == last.w
    assert kf.h == last.h


def test_ema_smooth():
    """EMA debe interpolar entre actual y anterior."""
    current = CropKeyframe(t=1.0, x=100, y=100, w=500, h=900)
    previous = CropKeyframe(t=0.0, x=0, y=0, w=500, h=900)
    smoothed = _ema_smooth(current, previous, alpha=0.5)
    assert smoothed.x == 50
    assert smoothed.y == 50


def test_smooth_trajectory():
    """smooth_trajectory debe devolver keyframes suavizados."""
    keyframes = [
        CropKeyframe(t=0.0, x=0, y=0, w=500, h=900),
        CropKeyframe(t=1.0, x=100, y=100, w=500, h=900),
        CropKeyframe(t=2.0, x=200, y=200, w=500, h=900),
    ]
    smoothed = smooth_trajectory(keyframes, alpha=0.5)
    assert len(smoothed) == 3
    assert smoothed[0] == keyframes[0]
    assert smoothed[1].x == 50


# ---------------------------------------------------------------------------
# Split screen
# ---------------------------------------------------------------------------

def test_split_screen_crops():
    """_split_screen_crops debe devolver dos recortes (arriba/abajo)."""
    face_a = (200, 100, 200, 250)
    face_b = (600, 600, 200, 250)
    frame_w, frame_h = 1920, 1080

    crop_a, crop_b = _split_screen_crops(face_a, face_b, frame_w, frame_h)

    assert crop_a.w == crop_b.w
    assert crop_a.h == crop_b.h
    assert crop_a.h + crop_b.h == crop_a.h * 2  # mitad cada uno
    # crop_a arriba (y menor), crop_b abajo (y mayor)
    assert crop_a.y < crop_b.y


def test_split_screen_crops_no_faces():
    """Sin caras, split screen debe devolver recortes vacíos centrados."""
    crop_a, crop_b = _split_screen_crops(None, None, 1920, 1080)
    assert crop_a.w > 0
    assert crop_b.w > 0


# ---------------------------------------------------------------------------
# Mouth open ratio (Face Mesh)
# ---------------------------------------------------------------------------

def test_mouth_open_ratio_no_landmarks():
    """Sin landmarks, el ratio debe ser 0."""
    mesh = MagicMock()
    mesh.multi_face_landmarks = None
    ratio = _mouth_open_ratio(mesh, None, 1080)
    assert ratio == 0.0


# ---------------------------------------------------------------------------
# VAD
# ---------------------------------------------------------------------------

def test_vad_not_available_without_silero():
    """VoiceActivityDetector no disponible si silero-vad no está instalado."""
    with patch.dict("sys.modules", {"silero_vad": None}):
        vad = VoiceActivityDetector()
        assert not vad.available


# ---------------------------------------------------------------------------
# Select speaker
# ---------------------------------------------------------------------------

def test_select_speaker_no_faces():
    """Sin caras, select_speaker devuelve None."""
    result_id, secs = select_speaker(
        [], None, 0.0, None, 0.0, None, 1080
    )
    assert result_id is None


def test_select_speaker_first_face():
    """Con una cara y sin previo, seleccionar esa cara."""
    faces = [TrackedFace(face_id=0, x=0, y=0, w=100, h=100,
                         confidence=0.9, last_seen_frame=0, speaking=True)]
    result_id, secs = select_speaker(
        faces, None, 0.0, None, 0.0, None, 1080
    )
    assert result_id == 0


# ---------------------------------------------------------------------------
# Keyframes JSON
# ---------------------------------------------------------------------------

def test_save_and_load_keyframes(tmp_path):
    """Guardar y cargar keyframes debe ser roundtrip."""
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


# ---------------------------------------------------------------------------
# Reframing CLI-level (mocks)
# ---------------------------------------------------------------------------

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


def test_reframe_clip_invalid_mode_raises(tmp_path):
    """Modo inválido debe lanzar ValueError."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake")
    with pytest.raises(ValueError):
        reframe_clip(video, 0.0, 10.0, tmp_path / "out.mp4", mode="invalido")


def test_reframe_clip_ffmpeg_command(tmp_path):
    """reframe_clip debe construir el comando de ffmpeg correctamente (mock)."""
    video = tmp_path / "video.mp4"
    video.write_bytes(b"fake video")
    out = tmp_path / "out" / "vertical.mp4"

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
            if self.frame_idx >= 30:
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

    fake_detection = [(100, 100, 200, 250, 0.9)]

    with patch("cv2.VideoCapture", return_value=FakeCap()), \
         patch("subprocess.Popen", side_effect=lambda cmd, **kw: FakeProcess(cmd, **kw)), \
         patch("app.pipeline.reframe.detect_trajectory", return_value=[]), \
         patch("app.pipeline.reframe.smooth_trajectory", return_value=[
             CropKeyframe(t=0.0, x=0, y=0, w=900, h=1600),
         ]), \
         patch("app.pipeline.reframe._init_face_detection") as mock_det, \
         patch("app.pipeline.reframe._init_face_mesh") as mock_mesh:
        mock_det.return_value.process.return_value.detections = None
        mock_mesh.return_value.process.return_value.multi_face_landmarks = None

        result = reframe_clip(video, 0.0, 1.0, out, mode=MODE_SINGLE)

    assert result == out
    assert len(captured_cmds) >= 1
    cmd = captured_cmds[0]
    assert cmd[0] == "ffmpeg"
    assert str(out) in cmd


def test_available_modes():
    """Los modos disponibles deben ser single, auto, split."""
    assert MODE_SINGLE == "single"
    assert MODE_AUTO == "auto"
    assert MODE_SPLIT == "split"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
