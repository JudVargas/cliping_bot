"""Verificación del entorno de desarrollo ClipForge.

Comprueba:
- ffmpeg y ffprobe instalados y accesibles.
- Si ffmpeg incluye el encoder h264_nvenc (GPU NVIDIA).
- Disponibilidad de CUDA y VRAM de la GPU.

Uso:
    python scripts/check_env.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional


def _run(cmd: list[str]) -> Optional[str]:
    """Ejecuta un comando y devuelve su stdout, o None si falla."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        return None
    return None


def check_ffmpeg() -> tuple[bool, str]:
    """Verifica que ffmpeg y ffprobe estén instalados."""
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg:
        return False, "ffmpeg no encontrado en el PATH"
    if not ffprobe:
        return False, "ffprobe no encontrado en el PATH"
    version = _run(["ffmpeg", "-version"])
    line = version.splitlines()[0] if version else "desconocida"
    return True, f"ffmpeg OK ({line}) | ffprobe OK"


def check_nvenc() -> tuple[bool, str]:
    """Verifica si ffmpeg tiene el encoder h264_nvenc."""
    encoders = _run(["ffmpeg", "-encoders"])
    if encoders is None:
        return False, "No se pudo listar encoders de ffmpeg"
    if "h264_nvenc" in encoders:
        return True, "Encoder h264_nvenc DISPONIBLE (GPU NVIDIA)"
    return False, "Encoder h264_nvenc NO disponible (se usará libx264 en CPU)"


def check_cuda() -> tuple[bool, str]:
    """Verifica disponibilidad de CUDA y VRAM de la GPU."""
    # Intento 1: nvidia-smi (ligero, no requiere torch)
    smi = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    if smi:
        line = smi.strip().splitlines()[0] if smi.strip() else ""
        return True, f"CUDA disponible vía nvidia-smi: {line.strip()} MiB"
    # Intento 2: torch si está instalado (opcional)
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram_mib = props.total_memory // (1024 * 1024)
            return True, f"CUDA disponible vía torch: {props.name}, {vram_mib} MiB VRAM"
        return False, "torch instalado pero CUDA no disponible"
    except ImportError:
        pass
    return False, "No se pudo detectar CUDA (nvidia-smi/torch no disponibles)"


def main() -> int:
    print("=" * 60)
    print("  ClipForge - Verificación del entorno")
    print("=" * 60)

    checks: list[tuple[str, bool, str]] = []

    ok, msg = check_ffmpeg()
    checks.append(("ffmpeg / ffprobe", ok, msg))
    print(f"[{'OK ' if ok else 'FALLA'}] ffmpeg / ffprobe: {msg}")

    ok, msg = check_nvenc()
    checks.append(("h264_nvenc", ok, msg))
    print(f"[{'OK ' if ok else 'AVISO'}] NVENC: {msg}")

    ok, msg = check_cuda()
    checks.append(("CUDA / VRAM", ok, msg))
    print(f"[{'OK ' if ok else 'AVISO'}] CUDA: {msg}")

    print("-" * 60)
    fallos = [c for c in checks if not c[1]]
    if fallos:
        print(f"RESULTADO: {len(fallos)} problema(s) detectado(s).")
        for nombre, _, msg in fallos:
            print(f"  - {nombre}: {msg}")
        return 1
    print("RESULTADO: Entorno listo para ClipForge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
