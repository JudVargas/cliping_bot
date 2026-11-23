# ClipForge: generador local de clips verticales con IA (uso personal)

## Objetivo
Aplicación local que convierte un video largo (podcast, entrevista, stream, clase) en clips cortos verticales 9:16 listos para TikTok / Reels / Shorts:

1. Transcribe el audio con timestamps por palabra.
2. Un LLM elige los mejores momentos (frases completas, se entienden solos, 20-60 s).
3. Corta cada clip, quita silencios y muletillas.
4. Reencuadra a vertical siguiendo a quien habla.
5. Quema subtítulos estilizados (palabra resaltada).
6. Permite revisar y editar inicio/fin de cada clip antes de exportar.

Uso estrictamente personal y local. No copiar código, textos ni branding de ningún servicio comercial.

## Entorno de desarrollo
- CPU: Ryzen 5 3600 (6 núcleos / 12 hilos)
- RAM: 32 GB
- GPU: NVIDIA GTX 1660 Ti, 6 GB VRAM (sin tensor cores; NVENC disponible)
- Pensar siempre en el límite de 6 GB de VRAM: nunca cargar dos modelos de GPU a la vez.
- El código debe funcionar en Windows y Linux: usar `pathlib`, nunca rutas con `/` o `\` escritas a mano.

## Stack
- Python 3.11+, gestionado con `uv` o `venv` + `requirements.txt`
- Backend: FastAPI + Uvicorn, SQLite (SQLModel o SQLAlchemy), cola de trabajos simple en proceso (sin Redis/Celery)
- Transcripción: `faster-whisper` en GPU. Probar `compute_type="int8_float16"` y si falla caer a `"int8"`. Modelo por defecto `medium`, configurable (`large-v3` en int8 si cabe).
- Video: FFmpeg (llamado por `subprocess`), codificación `h264_nvenc` con fallback a `libx264`.
- Visión: MediaPipe (face detection / face mesh) y OpenCV.
- Diarización/VAD opcional: `silero-vad` primero; `pyannote` solo si hace falta.
- LLM: cliente compatible con OpenAI (`openai` SDK con `base_url` configurable) para poder usar Gemini, OpenRouter u Ollama sin cambiar código.
- Frontend: React + Vite + TypeScript (se hace al final).

## Estructura de carpetas
```
clipforge/
  AGENTS.md
  PROMPTS.md
  .env.example
  pyproject.toml
  backend/
    app/
      main.py            # FastAPI
      config.py          # lee .env (pydantic-settings)
      db.py, models.py   # SQLite
      jobs.py            # cola de trabajos y estados
      pipeline/
        ingest.py        # ffprobe, extraer audio wav 16k mono
        transcribe.py    # faster-whisper -> palabras con timestamps
        moments.py       # LLM -> lista de clips candidatos
        silence.py       # EDL: quitar silencios y muletillas
        reframe.py       # detección de caras + recorte 9:16
        captions.py      # genera .ass
        render.py        # ensambla con FFmpeg
      llm/
        client.py        # wrapper OpenAI-compatible, reintentos, validación JSON
        prompts.py       # prompts del LLM (en español)
    tests/
  data/                  # videos, audio, transcripciones, clips (ignorado por git)
  frontend/              # React (etapa final)
```

## Modelos de datos (contratos entre módulos)
```python
class Word:      text: str; start: float; end: float; prob: float
class Transcript: language: str; words: list[Word]; segments: list[Segment]
class Moment:    id: int; start: float; end: float; title: str; reason: str; score: float
class EditDecision: keep: list[tuple[float, float]]   # tramos a conservar
class CropKeyframe: t: float; x: int; y: int; w: int; h: int
```
Todo tiempo está en segundos (float) relativo al video original. Cada etapa guarda su resultado en `data/<video_id>/` como JSON para poder reanudar sin recalcular.

## Reglas de trabajo para el agente
1. Trabajar **una etapa a la vez**, tal como pide el usuario en cada prompt. No adelantar etapas ni agregar funciones no pedidas.
2. Cada módulo debe poder ejecutarse solo desde CLI (`python -m app.pipeline.transcribe video.mp4`) para probarlo sin la API.
3. Antes de escribir código en una etapa nueva, proponer un plan corto (archivos a crear/modificar). Esperar aprobación si el cambio toca más de 3 archivos.
4. Escribir al menos un test pequeño por módulo, usando un video de prueba corto (30-60 s) en `backend/tests/fixtures/`.
5. Tipado con type hints, funciones pequeñas, `logging` en lugar de `print`.
6. Nunca llamar a FFmpeg con `shell=True`; pasar la lista de argumentos y validar rutas.
7. Manejo de errores explícito: si falla NVENC, caer a CPU y avisar en el log.
8. Configuración (claves API, modelo, idioma) siempre en `.env`, nunca en el código. Mantener `.env.example` actualizado.
9. No instalar dependencias pesadas sin avisar (torch, pyannote). Preferir lo ya listado en el stack.
10. Al terminar cada etapa: resumir qué se hizo, cómo probarlo y qué queda pendiente. Hacer commit con mensaje claro.

## Decisiones de diseño importantes
- **Selección de momentos:** dividir la transcripción en ventanas (~8-10 min con solape de 60 s), pedir al LLM JSON estricto, validar con un esquema, deduplicar solapes y ajustar inicio/fin a límites de frase usando los timestamps de palabras.
- **Idioma:** la interfaz y los prompts del LLM en español; detectar idioma del audio automáticamente.
- **Encuadre:** muestrear ~5 fps para detectar caras, suavizar el recorte (media móvil exponencial), mantener el recorte unos segundos antes de cambiar de persona, evitar saltos bruscos. Si dos personas hablan a la vez, usar pantalla dividida (arriba/abajo).
- **Subtítulos:** archivo `.ass` con palabra activa resaltada, 3-5 palabras por línea, resolución 1080x1920, fuente con licencia libre.
- **Render:** una sola pasada de FFmpeg por clip cuando sea posible; el recorte dinámico puede hacerse leyendo frames con OpenCV y enviándolos por pipe a FFmpeg, mezclando el audio original aparte.
- **Rendimiento:** procesar un video de 1 h en menos de ~20 min en el equipo descrito.
