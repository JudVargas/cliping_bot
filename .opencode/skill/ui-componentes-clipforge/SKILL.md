---
name: ui-componentes-clipforge
description: Arquitectura del frontend de ClipForge (React + Vite + TypeScript) con las pantallas, componentes y estados de la app (subida, progreso, lista de momentos, editor de clip, exportación) y cómo se adaptan a móvil y escritorio. Úsalo al crear o cambiar pantallas y componentes del producto.
---

# Pantallas y componentes de ClipForge

Combina este skill con `ui-responsive` (adaptación) y `ui-futurista` (estilo). Los tipos de datos vienen del backend (ver AGENTS.md): `Word`, `Moment`, `Transcript`.

## Stack del frontend
React 18 + Vite + TypeScript, Tailwind, React Router, **TanStack Query** (datos del servidor), Zustand (estado local del editor), `lucide-react`, `wavesurfer.js` con plugin Regions (forma de onda y selección de rango), `@tanstack/react-virtual` si hace falta.

## Estructura
```
frontend/src/
  app/            router, providers, layout (Shell, SideRail, BottomNav)
  features/
    upload/       UploadZone, UploadProgress
    videos/       VideoList, VideoCard, PipelineStages
    moments/      MomentList, MomentCard, ScoreRing
    editor/       ClipEditor, ClipFrame, Waveform, TranscriptPicker,
                  StylePanel, TrimControls, ExportBar
  components/ui/  Button, Input, Slider, Chip, Sheet, Tabs, Toast, Skeleton
  lib/            api.ts (fetch tipado), format.ts (tiempos), hooks
  styles/         tokens.css, base.css
```
Regla: `components/ui` no conoce el negocio; `features/*` sí. Los tipos de la API viven en `lib/types.ts` y reflejan los modelos del backend.

## Pantallas

### 1. Inicio / Videos (`/`)
- Arriba: zona de subida. Móvil: botón grande "Elegir video" (abre selector de archivos del sistema). Escritorio: además arrastrar y soltar.
- Debajo: lista de videos con estado (`transcribing`, `finding_moments`, `ready`, `error`) usando `PipelineStages`.
- Vacío: una frase y el botón de subir; sin ilustraciones recargadas.

### 2. Progreso de procesamiento
- `PipelineStages`: Subida, Transcripción, Búsqueda de momentos, Listo. Vertical en móvil, horizontal en `md+`.
- Muestra porcentaje y tiempo estimado cuando exista; permite cancelar.
- Error: mensaje claro, causa probable y botón "Reintentar esta etapa".

### 3. Momentos (`/videos/:id`)
- Lista ordenada por puntaje. El mejor ocupa más espacio. Cada `MomentCard` muestra: título, rango `mm:ss–mm:ss` (mono), duración, `ScoreRing`, motivo en una línea (con "ver más").
- Móvil: lista de una columna, tocar abre el editor a pantalla completa. Escritorio: lista a la izquierda y vista previa a la derecha.
- Acciones por tarjeta: Previsualizar, Editar, Exportar. Selección múltiple para exportar varios.

### 4. Editor de clip (`/clips/:id`)
Escritorio (≥ `xl`), 3 paneles:
```
| Transcripción (palabras clicables) | ClipFrame 9:16 + controles | Estilo y ajustes |
|                 Forma de onda con región arrastrable                   |
```
Móvil:
```
ClipFrame 9:16 (arriba, sticky)
Forma de onda + controles de recorte
Pestañas: Transcripción | Estilo | Exportar  (contenido en bottom sheet)
```
- **ClipFrame**: único elemento con brillo (ver `ui-futurista`). Reproduce el render de baja calidad o el original recortado con subtítulos superpuestos en HTML.
- **TrimControls**: arrastrar bordes de la región en la forma de onda, más botones ±0.1 s y ±1 s, y atajos de teclado (`←/→` mueven el cabezal, `[` y `]` fijan inicio/fin).
- **TranscriptPicker**: tocar una palabra mueve el cabezal; mantener y arrastrar selecciona un rango que se convierte en inicio/fin. Resalta la palabra activa con `ion`.
- **StylePanel**: estilo de subtítulos (miniaturas de los 3 estilos), modo de encuadre (Una persona / Automático / Pantalla dividida), interruptor "Quitar silencios y muletillas".
- **ExportBar**: botón "Exportar clip" fijo abajo en móvil; muestra el progreso y luego "Descargar".

### 5. Ajustes (`/ajustes`)
Modelo de Whisper, proveedor/modelo de LLM, estilo de subtítulos por defecto, carpeta de salida. Formulario de una columna, con guardado explícito.

## Datos y estado
- Todas las llamadas por `lib/api.ts` con rutas relativas `/api/...`. Cada endpoint tiene su hook de TanStack Query.
- Polling de jobs cada 2 s mientras `status` esté en curso; detener al terminar.
- Cambios del editor (inicio, fin, título) con actualización optimista y `PATCH /moments/{id}` con debounce de 600 ms.
- Estado local del editor en Zustand: `playhead`, `selection`, `style`, `reframeMode`, `removeSilence`.
- Formateo de tiempo en un solo lugar (`formatTime(seconds)` → `mm:ss.mmm`).

## Accesibilidad específica
- La línea de tiempo es un `role="slider"` con `aria-valuemin/max/now` y `aria-valuetext` legible ("12 segundos").
- Las hojas inferiores atrapan el foco, se cierran con `Esc` y devuelven el foco al disparador.
- Los estados de procesamiento se anuncian en una región `aria-live="polite"`.

## Orden de construcción sugerido
1. Tokens, fuentes y `components/ui` (Button, Input, Chip, Sheet, Skeleton).
2. Shell responsive (SideRail + BottomNav) con rutas vacías.
3. Subida + lista de videos + `PipelineStages` con datos simulados (mock) hasta conectar la API.
4. Lista de momentos.
5. Editor: primero `ClipFrame` + reproductor, luego forma de onda, luego transcripción, luego estilos y exportación.
6. Ajustes, PWA y pulido.
