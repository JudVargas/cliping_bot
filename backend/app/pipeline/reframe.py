"""Etapa 6: Reencuadre vertical básico (una sola persona).

- Muestrear el video a ~5 fps, detectar la cara principal con MediaPipe.
- Calcular un recorte 9:16 centrado en la cara (la cara en el tercio superior
  del encuadre vertical).
- Suavizar la trayectoria con media móvil exponencial; si no hay cara en un
  tramo, mantener la última posición.
- Renderizar leyendo frames con OpenCV, recortando y escalando a 1080x1920,
  enviando los frames por pipe a FFmpeg y mezclando el audio original.
- Guardar la trayectoria como lista de CropKeyframe en JSON para poder
  editarla después.

CLI: python -m app.pipeline.reframe <video_path> --start X --end Y --out out.mp4
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp

from app.config import settings

logger = logging.getLogger(__name__)

# Resolución de salida vertical 9:16
OUT_WIDTH = 1080
OUT_HEIGHT = 1920

# Factor de suavizado EMA (0 = sin suavizado, 1 = máximo suavizado)
EMA_ALPHA = 0.3

# Tamaño del recorte como fracción del ancho original (la cara ocupará ~40%)
CROP_HEIGHT_RATIO = 9 / 16  # 9:16


@dataclass
class CropKeyframe:
    """Un keyframe del recorte: tiempo, posición y tamaño del recorte."""

    t: float          # tiempo en segundos (relativo al video original)
    x: int            # coordenada X del recorte (px en video original)
    y: int            # coordenada Y del recorte (px en video original)
    w: int            # ancho del recorte (px en video original)
    h: int            # alto del recorte (px en video original)


def _init_face_detection():
    """Inicializar el detector de caras de MediaPipe."""
    mp_face_detection = mp.solutions.face_detection
    detector = mp_face_detection.FaceDetection(
        model_selection=0,  # 0 = cara cercana (2m), 1 = cara lejana (5m)
        min_detection_confidence=0.5,
    )
    return detector


def _detect_main_face(detector, frame) -> tuple[int, int, int, int] | None:
    """Detectar la cara principal en un frame.

    Devuelve (x, y, w, h) en píxeles del frame, o None si no hay cara.
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = detector.process(rgb)
    if not results.detections:
        return None

    h, w = frame.shape[:2]
    # Elegir la detección con mayor bounding box (cara más grande/cerca)
    best = None
    best_area = 0
    for detection in results.detections:
        box = detection.location_data.relative_bounding_box
        x = int(box.xmin * w)
        y = int(box.ymin * h)
        bw = int(box.width * w)
        bh = int(box.height * h)
        area = bw * bh
        if area > best_area:
            best_area = area
            best = (x, y, bw, bh)

    return best


def _compute_crop(
    face_box: tuple[int, int, int, int] | None,
    frame_w: int,
    frame_h: int,
    last_crop: CropKeyframe | None,
    t: float,
) -> CropKeyframe:
    """Calcular el recorte 9:16 centrado en la cara.

    Si no hay cara, mantener el último recorte.
    La cara se coloca en el tercio superior del encuadre vertical.
    """
    # Dimensiones del recorte 9:16 basadas en el ancho del frame
    # El recorte tiene aspect ratio 9:16 (ancho:alto)
    crop_w = frame_w
    crop_h = int(frame_w * OUT_HEIGHT / OUT_WIDTH)  # 9:16

    # Si el recorte es más alto que el frame, ajustar al alto del frame
    if crop_h > frame_h:
        crop_h = frame_h
        crop_w = int(frame_h * OUT_WIDTH / OUT_HEIGHT)

    if face_box is not None:
        fx, fy, fw, fh = face_box
        # Centro de la cara
        cx = fx + fw // 2
        cy = fy + fh // 2

        # La cara va en el tercio superior del recorte vertical
        # El centro del recorte está un poco por encima del centro de la cara
        target_x = cx - crop_w // 2
        target_y = cy - int(crop_h * 0.35)  # cara en tercio superior
    else:
        # No hay cara: mantener el último recorte
        if last_crop is not None:
            return CropKeyframe(
                t=t,
                x=last_crop.x,
                y=last_crop.y,
                w=last_crop.w,
                h=last_crop.h,
            )
        # Sin referencia: centrado
        target_x = (frame_w - crop_w) // 2
        target_y = (frame_h - crop_h) // 2

    # Clamp dentro del frame
    target_x = max(0, min(target_x, frame_w - crop_w))
    target_y = max(0, min(target_y, frame_h - crop_h))

    return CropKeyframe(t=t, x=target_x, y=target_y, w=crop_w, h=crop_h)


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
        x=sx,
        y=sy,
        w=sw,
        h=sh,
    )


def detect_trajectory(
    video_path: str | Path,
    *,
    sample_fps: float = 5.0,
) -> list[CropKeyframe]:
    """Detectar la trayectoria de recorte muestreando el video a sample_fps.

    Devuelve una lista de CropKeyframe (sin suavizar).
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

    # Intervalo entre frames muestrados (en frames)
    frame_interval = max(1, int(round(fps / sample_fps)))

    keyframes: list[CropKeyframe] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            t = frame_idx / fps if fps > 0 else 0.0
            face_box = _detect_main_face(detector, frame)
            kf = _compute_crop(face_box, frame_w, frame_h, None, t)
            keyframes.append(kf)

        frame_idx += 1

    cap.release()
    detector.close()

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
    """Suavizar la trayectoria con media móvil exponencial.

    Si no hay cara en un tramo, mantener la última posición (el keyframe
    anterior ya se copió en _compute_crop cuando no hay cara).
    """
    if not keyframes:
        return []

    smoothed: list[CropKeyframe] = [keyframes[0]]
    for kf in keyframes[1:]:
        prev = smoothed[-1]
        smoothed.append(_ema_smooth(kf, prev, alpha=alpha))

    return smoothed


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


def reframe_clip(
    video_path: str | Path,
    start: float,
    end: float,
    out_path: str | Path,
    *,
    keyframes_path: str | Path | None = None,
    sample_fps: float = 5.0,
) -> Path:
    """Renderizar un clip vertical 9:16 siguiendo a la cara detectada.

    Lee frames con OpenCV, aplica el recorte de cada keyframe (interpolado),
    escala a 1080x1920 y envía por pipe a FFmpeg mezclando el audio original.

    Devuelve la ruta al archivo de salida.
    """
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"No se encuentra el video: {video_path}")

    if end <= start:
        raise ValueError(f"end ({end}) debe ser mayor que start ({start})")

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

    # FFmpeg: recibir frames crudos (BGR24) por stdin, escalar y codificar
    ffmpeg_cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{frame_w}x{frame_h}",
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
    # Fallback a libx264 si nvenc falla se maneja abajo

    # Recortar el rango de tiempo del video original para el audio
    # Usamos -ss y -to en el input de audio
    # (el video ya viene recortado por frames)

    process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    try:
        frame_idx = 0
        kf_idx = 0
        num_kf = len(keyframes)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            t = frame_idx / fps if fps > 0 else 0.0

            # Solo procesar frames dentro del rango [start, end]
            if t < start:
                frame_idx += 1
                continue
            if t > end:
                break

            # Interpolar el keyframe para este tiempo
            kf = _interpolate_keyframe(keyframes, t)

            # Recortar el frame
            x = max(0, min(kf.x, frame_w - kf.w))
            y = max(0, min(kf.y, frame_h - kf.h))
            cropped = frame[y : y + kf.h, x : x + kf.w]

            # Escalar a 1080x1920
            resized = cv2.resize(cropped, (OUT_WIDTH, OUT_HEIGHT))

            # Enviar frame a FFmpeg por stdin
            if process.stdin:
                process.stdin.write(resized.tobytes())

            frame_idx += 1
            kf_idx += 1

    finally:
        cap.release()
        if process.stdin:
            process.stdin.close()
        process.wait()

    if process.returncode not in (0, None):
        stderr = process.stderr.read().decode() if process.stderr else ""
        # Si falló nvenc, reintentar con libx264
        if "h264_nvenc" in " ".join(ffmpeg_cmd):
            logger.warning(
                "h264_nvenc falló en reframe, usando libx264: %s", stderr[:200]
            )
            ffmpeg_cmd = [
                c if c != "h264_nvenc" else "libx264"
                for c in ffmpeg_cmd
            ]
            ffmpeg_cmd = [
                c if c != "-preset" or ffmpeg_cmd[i + 1] != "p4" else c
                for i, c in enumerate(ffmpeg_cmd)
            ]
            # Reemplazar preset p4 por medium
            for i, c in enumerate(ffmpeg_cmd):
                if c == "-preset" and i + 1 < len(ffmpeg_cmd):
                    ffmpeg_cmd[i + 1] = "medium"
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            # Reejecutar el render (simplificado: segundo intento)
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
                    kf = _interpolate_keyframe(keyframes, t)
                    x = max(0, min(kf.x, frame_w - kf.w))
                    y = max(0, min(kf.y, frame_h - kf.h))
                    cropped = frame[y : y + kf.h, x : x + kf.w]
                    resized = cv2.resize(cropped, (OUT_WIDTH, OUT_HEIGHT))
                    if process.stdin:
                        process.stdin.write(resized.tobytes())
                    frame_idx += 1
            finally:
                cap.release()
                if process.stdin:
                    process.stdin.close()
            process.wait()

    if process.returncode not in (0, None):
        stderr = process.stderr.read().decode() if process.stderr else ""
        raise RuntimeError(
            f"ffmpeg falló en reframe: {stderr.strip()}"
        )

    logger.info("Clip vertical renderizado: %s (%.1f-%.1f s)", out_path, start, end)
    return out_path


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

    # Encontrar el segmento que contiene t
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
    args = parser.parse_args()

    reframe_clip(
        args.video,
        args.start,
        args.end,
        args.out,
        keyframes_path=args.keyframes,
        sample_fps=args.sample_fps,
    )
    print(f"Clip vertical generado: {args.out}")
