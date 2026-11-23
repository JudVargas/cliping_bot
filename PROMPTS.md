# Prompts por etapas para opencode

## Cómo usarlos
1. Crea la carpeta del proyecto, copia `AGENTS.md` en la raíz y ejecuta `git init`.
2. Abre opencode en esa carpeta. Opencode lee `AGENTS.md` automáticamente como contexto.
3. Usa **una sesión nueva por etapa** (así el modelo no se llena de contexto y rinde mejor, sobre todo los gratuitos).
4. En cada etapa: primero modo **Plan** (tecla Tab para cambiar de agente) para revisar el plan, luego modo **Build**.
5. Haz commit al terminar cada etapa. No pases a la siguiente si la prueba de aceptación falla.
6. Si el modelo se pierde, pídele: "Detente. Resume qué has hecho y qué falló, sin cambiar código."

---

## Etapa 0: Esqueleto del proyecto
```
Lee AGENTS.md. Crea el esqueleto del proyecto ClipForge tal como describe la
estructura de carpetas, pero solo con archivos vacíos o con docstrings, sin
lógica todavía. Incluye:
- pyproject.toml (o requirements.txt) con fastapi, uvicorn, pydantic-settings,
  sqlmodel, openai, faster-whisper, opencv-python, mediapipe, pytest
- .env.example con LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, WHISPER_MODEL=medium,
  WHISPER_COMPUTE=int8_float16, DATA_DIR=./data
- config.py que lea ese .env
- .gitignore (data/, .env, __pycache__, node_modules)
- Un script `scripts/check_env.py` que verifique: ffmpeg y ffprobe instalados,
  si ffmpeg tiene el encoder h264_nvenc, si CUDA está disponible y cuánta VRAM hay.
Muéstrame primero el plan y espera mi OK.
Criterio de aceptación: `python scripts/check_env.py` imprime un resumen claro.
```

## Etapa 1: Ingesta y transcripción
```
Implementa pipeline/ingest.py y pipeline/transcribe.py.
- ingest: con ffprobe obtener duración, resolución y fps; extraer audio a
  wav 16 kHz mono en data/<video_id>/audio.wav.
- transcribe: usar faster-whisper en GPU con word_timestamps=True y vad_filter=True.
  Leer modelo y compute_type de config. Si int8_float16 falla, reintentar con int8
  y avisar en el log. Guardar data/<video_id>/transcript.json con el modelo
  Transcript descrito en AGENTS.md. Mostrar barra de progreso.
- Ambos deben funcionar por CLI: python -m app.pipeline.transcribe video.mp4
- Si ya existe transcript.json, no recalcular salvo flag --force.
Incluye un test con un video corto de fixtures.
Criterio de aceptación: transcribir un video de 2 minutos en español genera un
JSON con palabras y tiempos coherentes.
```

## Etapa 2: Selección de momentos con LLM
```
Implementa llm/client.py, llm/prompts.py y pipeline/moments.py.
- client.py: wrapper del SDK openai con base_url configurable, reintentos con
  backoff, y una función que pida JSON y lo valide con pydantic (reintenta si
  el JSON es inválido).
- prompts.py: prompt en español que reciba un fragmento de transcripción con
  timestamps y devuelva una lista JSON de clips con: start, end, title, reason,
  score (0-10). Reglas: duración entre 20 y 60 s, deben entenderse sin contexto,
  empezar y terminar en frases completas, preferir historias, remates, ideas
  fuertes y opiniones claras.
- moments.py: dividir la transcripción en ventanas de ~8-10 min con solape de
  60 s, llamar al LLM por ventana, unir resultados, eliminar duplicados por
  solape (IoU de tiempo), y ajustar start/end al límite de palabra/frase más
  cercano usando los timestamps. Guardar moments.json ordenado por score.
- CLI: python -m app.pipeline.moments <video_id> --top 10
Criterio de aceptación: sobre un podcast de 20+ minutos devuelve 5-10 momentos
razonables sin cortes a mitad de frase.
```

## Etapa 3: Cortar y exportar (todavía horizontal)
```
Implementa pipeline/render.py versión mínima.
- Función render_clip(video_path, start, end, out_path) con FFmpeg:
  h264_nvenc si está disponible, si no libx264, audio aac, sin shell=True.
- CLI que lea moments.json y exporte todos los clips a data/<video_id>/clips/.
- Cada clip debe tener el corte exacto (usar -ss/-to con reencodeo, no copy).
Criterio de aceptación: los clips se reproducen bien, empiezan y terminan donde
dice moments.json y el audio queda sincronizado.
```

## Etapa 4: Subtítulos
```
Implementa pipeline/captions.py.
- Generar un archivo .ass por clip a partir de las palabras del transcript
  dentro del rango del clip (tiempos relativos al inicio del clip).
- Resolución de referencia 1080x1920, fuente grande y legible, borde negro,
  posición en el tercio inferior-central.
- 3 a 5 palabras por línea; la palabra activa se resalta con otro color
  (usar tags \k o eventos por palabra).
- Crear 3 estilos predefinidos seleccionables por nombre (por ejemplo:
  "clasico", "resaltado", "minimal") definidos en un dict fácil de ampliar.
- Integrar en render.py: opción --captions <estilo> que quema el .ass con el
  filtro `ass` de FFmpeg (cuidado con el escapado de rutas en Windows).
Criterio de aceptación: el clip exportado muestra subtítulos sincronizados con
la voz y la palabra activa cambia de color.
```

## Etapa 5: Quitar silencios y muletillas
```
Implementa pipeline/silence.py.
- A partir de las palabras del clip, construir una lista de tramos a conservar
  (EditDecision.keep): eliminar pausas mayores a 0.6 s (dejar 0.15 s de respiro)
  y muletillas configurables ("eh", "em", "mmm", "este", "o sea" solo si
  aislada) cuando Whisper las haya transcrito.
- Complementar con `silencedetect` de FFmpeg para pausas que no aparezcan
  como palabras.
- No cortar risas ni énfasis: si hay un pico de energía en una pausa, conservarla.
- Integrar en render.py: concatenar los tramos con select/aselect o con
  trim+concat, con un fundido de audio de 10-20 ms en cada unión para evitar clics.
- Los subtítulos deben recalcular sus tiempos según los tramos conservados.
Criterio de aceptación: un clip con muchas pausas queda notablemente más
dinámico, sin cortes bruscos de audio y con subtítulos aún sincronizados.
```

## Etapa 6: Reencuadre vertical básico
```
Implementa pipeline/reframe.py versión 1 (una sola persona).
- Muestrear el video a ~5 fps, detectar la cara principal con MediaPipe.
- Calcular un recorte 9:16 centrado en la cara (la cara en el tercio superior
  del encuadre vertical).
- Suavizar la trayectoria con media móvil exponencial; si no hay cara en un
  tramo, mantener la última posición.
- Renderizar leyendo frames con OpenCV, recortando y escalando a 1080x1920,
  enviando los frames por pipe a FFmpeg y mezclando el audio original.
- Guardar la trayectoria como lista de CropKeyframe en JSON para poder
  editarla después.
Criterio de aceptación: un clip de una persona hablando a cámara sale vertical,
con la cara bien encuadrada y sin temblores.
```

## Etapa 7: Seguir a quien habla (dos o más personas)
```
Mejora reframe.py a versión 2.
- Detectar todas las caras por frame y seguirlas entre frames con un tracker
  simple (IoU o centroide) para darles un id estable.
- Determinar quién habla combinando: (a) apertura de la boca con MediaPipe
  Face Mesh, y (b) actividad de voz (silero-vad) sobre el audio.
- Cambiar de persona solo si la nueva lleva hablando más de ~0.8 s, y hacer
  un movimiento de cámara suave (no un corte seco), salvo que prefiera corte.
- Si dos personas hablan casi a la vez, modo pantalla dividida (una arriba y
  otra abajo).
- Exponer una opción para forzar un modo: single, auto, split.
Criterio de aceptación: en una entrevista de dos personas, el encuadre cambia
al hablante correcto con transiciones suaves y sin parpadeo.
```

## Etapa 8: API y cola de trabajos
```
Implementa app/main.py, db.py, models.py y jobs.py.
Endpoints:
- POST /videos (subir archivo) -> crea video y lanza pipeline en segundo plano
- GET /videos, GET /videos/{id}
- GET /videos/{id}/moments, PATCH /moments/{id} (editar start, end, title)
- POST /moments/{id}/render (opciones: estilo de subtítulos, modo de encuadre,
  quitar silencios sí/no)
- GET /clips/{id}/download
- GET /jobs/{id} con estado y progreso (SSE o polling)
Estados del video: uploaded, transcribing, finding_moments, ready, error.
Un solo worker a la vez (la GPU tiene 6 GB). Reanudar desde la última etapa
completada si el proceso se reinicia.
Criterio de aceptación: subir un video con curl y obtener clips descargables
solo usando la API.
```

## Etapa 9: Interfaz web
```
Crea el frontend en /frontend con React + Vite + TypeScript.
Pantallas:
1. Subir video (arrastrar y soltar) con barra de progreso del procesamiento.
2. Lista de momentos: título, duración, score, botón de previsualizar.
3. Editor de clip: reproductor, controles para ajustar inicio/fin (con la
   transcripción al lado para elegir por palabras), selector de estilo de
   subtítulos, modo de encuadre, interruptor de quitar silencios.
4. Botón "Exportar" y descarga del clip final.
Diseño simple y limpio, modo oscuro. Primero propón la estructura de componentes
y espera mi OK.
Criterio de aceptación: flujo completo desde la web, sin tocar la terminal.
```

## Etapa 10: Extras (opcionales, una por sesión)
```
- Exportar SRT del video completo y por hablante.
- Pedir un tema en texto libre ("clips donde hablen de dinero") y que el LLM
  arme el clip buscando en la transcripción.
- Título sobreimpreso en los primeros segundos del clip.
- Logo / marca de agua configurable.
- Modo LLM local con Ollama (modelo de 7B cuantizado) como alternativa sin internet.
```

Usa los skills ui-responsive, ui-futurista y ui-componentes-clipforge.
Primero propón la estructura de componentes y espera mi OK. 


---

## Prompt de rescate (cuando el modelo se atasca)
```
Detente. No cambies más código. Resume en 5 líneas: qué intentabas, qué falló
exactamente (mensaje de error), y qué hipótesis tienes. Después propón UNA sola
corrección mínima y espera mi aprobación.
```

## Consejos para modelos gratuitos
- Pide cambios pequeños y verificables; si el prompt es largo, divídelo.
- Pega siempre el error completo, no un resumen.
- Si un modelo no entiende MediaPipe o FFmpeg, ponle la documentación oficial como contexto antes de pedir el código.
- Para las etapas 6 y 7 (encuadre) usa el mejor modelo disponible; son las más difíciles.
