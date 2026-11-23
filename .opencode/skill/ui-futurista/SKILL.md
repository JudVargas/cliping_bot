---
name: ui-futurista
description: Sistema de diseño futurista y profesional para ClipForge, con paleta oscura de tinta azul con violeta, cian y magenta, tokens CSS/Tailwind, tipografía, superficies de cristal, brillo contenido y reglas de movimiento. Úsalo al definir estilos, colores, componentes base o cualquier decisión visual del frontend.
---

# Diseño futurista, sobrio y profesional

## Idea rectora
Una **consola de edición del futuro**: fondo de tinta profunda, superficies con un leve cristal, líneas finas luminosas y datos precisos. La sensación es de herramienta de precisión, no de videojuego. **Gasta la audacia en un solo lugar:** el marco de la vista previa vertical del clip (borde con degradado "plasma" que se anima solo mientras se procesa). Todo lo demás es tranquilo y disciplinado.

## Paleta (tokens)
| Token | Hex | Uso |
|---|---|---|
| `void` | `#060914` | fondo de la app |
| `panel` | `#0D1330` | superficies principales |
| `panel-2` | `#141C45` | superficies elevadas, inputs |
| `line` | `#26306A` | bordes y divisores |
| `ink` | `#E8ECFF` | texto principal |
| `ink-muted` | `#8D97C4` | texto secundario |
| `plasma` | `#7C5CFF` | acción principal (relleno), foco |
| `plasma-soft` | `#A99BFF` | texto/iconos sobre fondo oscuro con acento violeta |
| `ion` | `#2DE2E6` | datos activos, progreso, palabra activa |
| `flare` | `#FF4D8D` | destructivo, error, grabación |
| `ok` | `#3DF5A7` | éxito |
| `warn` | `#FFC857` | aviso |

Reglas de contraste (WCAG AA): el texto normal necesita ≥ 4.5:1. **No uses `plasma` para texto pequeño** sobre `void` (queda ~3.9:1); úsalo como relleno con texto blanco o usa `plasma-soft`. El texto sobre `ion` o `ok` es `void`.

```css
/* src/styles/tokens.css */
:root {
  --void: #060914;  --panel: #0d1330;  --panel-2: #141c45;  --line: #26306a;
  --ink: #e8ecff;   --ink-muted: #8d97c4;
  --plasma: #7c5cff; --plasma-soft: #a99bff;
  --ion: #2de2e6;   --flare: #ff4d8d;  --ok: #3df5a7;  --warn: #ffc857;

  --r-field: 8px;  --r-panel: 16px;  --r-pill: 999px;   /* radios con jerarquía */
  --ease: cubic-bezier(.2,.8,.2,1);
  --dur-fast: 140ms;  --dur: 220ms;
}
```

Con Tailwind v4 exponer los tokens con `@theme { --color-void: var(--void); ... }` (o en `tailwind.config` si es v3) para usar `bg-void`, `text-ink`, `border-line`, etc.

## Tipografía
- Títulos y números grandes: **Sora** (600-700), carácter geométrico y técnico.
- Texto de interfaz y lectura: **Manrope** (400-600).
- Tiempos y códigos (`00:12.340`, rutas): **JetBrains Mono** con `font-variant-numeric: tabular-nums`. El mono se reserva a datos reales, no a decoración.
- Instalar con `@fontsource-variable/sora`, `@fontsource-variable/manrope`, `@fontsource/jetbrains-mono` (funciona sin internet).
- Escala: 12 / 14 / 16 / 20 / 28 / 40 px; interlineado 1.5 en texto, 1.15 en títulos. Líneas de lectura < 70 caracteres.
- Frases en minúscula normal ("Sentence case"). **No usar etiquetas en MAYÚSCULAS sobre cada título** ni "01 / 02 / 03" salvo que sea una secuencia real (por ejemplo, las etapas del procesamiento).

## Superficies
```css
.surface {            /* panel estándar */
  background: color-mix(in oklab, var(--panel) 88%, transparent);
  border: 1px solid var(--line);
  border-radius: var(--r-panel);
}
.surface-glass {      /* solo para elementos flotantes: barra inferior, hojas, modales */
  background: color-mix(in oklab, var(--panel) 70%, transparent);
  backdrop-filter: blur(14px) saturate(140%);
  border: 1px solid color-mix(in oklab, var(--ion) 18%, var(--line));
}
```
- Fondo de página: `void` con un gradiente radial muy tenue de `plasma` (≤ 12 % de opacidad) en una esquina y una **rejilla de 1 px casi invisible** (≤ 4 % de opacidad). Nada de partículas ni vídeos de fondo.
- `backdrop-filter` solo en 1-2 elementos flotantes por pantalla (es costoso en móviles).
- Sombras: casi no se usan. La elevación se expresa con color de superficie (`panel` → `panel-2`) y borde, no con sombras grises.

## Brillo (glow): con disciplina
- **Máximo un elemento con brillo por vista.** Candidatos: el marco de la vista previa, el botón principal en foco, la palabra activa.
- Brillo = `box-shadow: 0 0 0 1px var(--plasma), 0 0 24px -4px color-mix(in oklab, var(--plasma) 60%, transparent)`.
- Prohibido: texto con resplandor neón, bordes degradados en todas las tarjetas, gradientes decorativos en cada botón.

## El marco de la vista previa (el momento memorable)
```css
.clip-frame {
  position: relative; aspect-ratio: 9/16; border-radius: 20px; padding: 2px;
  background: conic-gradient(from var(--angle), var(--plasma), var(--ion), var(--flare), var(--plasma));
}
.clip-frame[data-busy="true"] { animation: spin 3s linear infinite; }
.clip-frame > .inner { border-radius: 18px; background: var(--void); overflow: hidden; height: 100%; }
@property --angle { syntax: "<angle>"; inherits: false; initial-value: 0deg; }
@keyframes spin { to { --angle: 360deg; } }
```
En reposo el marco está quieto y apagado (`--line`); solo se anima mientras hay trabajo en curso.

## Componentes base (cada uno con estados completos)
- **Botón primario:** relleno `plasma`, texto blanco, radio `--r-field`, foco con anillo `ion`. Secundario: borde `line`, fondo transparente. Destructivo: `flare`.
- **Input/slider:** fondo `panel-2`, borde `line`, foco `ion`. El slider de la línea de tiempo usa `ion` para el tramo activo.
- **Chip/estado:** píldora con punto de color + texto (el color nunca es la única señal).
- **Progreso por etapas:** lista vertical (móvil) u horizontal (escritorio) con estados `pendiente / en curso / listo / error`; aquí sí se numera porque es una secuencia.
- **Tarjetas de momentos:** no todas idénticas. La de mayor puntaje es más grande o va primera; el puntaje se muestra como un anillo de progreso, no como un número suelto.

## Movimiento
- Solo animar en respuesta a una acción (abrir hoja, confirmar, cambiar de pestaña) y en el marco de procesamiento. **Sin entradas "fade-up" en cada sección** ni hovers animados en todas las tarjetas.
- Duraciones 140-220 ms, easing `--ease`. Sin rebotes.
- Respetar siempre `prefers-reduced-motion: reduce` (sustituir animaciones por cambios instantáneos o fundidos cortos).
- Librería opcional: `motion` (Framer Motion) solo para hojas inferiores y transiciones de ruta.

## Iconos y adornos
- `lucide-react`, trazo 1.5-1.75 px, tamaño 20 px por defecto. Un solo set de iconos en toda la app.
- Sin emojis como iconos de interfaz.

## Texto de la interfaz
Español neutro, verbos claros y específicos: "Guardar cambios", "Exportar clip", "Buscar momentos". El mismo nombre para la misma acción en todo el flujo. Los errores dicen qué pasó y cómo arreglarlo, sin disculpas: "No se pudo leer el video. Prueba con un archivo MP4 o MOV."
