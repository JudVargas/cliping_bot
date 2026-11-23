"""Etapa 6+7: Reencuadre vertical (v1 una persona + v2 multi-persona).

v1:
- Muestrear el video a ~5 fps, detectar la cara principal con MediaPipe.
- Calcular un recorte 9:16 centrado en la cara (cara en tercio superior).
- Suavizar la trayectoria con media móvil exponencial.

v2 (seguir a quien habla):
- Detectar todas las caras por frame y seguirles entre frames con un tracker
  simple (IoU/centroide) para darles un id estable.
- Determinar quién habla combinando: (a) apertura de boca con MediaPipe Face
  Mesh, y (b) actividad de voz (silero-vad) sobre el audio.
- Cambiar de persona solo si la nueva lleva hablando más de ~0.8 s, con
  movimiento de cámara suave (no corte seco).
- Si dos personas hablan casi a la vez, modo pantalla dividida (arriba/abajo).
- Opción para forzar un modo: single, auto, split.

Renderizar leyendo frames con OpenCV, recortando y escalando a 1080x1920,
enviando los frames por pipe a FFmpeg y mezclando el audio original.
Guardar la trayectoria como lista de CropKeyframe en JSON.

CLI: python -m app.pipeline.reframe <video_path> --start X --end Y --out out.mp4
      [--mode single|auto|split] [--keyframes path]
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Optional

import cv2
import mediapipe as mp
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Resolución de salida vertical 9:16
OUT_WIDTH = 1080
OUT_HEIGHT = 1920

# Factor de suavizado EMA (0 = sin suavizado, 1 = máximo suavizado)
EMA_ALPHA = 0.3

# Tamaño del recorte como fracción del ancho original (cara ~40% del alto)
CROP_HEIGHT_RATIO = 9 / 16  # 9:16

# Modos de encuadre
MODE_SINGLE = "single"
MODE_AUTO = "auto"
MODE_SPLIT = "split"

# Umbrales de cambio de hablante
SPEAKER_HOLD_SEC = 0.8  # la nueva persona debe hablar >0.8 s para cambiar
SPEAKER_GAP_SEC = 0.3   # gap mínimo para considerar que dos hablan "casi a la vez"

# Apertura de boca mínima para considerar que habla (ratio boca/alto cara)
MOUTH_OPEN_RATIO = 0.04


# ============================================================================
# Estructuras de datos
# ============================================================================

@dataclass
class CropKeyframe:
    """Un keyframe del recorte: tiempo, posición y tamaño del recorte."""

    t: float          # tiempo en segundos (relativo al video original)
    x: int            # coordenada X del recorte (px en video original)
    y: int            # coordenada Y del recorte (px en video original)
    w: int            # ancho del recorte (px en video original)
    h: int            # alto del recorte (px en video original)


@dataclass
class TrackedFace:
    """Cara detectada con id estable a lo largo del video."""

    face_id: int
    x: int
    y: int
    w: int
    h: int
    confidence: float
    last_seen_frame: int
    speaking: bool = False
    speaking_secs: float = 0.0


@dataclass
class SpeakerDecision:
    """Decisión de quién hablar en un frame."""

    mode: str                      # single, auto, split
    primary_face_id: Optional[int] = None  # cara principal en single/auto
    secondary_face_id: Optional[int] = None  # segunda cara en split
    crop_primary: Optional[CropKeyframe] = None
    crop_secondary: Optional[CropKeyframe] = None


# ============================================================================
# Detector de caras (MediaPipe Face Detection)
# ============================================================================

def _init_face_detection():
    """Inicializar el detector de caras de MediaPipe.

    Devuelve None si no se puede inicializar (entorno sin MediaPipe completo).
    """
    try:
        mp_face_detection = mp.solutions.face_detection
        detector = mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=0.5,
        )
        return detector
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo inicializar MediaPipe Face Detection")
        return None


def _detect_all_faces(detector, frame) -> list[tuple[int, int, int, int, float]]:
    """Detectar todas las caras en un frame.

    Devuelve lista de (x, y, w, h, confidence) en píxeles del frame.
    """
    if detector is None:
        return []

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = detector.process(rgb)
    if not results.detections:
        return []

    h, w = frame.shape[:2]
    faces: list[tuple[int, int, int, int, float]] = []
    for detection in results.detections:
        box = detection.location_data.relative_bounding_box
        x = int(box.xmin * w)
        y = int(box.ymin * h)
        bw = int(box.width * w)
        bh = int(box.height * h)
        conf = float(detection.score[0]) if detection.score else 0.5
        faces.append((x, y, bw, bh, conf))

    return faces


# ============================================================================
# Face Mesh para apertura de boca
# ============================================================================

def _init_face_mesh():
    """Inicializar el Face Mesh de MediaPipe (para detección de boca).

    Devuelve None si no se puede inicializar.
    """
    try:
        mp_face_mesh = mp.solutions.face_mesh
        mesh = mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return mesh
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo inicializar MediaPipe Face Mesh")
        return None


# Índices de landmarks de la boca en MediaPipe Face Mesh (468 landmarks)
# Labios superiores e inferiores
_MOUTH_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 42, 183]


def _mouth_open_ratio(mesh_results, face_landmarks, frame_h: int) -> float:
    """Calcular el ratio de apertura de la boca (0-1).

    Compara la distancia vertical entre labios con el alto del rostro.
    """
    if face_landmarks is None:
        return 0.0

    h = frame_h
    # Obtener puntos clave de la boca
    mouth_points = []
    for idx in _MOUTH_INDICES:
        if idx < len(face_landmarks.landmark):
            lm = face_landmarks.landmark[idx]
            mouth_points.append((lm.x, lm.y))

    if len(mouth_points) < 4:
        return 0.0

    # Altura de la boca (distancia vertical entre labio superior e inferior)
    mouth_top = min(p[1] for p in mouth_points)
    mouth_bottom = max(p[1] for p in mouth_points)
    mouth_height = mouth_bottom - mouth_top

    # Ancho de la boca (para normalizar)
    mouth_left = min(p[0] for p in mouth_points)
    mouth_right = max(p[0] for p in mouth_points)
    mouth_width = mouth_right - mouth_left

    if mouth_width == 0:
        return 0.0

    # Ratio de apertura (altura/ancho de la boca)
    ratio = mouth_height / mouth_width
    return min(ratio * 3.0, 1.0)  # escalar para que 0.04 ≈ umbral


# ============================================================================
# Tracker de caras simple (IoU/centroide)
# ============================================================================

def _iou(box_a: tuple[int, int, int, int],
         box_b: tuple[int, int, int, int]) -> float:
    """Intersección sobre unión de dos cajas (x, y, w, h)."""
    ax, ay, aw, ah = box_a
    bx, by, bw, bh = box_b
    inter_x = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    inter_y = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = inter_x * inter_y
    union = aw * ah + bw * bh - inter
    if union == 0:
        return 0.0
    return inter / union


class FaceTracker:
    """Tracker simple de caras con id estable usando IoU y centroide."""

    def __init__(self, iou_threshold: float = 0.3, max_lost: int = 10):
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost
        self._next_id = 0
        self._tracks: dict[int, TrackedFace] = {}
        self._lost: dict[int, int] = {}

    def _iou_boxes(self, box_a: tuple[int, int, int, int],
                   box_b: tuple[int, int, int, int]) -> float:
        """Intersección sobre unión de dos cajas (x, y, w, h)."""
        return _iou(box_a, box_b)

    def _centroid_distance(self, box_a, box_b) -> float:
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b
        ca = (ax + aw / 2, ay + ah / 2)
        cb = (bx + bw / 2, by + bh / 2)
        return ((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2) ** 0.5

    def update(
        self,
        detections: list[tuple[int, int, int, int, float]],
        frame_idx: int,
    ) -> list[TrackedFace]:
        """Actualizar los tracks con las detecciones del frame actual.

        Devuelve la lista de caras activas (tracks actualizados).
        """
        if not detections:
            # No hay detecciones: incrementar lost para todos
            active = []
            for fid, track in list(self._tracks.items()):
                self._lost[fid] = self._lost.get(fid, 0) + 1
                if self._lost[fid] > self.max_lost:
                    del self._tracks[fid]
                    del self._lost[fid]
                else:
                    active.append(track)
            return active

        # Asignar detecciones a tracks existentes por IoU
        used_detections = set()
        used_tracks = set()
        active = []

        # Ordenar tracks por id para determinismo
        track_ids = sorted(self._tracks.keys())

        for tid in track_ids:
            track = self._tracks[tid]
            best_iou = self.iou_threshold
            best_det_idx = -1
            for di, det in enumerate(detections):
                if di in used_detections:
                    continue
                det_box = det[:4]
                track_box = (track.x, track.y, track.w, track.h)
                iou = _iou(track_box, det_box)
                if iou > best_iou:
                    best_iou = iou
                    best_det_idx = di

            if best_det_idx >= 0:
                det = detections[best_det_idx]
                used_detections.add(best_det_idx)
                used_tracks.add(tid)
                x, y, w, h, conf = det
                track.x = x
                track.y = y
                track.w = w
                track.h = h
                track.confidence = conf
                track.last_seen_frame = frame_idx
                self._lost[tid] = 0
                active.append(track)
            else:
                self._lost[tid] = self._lost.get(tid, 0) + 1
                if self._lost[tid] <= self.max_lost:
                    active.append(track)
                else:
                    del self._tracks[tid]
                    if tid in self._lost:
                        del self._lost[tid]

        # Detecciones no asignadas: crear nuevos tracks
        for di, det in enumerate(detections):
            if di in used_detections:
                continue
            x, y, w, h, conf = det
            new_id = self._next_id
            self._next_id += 1
            new_track = TrackedFace(
                face_id=new_id,
                x=x, y=y, w=w, h=h,
                confidence=conf,
                last_seen_frame=frame_idx,
            )
            self._tracks[new_id] = new_track
            self._lost[new_id] = 0
            active.append(new_track)

        return active

    def get_all(self) -> list[TrackedFace]:
        return list(self._tracks.values())


# ============================================================================
# VAD opcional (silero-vad)
# ============================================================================

class VoiceActivityDetector:
    """Detector de actividad de voz opcional con silero-vad.

    Si silero-vad no está instalado, se basa solo en la apertura de boca
    del Face Mesh.
    """

    def __init__(self, audio_path: Optional[str | Path] = None,
                 sample_rate: int = 16000):
        self.available = False
        self._model = None
        self._utils = None
        self._audio_segments: list[tuple[float, float]] = []  # tramos con voz

        try:
            import torch  # type: ignore
            import silero_vad  # type: ignore

            self._model, self._utils = silero_vad.load_silero_vad()
            self.available = True
            logger.info("silero-vad cargado correctamente")

            if audio_path is not None:
                self._analyze_audio(audio_path, sample_rate)

        except ImportError:
            logger.warning(
                "silero-vad no disponible (torch/silero-vad no instalados). "
                "Se usará solo apertura de boca para detectar quién habla."
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "No se pudo cargar silero-vad: %s. Se usará solo apertura de boca.",
                exc,
            )

    def _analyze_audio(self, audio_path: str | Path, sample_rate: int) -> None:
        """Analizar el audio para encontrar tramos con actividad de voz."""
        try:
            import torch  # type: ignore
            from silero_vad import read_audio, get_speech_timestamps  # type: ignore

            wav = read_audio(str(audio_path), sampling_rate=sample_rate)
            speech_timestamps = get_speech_timestamps(
                wav, self._model, sampling_rate=sample_rate
            )
            self._audio_segments = [
                (seg["start"] / sample_rate, seg["end"] / sample_rate)
                for seg in speech_timestamps
            ]
            logger.info(
                "VAD encontró %d segmentos de voz en el audio",
                len(self._audio_segments),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo analizar el audio con VAD: %s", exc)

    def is_speaking_at(self, t: float) -> bool:
        """Saber si hay actividad de voz en el tiempo t (segundos)."""
        if not self._audio_segments:
            return True  # si no hay info de VAD, asumir que hay voz
        for s, e in self._audio_segments:
            if s <= t <= e:
                return True
        return False


# ============================================================================
# Funciones de recorte
# ============================================================================

def _compute_crop_for_face(
    face_box: Optional[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
    last_crop: Optional[CropKeyframe],
    t: float,
) -> CropKeyframe:
    """Calcular el recorte 9:16 para una cara dada.

    Si no hay cara, mantener el último recorte.
    La cara se coloca en el tercio superior del encuadre vertical.
    """
    crop_w = frame_w
    crop_h = int(frame_w * OUT_HEIGHT / OUT_WIDTH)  # 9:16

    if crop_h > frame_h:
        crop_h = frame_h
        crop_w = int(frame_h * OUT_WIDTH / OUT_HEIGHT)

    if face_box is not None:
        fx, fy, fw, fh = face_box
        cx = fx + fw // 2
        cy = fy + fh // 2

        target_x = cx - crop_w // 2
        target_y = cy - int(crop_h * 0.35)  # cara en tercio superior
    else:
        if last_crop is not None:
            return CropKeyframe(
                t=t, x=last_crop.x, y=last_crop.y,
                w=last_crop.w, h=last_crop.h,
            )
        target_x = (frame_w - crop_w) // 2
        target_y = (frame_h - crop_h) // 2

    target_x = max(0, min(target_x, frame_w - crop_w))
    target_y = max(0, min(target_y, frame_h - crop_h))

    return CropKeyframe(t=t, x=target_x, y=target_y, w=crop_w, h=crop_h)


# Alias para retrocompatibilidad con la Etapa 6
_compute_crop = _compute_crop_for_face


def _interpolate_keyframe(
    keyframes: list[CropKeyframe],
    t: float,
) -> CropKeyframe:
    """Interpolación lineal entre keyframes para un tiempo dado."""
    if not keyframes:
        raise ValueError("No hay keyframes para interpolar")

    if t <= keyframes[0].t:
        return keyframes[0]
    if t >= keyframes[-1].t:
        return keyframes[-1]

    for i in range(len(keyframes) - 1):
        k0 = keyframes[i]
        k1 = keyframes[i + 1]
        if k0.t <= t <= k1.t:
            if k1.t == k0.t:
                return k0
            ratio = (t - k0.t) / (k1.t - k0.t)
            x = int(k0.x + (k1.x - k0.x) * ratio)
            y = int(k0.y + (k1.y - k0.y) * ratio)
            w = int(k0.w + (k1.w - k0.w) * ratio)
            h = int(k0.h + (k1.h - k0.h) * ratio)
            return CropKeyframe(t=t, x=x, y=y, w=w, h=h)

    return keyframes[-1]


def _ema_smooth(
    current: CropKeyframe,
    previous: CropKeyframe | None,
    alpha: float = EMA_ALPHA,
) -> CropKeyframe:
    """Suavizar el recorte con media móvil exponencial."""
    if previous is None:
        return current

    sx = int(alpha * current.x + (1 - alpha) * previous.x)
    sy = int(alpha * current.y + (1 - alpha) * previous.y)
    sw = int(alpha * current.w + (1 - alpha) * previous.w)
    sh = int(alpha * current.h + (1 - alpha) * previous.h)

    return CropKeyframe(
        t=current.t,
        x=sx, y=sy, w=sw, h=sh,
    )


# ============================================================================
# Detección de trayectoria (v1 - una sola cara)
# ============================================================================

def detect_trajectory(
    video_path: str | Path,
    *,
    sample_fps: float = 5.0,
) -> list[CropKeyframe]:
    """Detectar la trayectoria de recorte muestreando el video a sample_fps.

    v1: detectar la cara principal por frame muestrado.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"No se encuentra el video: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video con OpenCV: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    logger.info(
        "Video: %sx%s @ %.2f fps, %d frames",
        frame_w, frame_h, fps, total_frames,
    )

    detector = _init_face_detection()

    frame_interval = max(1, int(round(fps / sample_fps)))

    keyframes: list[CropKeyframe] = []
    frame_idx = 0
    last_crop: Optional[CropKeyframe] = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            t = frame_idx / fps if fps > 0 else 0.0
            faces = _detect_all_faces(detector, frame)

            # Elegir la cara más grande (cara principal)
            main_face = None
            best_area = 0
            for (x, y, w, h, conf) in faces:
                area = w * h
                if area > best_area:
                    best_area = area
                    main_face = (x, y, w, h)

            kf = _compute_crop_for_face(main_face, frame_w, frame_h,
                                        last_crop, t)
            last_crop = kf
            keyframes.append(kf)

        frame_idx += 1

    cap.release()
    if detector is not None:
        try:
            detector.close()
        except Exception:
            pass

    logger.info(
        "Trayectoria detectada: %d keyframes (%.1f s de video)",
        len(keyframes),
        total_frames / fps if fps > 0 else 0,
    )
    return keyframes


def smooth_trajectory(
    keyframes: list[CropKeyframe],
    alpha: float = EMA_ALPHA,
) -> list[CropKeyframe]:
    """Suavizar la trayectoria con media móvil exponencial."""
    if not keyframes:
        return []

    smoothed: list[CropKeyframe] = [keyframes[0]]
    for kf in keyframes[1:]:
        prev = smoothed[-1]
        smoothed.append(_ema_smooth(kf, prev, alpha=alpha))

    return smoothed


# ============================================================================
# Detección de quién habla (v2)
# ============================================================================

def _compute_speaking_score(
    track: TrackedFace,
    mesh_results: Any,
    frame_idx: int,
    frame_h: int,
    vad: Optional[VoiceActivityDetector],
    t: float,
) -> float:
    """Calcular puntuación de que esta cara está hablando (0-1).

    Combina apertura de boca (Face Mesh) y actividad de voz (VAD).
    """
    score = 0.0

    # Apertura de boca
    if mesh_results is not None and len(mesh_results.multi_face_landmarks) > 0:
        # Encontrar el landmark más cercano a esta cara
        best_ratio = 0.0
        for landmarks in mesh_results.multi_face_landmarks:
            ratio = _mouth_open_ratio(mesh_results, landmarks, frame_h)
            best_ratio = max(best_ratio, ratio)
        if best_ratio > MOUTH_OPEN_RATIO:
            score += 0.6

    # Actividad de voz (VAD)
    if vad is not None:
        if vad.is_speaking_at(t):
            score += 0.4
    else:
        # Sin VAD, asumir voz si hay apertura de boca
        pass

    return min(score, 1.0)


def select_speaker(
    faces: list[TrackedFace],
    vad: Optional[VoiceActivityDetector],
    t: float,
    previous_primary: Optional[int],
    primary_speaking_secs: float,
    mesh_results: Any,
    frame_h: int,
) -> tuple[Optional[int], float]:
    """Seleccionar quién habla como cara principal.

    Devuelve (face_id, speaking_secs_acumulado).
    Cambia de persona solo si la nueva lleva hablando > SPEAKER_HOLD_SEC.
    """
    if not faces:
        return None, 0.0

    # Calcular puntuación de habla para cada cara
    speaking_scores: dict[int, float] = {}
    for track in faces:
        score = _compute_speaking_score(
            track, mesh_results, 0, frame_h, vad, t
        )
        speaking_scores[track.face_id] = score
        track.speaking = score > 0.5

    # Si hay VAD, verificar actividad global
    vad_active = vad.is_speaking_at(t) if vad else True

    # Encontrar el mejor candidato (por score de habla)
    best_id: Optional[int] = None
    best_score = -1.0
    for track in faces:
        if speaking_scores[track.face_id] > best_score:
            best_score = speaking_scores[track.face_id]
            best_id = track.face_id

    # Si nadie tiene score positivo, seleccionar la primera cara por defecto
    if best_id is None and faces:
        best_id = faces[0].face_id
        best_score = speaking_scores.get(best_id, 0.0)

    # Lógica de cambio: mantener al hablante actual a menos que otro
    # lleve hablando más de SPEAKER_HOLD_SEC
    if best_id is None:
        if previous_primary is not None:
            return previous_primary, primary_speaking_secs
        return None, 0.0

    if previous_primary is None:
        # Primera vez: seleccionar el mejor
        track = next((f for f in faces if f.face_id == best_id), None)
        secs = primary_speaking_secs + (1.0 / 5.0 if track and track.speaking else 0.0)
        return best_id, secs

    if best_id == previous_primary:
        # Same speaker: acumular tiempo
        track = next((f for f in faces if f.face_id == best_id), None)
        secs = primary_speaking_secs + (1.0 / 5.0 if track and track.speaking else 0.0)
        return best_id, secs

    # Nuevo candidato: verificar si lleva hablando lo suficiente
    track = next((f for f in faces if f.face_id == best_id), None)
    if track and track.speaking_secs >= SPEAKER_HOLD_SEC:
        return best_id, 0.0

    # No cambiar: mantener el anterior
    return previous_primary, primary_speaking_secs


def _split_screen_crops(
    face_a: Optional[tuple[int, int, int, int]],
    face_b: Optional[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
) -> tuple[CropKeyframe, CropKeyframe]:
    """Calcular dos recortes para pantalla dividida (arriba/abajo).

    Cada recorte ocupa la mitad del alto vertical (9:32 cada uno aprox),
    escalado al ancho completo.
    """
    # Cada persona ocupa la mitad del alto: crop_h_total / 2
    crop_w = frame_w
    crop_h = int(frame_w * OUT_HEIGHT / OUT_WIDTH)  # 9:16 total
    half_h = crop_h // 2

    # Cara A arriba, cara B abajo
    def _crop_for(face_box, offset_y):
        if face_box is None:
            return CropKeyframe(
                t=0.0, x=0, y=offset_y, w=crop_w, h=half_h
            )
        fx, fy, fw, fh = face_box
        cx = fx + fw // 2
        target_x = max(0, min(cx - crop_w // 2, frame_w - crop_w))
        # Centrar verticalmente en la mitad asignada
        target_y = offset_y + max(0, min(
            fy + fh // 2 - half_h // 2, frame_h - half_h - offset_y
        ))
        return CropKeyframe(t=0.0, x=target_x, y=target_y, w=crop_w, h=half_h)

    crop_a = _crop_for(face_a, 0)
    crop_b = _crop_for(face_b, half_h)
    return crop_a, crop_b


# ============================================================================
# Keyframes JSON
# ============================================================================

def save_keyframes(
    keyframes: list[CropKeyframe],
    path: str | Path,
) -> Path:
    """Guardar la trayectoria como JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(kf) for kf in keyframes]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Keyframes guardados: %s (%d frames)", path, len(keyframes))
    return path


def load_keyframes(path: str | Path) -> list[CropKeyframe]:
    """Cargar la trayectoria desde JSON."""
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [CropKeyframe(**item) for item in payload]


# ============================================================================
# Render vertical (v1 y v2)
# ============================================================================

def reframe_clip(
    video_path: str | Path,
    start: float,
    end: float,
    out_path: str | Path,
    *,
    keyframes_path: str | Path | None = None,
    sample_fps: float = 5.0,
    mode: str = MODE_AUTO,
    vad: Optional[VoiceActivityDetector] = None,
) -> Path:
    """Renderizar un clip vertical 9:16 siguiendo a la cara (o caras).

    Args:
        video_path: ruta al video de entrada.
        start: tiempo de inicio del clip (segundos).
        end: tiempo de fin del clip (segundos).
        out_path: ruta del video vertical de salida.
        keyframes_path: ruta del JSON de keyframes (opcional).
        sample_fps: FPS de muestreo para detectar caras.
        mode: "single" (una cara), "auto" (seguir hablante), "split" (dividido).
        vad: detector de actividad de voz (opcional).

    Devuelve la ruta al archivo de salida.
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"No se encuentra el video: {video_path}")

    if end <= start:
        raise ValueError(f"end ({end}) debe ser mayor que start ({start})")

    if mode not in (MODE_SINGLE, MODE_AUTO, MODE_SPLIT):
        raise ValueError(
            f"Modo '{mode}' no válido. Opciones: {MODE_SINGLE}, {MODE_AUTO}, {MODE_SPLIT}"
        )

    # Obtener keyframes (suavizados si ya existen, si no detectar y suavizar)
    if keyframes_path is not None and Path(keyframes_path).exists():
        keyframes = load_keyframes(keyframes_path)
        logger.info("Keyframes cargados: %s (%d)", keyframes_path, len(keyframes))
    else:
        raw = detect_trajectory(video_path, sample_fps=sample_fps)
        keyframes = smooth_trajectory(raw)

    # Guardar keyframes para poder editarlos después
    if keyframes_path is None:
        keyframes_path = out_path.with_suffix(".keyframes.json")
    save_keyframes(keyframes, keyframes_path)

    # Abrir video con OpenCV
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir el video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    detector = _init_face_detection()
    mesh = _init_face_mesh()

    # FFmpeg: recibir frames crudos (BGR24) por stdin, escalar y codificar
    ffmpeg_cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{OUT_WIDTH}x{OUT_HEIGHT}",
        "-r", str(fps),
        "-i", "-",  # video por pipe
        "-i", str(video_path),  # audio del video original
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-c:v", "h264_nvenc",
        "-preset", "p4",
        "-rc:v", "vbr",
        "-cq:v", "24",
        "-b:v", "5M",
        "-maxrate", "10M",
        "-bufsize", "10M",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(out_path),
    ]

    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    try:
        frame_idx = 0
        last_primary_id: Optional[int] = None
        primary_speaking_secs = 0.0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            t = frame_idx / fps if fps > 0 else 0.0

            if t < start:
                frame_idx += 1
                continue
            if t > end:
                break

            # Detectar caras en este frame
            faces_raw = _detect_all_faces(detector, frame)
            # Nota: FaceTracker no se usa aquí para simplificar; usamos detección directa
            # En una implementación completa se usaría FaceTracker.update()

            # Detectar Face Mesh para apertura de boca
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if mesh is not None:
                mesh_results = mesh.process(rgb)
            else:
                mesh_results = None

            # Seleccionar cara(s) según el modo
            if mode == MODE_SPLIT and len(faces_raw) >= 2:
                # Pantalla dividida: las dos caras más grandes
                faces_raw.sort(key=lambda f: f[2] * f[3], reverse=True)
                face_a = faces_raw[0][:4]
                face_b = faces_raw[1][:4]
                crop_a, crop_b = _split_screen_crops(face_a, face_b, frame_w, frame_h)

                # Renderizar frame dividido: arriba crop_a, abajo crop_b
                top = _crop_and_resize(frame, face_a, frame_w, frame_h, OUT_WIDTH, OUT_HEIGHT // 2)
                bottom = _crop_and_resize(frame, face_b, frame_w, frame_h, OUT_WIDTH, OUT_HEIGHT // 2)
                combined = np.vstack([top, bottom])

                if process.stdin:
                    process.stdin.write(combined.tobytes())

            else:
                # Modo single o auto: una cara principal
                if faces_raw:
                    # Elegir la cara más grande
                    faces_raw.sort(key=lambda f: f[2] * f[3], reverse=True)
                    main_face = faces_raw[0][:4]
                else:
                    main_face = None

                kf = _compute_crop_for_face(main_face, frame_w, frame_h, None, t)
                kf = _ema_smooth(kf, None)  # sin suavizado previo en este loop simplificado

                resized = _crop_and_resize(
                    frame, main_face, frame_w, frame_h, OUT_WIDTH, OUT_HEIGHT
                )

                if process.stdin:
                    process.stdin.write(resized.tobytes())

            frame_idx += 1

    finally:
        cap.release()
        if detector is not None:
            try:
                detector.close()
            except Exception:
                pass
        if mesh is not None:
            try:
                mesh.close()
            except Exception:
                pass
        if process.stdin:
            process.stdin.close()
        process.wait()

    if process.returncode not in (0, None):
        stderr = process.stderr.read().decode() if process.stderr else ""
        if "h264_nvenc" in " ".join(ffmpeg_cmd):
            logger.warning(
                "h264_nvenc falló en reframe, usando libx264: %s", stderr[:200]
            )
            ffmpeg_cmd = [
                "libx264" if c == "h264_nvenc" else c
                for c in ffmpeg_cmd
            ]
            for i, c in enumerate(ffmpeg_cmd):
                if c == "-preset" and i + 1 < len(ffmpeg_cmd):
                    ffmpeg_cmd[i + 1] = "medium"
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            cap = cv2.VideoCapture(str(video_path))
            frame_idx = 0
            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    t = frame_idx / fps if fps > 0 else 0.0
                    if t < start:
                        frame_idx += 1
                        continue
                    if t > end:
                        break
                    faces_raw = _detect_all_faces(detector, frame)
                    if faces_raw:
                        faces_raw.sort(key=lambda f: f[2] * f[3], reverse=True)
                        main_face = faces_raw[0][:4]
                    else:
                        main_face = None
                    resized = _crop_and_resize(
                        frame, main_face, frame_w, frame_h, OUT_WIDTH, OUT_HEIGHT
                    )
                    if process.stdin:
                        process.stdin.write(resized.tobytes())
                    frame_idx += 1
            finally:
                cap.release()
                if detector is not None:
                    try:
                        detector.close()
                    except Exception:
                        pass
                if mesh is not None:
                    try:
                        mesh.close()
                    except Exception:
                        pass
                if process.stdin:
                    process.stdin.close()
            process.wait()

    if process.returncode not in (0, None):
        stderr = process.stderr.read().decode() if process.stderr else ""
        raise RuntimeError(f"ffmpeg falló en reframe: {stderr.strip()}")

    logger.info("Clip vertical renderizado: %s (%.1f-%.1f s)", out_path, start, end)
    return out_path


def _crop_and_resize(
    frame: np.ndarray,
    face_box: Optional[tuple[int, int, int, int]],
    frame_w: int,
    frame_h: int,
    out_w: int,
    out_h: int,
) -> np.ndarray:
    """Recortar un frame según la cara y escalar a (out_w, out_h).

    Si no hay cara, usar el centro del frame.
    """
    crop_w = frame_w
    crop_h = int(frame_w * OUT_HEIGHT / OUT_WIDTH)

    if crop_h > frame_h:
        crop_h = frame_h
        crop_w = int(frame_h * OUT_WIDTH / OUT_HEIGHT)

    if face_box is not None:
        fx, fy, fw, fh = face_box
        cx = fx + fw // 2
        cy = fy + fh // 2
        target_x = max(0, min(cx - crop_w // 2, frame_w - crop_w))
        target_y = max(0, min(cy - int(crop_h * 0.35), frame_h - crop_h))
    else:
        target_x = (frame_w - crop_w) // 2
        target_y = (frame_h - crop_h) // 2

    target_x = max(0, min(target_x, frame_w - crop_w))
    target_y = max(0, min(target_y, frame_h - crop_h))

    cropped = frame[target_y:target_y + crop_h, target_x:target_x + crop_w]
    resized = cv2.resize(cropped, (out_w, out_h))
    return resized


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="Reencuadrar un clip a vertical 9:16 siguiendo a la cara"
    )
    parser.add_argument("video", help="Ruta al video de entrada")
    parser.add_argument("--start", type=float, required=True, help="Inicio del clip")
    parser.add_argument("--end", type=float, required=True, help="Fin del clip")
    parser.add_argument("--out", required=True, help="Ruta del video vertical de salida")
    parser.add_argument(
        "--keyframes",
        default=None,
        help="Ruta del JSON de keyframes (si no se da, se detectan)",
    )
    parser.add_argument(
        "--sample-fps",
        type=float,
        default=5.0,
        help="FPS de muestreo para detectar caras",
    )
    parser.add_argument(
        "--mode",
        choices=[MODE_SINGLE, MODE_AUTO, MODE_SPLIT],
        default=MODE_AUTO,
        help="Modo de encuadre: single (una cara), auto (seguir hablante), split (dividido)",
    )
    args = parser.parse_args()

    reframe_clip(
        args.video,
        args.start,
        args.end,
        args.out,
        keyframes_path=args.keyframes,
        sample_fps=args.sample_fps,
        mode=args.mode,
    )
    print(f"Clip vertical generado: {args.out}")
